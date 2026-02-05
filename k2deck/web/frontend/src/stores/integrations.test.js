import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useIntegrations } from './integrations'

// Mock useApi
const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => mockApi,
}))

describe('useIntegrations store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should initialize with default state', () => {
    const integrations = useIntegrations()

    expect(integrations.obs).toEqual({
      available: false,
      connected: false,
      status: 'unavailable',
      error: null,
    })
    expect(integrations.spotify).toEqual({
      available: false,
      connected: false,
      status: 'unavailable',
      error: null,
    })
    expect(integrations.twitch).toEqual({
      available: false,
      connected: false,
      status: 'unavailable',
      error: null,
    })
  })

  it('should fetch all integrations', async () => {
    mockApi.get.mockResolvedValueOnce({
      obs: { available: true, connected: true, status: 'connected', error: null },
      spotify: { available: true, connected: false, status: 'available', error: null },
      twitch: { available: false, connected: false, status: 'unavailable', error: null },
    })

    const integrations = useIntegrations()
    await integrations.fetchAll()

    expect(integrations.obs.connected).toBe(true)
    expect(integrations.spotify.available).toBe(true)
    expect(integrations.twitch.available).toBe(false)
  })

  it('should handle fetch error gracefully', async () => {
    mockApi.get.mockRejectedValueOnce(new Error('Network error'))

    const integrations = useIntegrations()
    await integrations.fetchAll()

    // Should keep defaults on error
    expect(integrations.obs.connected).toBe(false)
    expect(integrations.spotify.connected).toBe(false)
  })

  it('should handle status change', () => {
    const integrations = useIntegrations()

    integrations.handleChange('obs', 'connected')

    expect(integrations.obs.status).toBe('connected')
    expect(integrations.obs.connected).toBe(true)
  })

  it('should handle disconnect status change', () => {
    const integrations = useIntegrations()
    integrations.obs.connected = true
    integrations.obs.status = 'connected'

    integrations.handleChange('obs', 'disconnected')

    expect(integrations.obs.status).toBe('disconnected')
    expect(integrations.obs.connected).toBe(false)
  })

  it('should ignore change for unknown integration', () => {
    const integrations = useIntegrations()

    // Should not throw
    integrations.handleChange('unknown', 'connected')

    // State unchanged
    expect(integrations.obs.connected).toBe(false)
  })

  it('should connect to integration', async () => {
    mockApi.post.mockResolvedValueOnce({
      available: true,
      connected: true,
      status: 'connected',
      error: null,
    })

    const integrations = useIntegrations()
    await integrations.connect('obs')

    expect(mockApi.post).toHaveBeenCalledWith('/integrations/obs/connect', {})
    expect(integrations.obs.connected).toBe(true)
  })

  it('should connect with params', async () => {
    mockApi.post.mockResolvedValueOnce({
      available: true,
      connected: true,
      status: 'connected',
      error: null,
    })

    const integrations = useIntegrations()
    await integrations.connect('obs', { host: 'localhost', port: 4455 })

    expect(mockApi.post).toHaveBeenCalledWith('/integrations/obs/connect', {
      host: 'localhost',
      port: 4455,
    })
  })

  it('should handle connect error', async () => {
    mockApi.post.mockImplementationOnce(() => Promise.reject(new Error('Connection refused')))

    const integrations = useIntegrations()
    await integrations.connect('obs')

    expect(integrations.obs.error).toBe('Connection refused')
  })

  it('should disconnect from integration', async () => {
    mockApi.post.mockResolvedValueOnce({
      available: true,
      connected: false,
      status: 'available',
      error: null,
    })

    const integrations = useIntegrations()
    integrations.obs.connected = true
    await integrations.disconnect('obs')

    expect(mockApi.post).toHaveBeenCalledWith('/integrations/obs/disconnect')
    expect(integrations.obs.connected).toBe(false)
  })

  it('should handle disconnect error', async () => {
    mockApi.post.mockImplementationOnce(() => Promise.reject(new Error('Disconnect failed')))

    const integrations = useIntegrations()
    await integrations.disconnect('spotify')

    expect(integrations.spotify.error).toBe('Disconnect failed')
  })
})
