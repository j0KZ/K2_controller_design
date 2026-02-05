import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, config as testConfig } from '@vue/test-utils'
import { defineComponent, onMounted } from 'vue'

const mockApi = {
  get: vi.fn().mockResolvedValue({}),
  put: vi.fn().mockResolvedValue({}),
  post: vi.fn().mockResolvedValue({}),
  del: vi.fn(),
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => mockApi,
}))

import { useKeyboard } from './useKeyboard'
import { useUi } from '@/stores/ui'
import { useConfig } from '@/stores/config'
import { useK2State } from '@/stores/k2State'

// Helper component that uses the composable
const TestComponent = defineComponent({
  setup() {
    useKeyboard()
    return {}
  },
  template: '<div>test</div>',
})

describe('useKeyboard', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockApi.put.mockResolvedValue({})
    mockApi.get.mockResolvedValue({})
    wrapper = mount(TestComponent)
  })

  afterEach(() => {
    wrapper.unmount()
  })

  function dispatchKey(key, opts = {}) {
    const event = new KeyboardEvent('keydown', {
      key,
      bubbles: true,
      ...opts,
    })
    // Allow preventDefault to be tracked
    const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
    window.dispatchEvent(event)
    return preventDefaultSpy
  }

  it('should clear selection on Escape', () => {
    const ui = useUi()
    ui.selectControl({ id: 'A1', type: 'button' })

    dispatchKey('Escape')

    expect(ui.selectedControl).toBeNull()
  })

  it('should switch to layer 1 on pressing 1', () => {
    dispatchKey('1')

    expect(mockApi.put).toHaveBeenCalledWith('/k2/state/layer', { layer: 1 })
  })

  it('should switch to layer 2 on pressing 2', () => {
    dispatchKey('2')

    expect(mockApi.put).toHaveBeenCalledWith('/k2/state/layer', { layer: 2 })
  })

  it('should switch to layer 3 on pressing 3', () => {
    dispatchKey('3')

    expect(mockApi.put).toHaveBeenCalledWith('/k2/state/layer', { layer: 3 })
  })

  it('should not switch layers when ctrl is pressed', () => {
    dispatchKey('1', { ctrlKey: true })

    // Should not call layer change API
    expect(mockApi.put).not.toHaveBeenCalledWith('/k2/state/layer', expect.anything())
  })

  it('should save config on Ctrl+S when dirty', () => {
    const config = useConfig()
    config.dirty = true
    config.saveConfig = vi.fn().mockResolvedValue({})

    const spy = dispatchKey('s', { ctrlKey: true })

    expect(config.saveConfig).toHaveBeenCalled()
  })

  it('should not save config on Ctrl+S when not dirty', () => {
    const config = useConfig()
    config.dirty = false
    config.saveConfig = vi.fn().mockResolvedValue({})

    dispatchKey('s', { ctrlKey: true })

    expect(config.saveConfig).not.toHaveBeenCalled()
  })

  it('should revert on Ctrl+Z when dirty', () => {
    const config = useConfig()
    config.dirty = true
    config.fetchConfig = vi.fn().mockResolvedValue({})

    dispatchKey('z', { ctrlKey: true })

    expect(config.fetchConfig).toHaveBeenCalled()
  })

  it('should not revert on Ctrl+Z when not dirty', () => {
    const config = useConfig()
    config.dirty = false
    config.fetchConfig = vi.fn().mockResolvedValue({})

    dispatchKey('z', { ctrlKey: true })

    expect(config.fetchConfig).not.toHaveBeenCalled()
  })

  it('should ignore keydown when input is focused', () => {
    const ui = useUi()
    ui.selectControl({ id: 'A1', type: 'button' })

    // Create and dispatch event with input target
    const event = new KeyboardEvent('keydown', {
      key: 'Escape',
      bubbles: true,
    })
    Object.defineProperty(event, 'target', {
      value: { tagName: 'INPUT' },
      writable: false,
    })
    window.dispatchEvent(event)

    // Selection should NOT be cleared (input was focused)
    expect(ui.selectedControl).not.toBeNull()
  })
})
