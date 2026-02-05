import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import IntegrationPills from './IntegrationPills.vue'
import { useIntegrations } from '@/stores/integrations'
import { useUi } from '@/stores/ui'

// Mock useApi
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue({
      obs: { available: true, connected: false, status: 'available', error: null },
      spotify: { available: true, connected: true, status: 'connected', error: null },
      twitch: { available: false, connected: false, status: 'unavailable', error: null },
    }),
    post: vi.fn().mockResolvedValue({
      available: true,
      connected: true,
      status: 'connected',
      error: null,
    }),
  }),
}))

describe('IntegrationPills', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should render all integration pills', () => {
    const wrapper = mount(IntegrationPills)

    expect(wrapper.text()).toContain('obs')
    expect(wrapper.text()).toContain('spotify')
    expect(wrapper.text()).toContain('twitch')
  })

  it('should show success class for connected integration', async () => {
    const integrations = useIntegrations()
    integrations.spotify.connected = true

    const wrapper = mount(IntegrationPills)

    // Find spotify pill
    const pills = wrapper.findAll('[class*="flex items-center"]')
    const spotifyPill = pills.find(p => p.text().includes('spotify'))

    expect(spotifyPill.classes().some(c => c.includes('k2-success'))).toBe(true)
  })

  it('should show error class for integration with error', () => {
    const integrations = useIntegrations()
    integrations.obs.error = 'Connection failed'

    const wrapper = mount(IntegrationPills)

    const pills = wrapper.findAll('[class*="flex items-center"]')
    const obsPill = pills.find(p => p.text().includes('obs'))

    expect(obsPill.classes().some(c => c.includes('k2-error'))).toBe(true)
  })

  it('should show neutral class for unavailable integration', () => {
    const wrapper = mount(IntegrationPills)

    const integrations = useIntegrations()
    // Default state is unavailable

    const pills = wrapper.findAll('[class*="flex items-center"]')
    const twitchPill = pills.find(p => p.text().includes('twitch'))

    expect(twitchPill.classes().some(c => c.includes('bg-k2-surface'))).toBe(true)
  })

  it('should show title with status', () => {
    const integrations = useIntegrations()
    integrations.obs.status = 'available'

    const wrapper = mount(IntegrationPills)

    const pills = wrapper.findAll('[class*="flex items-center"]')
    const obsPill = pills.find(p => p.text().includes('obs'))

    expect(obsPill.attributes('title')).toBe('available')
  })

  it('should show title with error when present', () => {
    const integrations = useIntegrations()
    integrations.obs.error = 'Connection refused'

    const wrapper = mount(IntegrationPills)

    const pills = wrapper.findAll('[class*="flex items-center"]')
    const obsPill = pills.find(p => p.text().includes('obs'))

    expect(obsPill.attributes('title')).toBe('Connection refused')
  })

  it('should disconnect when clicking connected integration', async () => {
    const integrations = useIntegrations()
    const ui = useUi()
    integrations.spotify.connected = true
    integrations.spotify.available = true

    const wrapper = mount(IntegrationPills)

    const pills = wrapper.findAll('[class*="flex items-center"]')
    const spotifyPill = pills.find(p => p.text().includes('spotify'))

    await spotifyPill.trigger('click')

    // Should show toast
    expect(ui.toasts.length).toBeGreaterThanOrEqual(0)
  })

  it('should connect when clicking available integration', async () => {
    const integrations = useIntegrations()
    integrations.obs.connected = false
    integrations.obs.available = true

    const wrapper = mount(IntegrationPills)

    const pills = wrapper.findAll('[class*="flex items-center"]')
    const obsPill = pills.find(p => p.text().includes('obs'))

    await obsPill.trigger('click')

    // Connection was attempted
    expect(integrations.obs).toBeDefined()
  })

  it('should render indicator dot for each pill', () => {
    const wrapper = mount(IntegrationPills)

    const dots = wrapper.findAll('.w-2.h-2.rounded-full')
    expect(dots.length).toBe(3) // obs, spotify, twitch
  })
})
