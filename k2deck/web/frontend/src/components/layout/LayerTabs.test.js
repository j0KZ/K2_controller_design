import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import LayerTabs from './LayerTabs.vue'
import { useK2State } from '@/stores/k2State'
import { useUi } from '@/stores/ui'

const mockApi = {
  get: vi.fn(),
  put: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => mockApi,
}))

describe('LayerTabs', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockApi.put.mockResolvedValue({})
  })

  it('should render 3 layer buttons', () => {
    const wrapper = mount(LayerTabs)

    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(3)
    expect(buttons[0].text()).toBe('Layer 1')
    expect(buttons[1].text()).toBe('Layer 2')
    expect(buttons[2].text()).toBe('Layer 3')
  })

  it('should highlight active layer', () => {
    const k2State = useK2State()
    k2State.layer = 2

    const wrapper = mount(LayerTabs)

    const buttons = wrapper.findAll('button')
    expect(buttons[1].classes()).toContain('bg-k2-accent')
    expect(buttons[0].classes()).not.toContain('bg-k2-accent')
  })

  it('should call API on layer click', async () => {
    const wrapper = mount(LayerTabs)

    const buttons = wrapper.findAll('button')
    await buttons[1].trigger('click')

    expect(mockApi.put).toHaveBeenCalledWith('/k2/state/layer', { layer: 2 })
  })

  it('should update state on successful layer change', async () => {
    const k2State = useK2State()

    const wrapper = mount(LayerTabs)

    await wrapper.findAll('button')[2].trigger('click')
    await vi.dynamicImportSettled()

    expect(k2State.layer).toBe(3)
  })

  it('should show toast on error', async () => {
    mockApi.put.mockRejectedValueOnce(new Error('API error'))

    const ui = useUi()
    const wrapper = mount(LayerTabs)

    await wrapper.findAll('button')[1].trigger('click')
    await vi.dynamicImportSettled()

    // Wait for promise rejection to propagate
    await new Promise(r => setTimeout(r, 10))

    expect(ui.toasts.some(t => t.message.includes('Failed to switch layer'))).toBe(true)
  })

  it('should apply inactive style to non-selected layers', () => {
    const k2State = useK2State()
    k2State.layer = 1

    const wrapper = mount(LayerTabs)

    const buttons = wrapper.findAll('button')
    expect(buttons[1].classes()).toContain('bg-k2-surface')
    expect(buttons[2].classes()).toContain('bg-k2-surface')
  })
})
