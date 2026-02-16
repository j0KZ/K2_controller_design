import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProfiles } from './profiles'

// Mock useApi
const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => mockApi,
}))

describe('useProfiles store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should initialize with default state', () => {
    const profiles = useProfiles()

    expect(profiles.profiles).toEqual([])
    expect(profiles.activeProfile).toBe('default')
    expect(profiles.loading).toBe(false)
    expect(profiles.error).toBeNull()
  })

  it('should fetch profiles', async () => {
    mockApi.get.mockResolvedValueOnce({
      profiles: [{ name: 'default' }, { name: 'gaming' }],
      active: 'gaming',
    })

    const profiles = useProfiles()
    await profiles.fetchProfiles()

    expect(profiles.profiles).toHaveLength(2)
    expect(profiles.activeProfile).toBe('gaming')
    expect(profiles.loading).toBe(false)
  })

  it('should handle fetch error with fallback', async () => {
    mockApi.get.mockRejectedValueOnce(new Error('Network error'))

    const profiles = useProfiles()
    await profiles.fetchProfiles()

    expect(profiles.error).toBe('Network error')
    expect(profiles.profiles).toEqual([{ name: 'default' }])
    expect(profiles.activeProfile).toBe('default')
  })

  it('should get profile names', () => {
    const profiles = useProfiles()
    profiles.profiles = [{ name: 'default' }, { name: 'gaming' }, { name: 'streaming' }]

    expect(profiles.profileNames).toEqual(['default', 'gaming', 'streaming'])
  })

  it('should check if profile is active', () => {
    const profiles = useProfiles()
    profiles.activeProfile = 'gaming'

    expect(profiles.isActive('gaming')).toBe(true)
    expect(profiles.isActive('default')).toBe(false)
  })

  it('should create profile', async () => {
    mockApi.post.mockResolvedValueOnce({})
    mockApi.get.mockResolvedValueOnce({
      profiles: [{ name: 'default' }, { name: 'new-profile' }],
      active: 'default',
    })

    const profiles = useProfiles()
    await profiles.createProfile('new-profile', 'default')

    expect(mockApi.post).toHaveBeenCalledWith('/profiles', {
      name: 'new-profile',
      copy_from: 'default',
    })
  })

  it('should create profile without copy', async () => {
    mockApi.post.mockResolvedValueOnce({})
    mockApi.get.mockResolvedValueOnce({
      profiles: [{ name: 'default' }, { name: 'empty' }],
      active: 'default',
    })

    const profiles = useProfiles()
    await profiles.createProfile('empty', null)

    expect(mockApi.post).toHaveBeenCalledWith('/profiles', {
      name: 'empty',
      copy_from: null,
    })
  })

  it('should delete profile', async () => {
    mockApi.del.mockResolvedValueOnce({})
    mockApi.get.mockResolvedValueOnce({
      profiles: [{ name: 'default' }],
      active: 'default',
    })

    const profiles = useProfiles()
    await profiles.deleteProfile('old-profile')

    expect(mockApi.del).toHaveBeenCalledWith('/profiles/old-profile')
  })

  it('should activate profile', async () => {
    mockApi.put.mockResolvedValueOnce({})

    const profiles = useProfiles()
    await profiles.activateProfile('gaming')

    expect(mockApi.put).toHaveBeenCalledWith('/profiles/gaming/activate')
    expect(profiles.activeProfile).toBe('gaming')
  })

  it('should handle change from WebSocket', () => {
    const profiles = useProfiles()
    profiles.activeProfile = 'default'

    profiles.handleChange('streaming')

    expect(profiles.activeProfile).toBe('streaming')
  })

  it('should handle create profile error', async () => {
    mockApi.post.mockRejectedValueOnce(new Error('Profile exists'))

    const profiles = useProfiles()

    await expect(profiles.createProfile('existing')).rejects.toThrow('Profile exists')
    expect(profiles.error).toBe('Profile exists')
  })

  it('should handle delete profile error', async () => {
    mockApi.del.mockRejectedValueOnce(new Error('Cannot delete active'))

    const profiles = useProfiles()

    await expect(profiles.deleteProfile('active')).rejects.toThrow('Cannot delete active')
    expect(profiles.error).toBe('Cannot delete active')
  })

  it('should handle activate profile error', async () => {
    mockApi.put.mockRejectedValueOnce(new Error('Profile not found'))

    const profiles = useProfiles()

    await expect(profiles.activateProfile('missing')).rejects.toThrow('Profile not found')
    expect(profiles.error).toBe('Profile not found')
  })

  it('should export profile via window.location.href', () => {
    const profiles = useProfiles()
    const originalLocation = window.location
    delete window.location
    window.location = { href: '' }

    profiles.exportProfile('gaming')

    expect(window.location.href).toBe('/api/profiles/gaming/export')
    window.location = originalLocation
  })

  it('should import profile and refresh list', async () => {
    const mockFile = new File(['{}'], 'test.json', { type: 'application/json' })
    const mockResponse = { message: "Profile 'test' imported", profile: 'test' }

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })
    mockApi.get.mockResolvedValueOnce({
      profiles: [{ name: 'default' }, { name: 'test' }],
      active: 'default',
    })

    const profiles = useProfiles()
    const result = await profiles.importProfile(mockFile)

    expect(global.fetch).toHaveBeenCalledWith('/api/profiles/import', {
      method: 'POST',
      body: expect.any(FormData),
    })
    expect(result.profile).toBe('test')
    expect(profiles.loading).toBe(false)
    expect(profiles.error).toBeNull()
  })

  it('should handle import error with string detail', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: 'Profile already exists' }),
    })

    const profiles = useProfiles()
    const mockFile = new File(['{}'], 'test.json', { type: 'application/json' })

    await expect(profiles.importProfile(mockFile)).rejects.toThrow('Profile already exists')
    expect(profiles.error).toBe('Profile already exists')
    expect(profiles.loading).toBe(false)
  })

  it('should handle import error with dict detail', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: { message: 'Config validation failed', errors: ['bad'] } }),
    })

    const profiles = useProfiles()
    const mockFile = new File(['{}'], 'test.json', { type: 'application/json' })

    await expect(profiles.importProfile(mockFile)).rejects.toThrow('Config validation failed')
    expect(profiles.error).toBe('Config validation failed')
  })
})
