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
})
