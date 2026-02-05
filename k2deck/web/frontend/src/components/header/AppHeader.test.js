import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import AppHeader from './AppHeader.vue'

// Mock useApi with proper responses for all child components
const mockGet = vi.fn((path) => {
  if (path === '/integrations') {
    return Promise.resolve({
      obs: { available: false, connected: false, status: 'unavailable', error: null },
      spotify: { available: false, connected: false, status: 'unavailable', error: null },
      twitch: { available: false, connected: false, status: 'unavailable', error: null },
    })
  }
  if (path === '/profiles') {
    return Promise.resolve({ profiles: [], active: 'default' })
  }
  return Promise.resolve({})
})

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    get: mockGet,
    put: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
    del: vi.fn(),
  }),
}))

describe('AppHeader', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should render K2 Deck title', () => {
    const wrapper = mount(AppHeader)

    expect(wrapper.text()).toContain('K2 Deck')
  })

  it('should render header element', () => {
    const wrapper = mount(AppHeader)

    expect(wrapper.find('header').exists()).toBe(true)
  })

  it('should contain ConnectionStatus component', () => {
    const wrapper = mount(AppHeader)

    const connectionStatus = wrapper.findComponent({ name: 'ConnectionStatus' })
    expect(connectionStatus.exists()).toBe(true)
  })

  it('should contain IntegrationPills component', () => {
    const wrapper = mount(AppHeader)

    const integrationPills = wrapper.findComponent({ name: 'IntegrationPills' })
    expect(integrationPills.exists()).toBe(true)
  })

  it('should contain ProfileDropdown component', () => {
    const wrapper = mount(AppHeader)

    const profileDropdown = wrapper.findComponent({ name: 'ProfileDropdown' })
    expect(profileDropdown.exists()).toBe(true)
  })

  it('should apply header styling', () => {
    const wrapper = mount(AppHeader)

    expect(wrapper.find('.app-header').exists()).toBe(true)
    expect(wrapper.html()).toContain('bg-k2-surface')
  })
})
