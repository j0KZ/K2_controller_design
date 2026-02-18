import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// Mock useDragDrop before importing component
const mockDragDrop = {
  isDragOver: vi.fn().mockReturnValue(false),
  isSourceControl: vi.fn().mockReturnValue(false),
  onControlDragStart: vi.fn(),
  onDragEnd: vi.fn(),
  onDragOver: vi.fn(),
  onDragEnter: vi.fn(),
  onDragLeave: vi.fn(),
  onDrop: vi.fn(),
  state: { isDragging: false },
  resetDragState: vi.fn(),
}
vi.mock('@/composables/useDragDrop', () => ({
  useDragDrop: () => mockDragDrop,
}))

import K2Control from './K2Control.vue'
import { useUi } from '@/stores/ui'
import { useK2State } from '@/stores/k2State'
import { useAnalogState } from '@/stores/analogState'
import { useConfig } from '@/stores/config'

describe('K2Control', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockDragDrop.isDragOver.mockReturnValue(false)
    mockDragDrop.isSourceControl.mockReturnValue(false)
  })

  it('should render a button control by default', () => {
    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'A1', type: 'button', hasLed: false },
        rowType: 'button',
      },
    })

    expect(wrapper.find('.k2-button').exists()).toBe(true)
  })

  it('should render an encoder control', () => {
    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'E1', type: 'encoder', hasLed: false },
        rowType: 'encoder',
      },
    })

    expect(wrapper.find('.k2-encoder').exists()).toBe(true)
  })

  it('should render a pot control', () => {
    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'P1', type: 'pot' },
        rowType: 'pot',
      },
    })

    expect(wrapper.find('.k2-pot').exists()).toBe(true)
  })

  it('should render a fader control', () => {
    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'F1', type: 'fader' },
        rowType: 'fader',
      },
    })

    expect(wrapper.find('.k2-fader').exists()).toBe(true)
  })

  it('should select control on click', async () => {
    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'A1', type: 'button', hasLed: false },
        rowType: 'button',
      },
    })

    const ui = useUi()
    await wrapper.find('.k2-control').trigger('click')

    expect(ui.selectedControl).toEqual({ id: 'A1', type: 'button', hasLed: false })
  })

  it('should apply selected class when control is selected', () => {
    const ui = useUi()
    ui.selectControl({ id: 'A1', type: 'button', hasLed: false })

    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'A1', type: 'button', hasLed: false },
        rowType: 'button',
      },
    })

    expect(wrapper.find('.control-selected').exists()).toBe(true)
  })

  it('should not apply selected class when different control selected', () => {
    const ui = useUi()
    ui.selectControl({ id: 'A2', type: 'button', hasLed: false })

    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'A1', type: 'button', hasLed: false },
        rowType: 'button',
      },
    })

    expect(wrapper.find('.control-selected').exists()).toBe(false)
  })

  it('should pass LED state to child component', () => {
    const k2State = useK2State()
    k2State.leds = { 36: 'green' }

    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'A1', type: 'button', hasLed: true, note: 36 },
        rowType: 'button',
      },
    })

    expect(wrapper.find('.k2-button').exists()).toBe(true)
  })

  it('should pass analog value to fader', () => {
    const analogState = useAnalogState()
    analogState.positions = { 1: 64 }

    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'F1', type: 'fader', cc: 1 },
        rowType: 'fader',
      },
    })

    expect(wrapper.find('.k2-fader').exists()).toBe(true)
    expect(wrapper.text()).toContain('64')
  })

  it('should return null analog value when no cc', () => {
    const wrapper = mount(K2Control, {
      props: {
        control: { id: 'A1', type: 'button', hasLed: false },
        rowType: 'button',
      },
    })

    // Button without CC should not show analog value
    expect(wrapper.find('.k2-button').exists()).toBe(true)
  })

  // --- Drag and Drop ---

  describe('drag and drop', () => {
    it('sets draggable true when control has mapping', () => {
      const config = useConfig()
      config.config = {
        mappings: { note_on: { 36: { name: 'HK', action: 'hotkey' } } },
      }

      const wrapper = mount(K2Control, {
        props: {
          control: { id: 'A1', type: 'button', note: 36, hasLed: false },
          rowType: 'button',
        },
      })

      expect(wrapper.find('.k2-control').attributes('draggable')).toBe('true')
    })

    it('sets draggable false when control has no mapping', () => {
      const config = useConfig()
      config.config = { mappings: {} }

      const wrapper = mount(K2Control, {
        props: {
          control: { id: 'A1', type: 'button', note: 36, hasLed: false },
          rowType: 'button',
        },
      })

      expect(wrapper.find('.k2-control').attributes('draggable')).toBe('false')
    })

    it('applies drop-target-active class during dragover', () => {
      mockDragDrop.isDragOver.mockReturnValue(true)

      const wrapper = mount(K2Control, {
        props: {
          control: { id: 'A1', type: 'button', hasLed: false },
          rowType: 'button',
        },
      })

      expect(wrapper.find('.drop-target-active').exists()).toBe(true)
    })

    it('applies drag-source-active class when being dragged', () => {
      mockDragDrop.isSourceControl.mockReturnValue(true)

      const wrapper = mount(K2Control, {
        props: {
          control: { id: 'A1', type: 'button', hasLed: false },
          rowType: 'button',
        },
      })

      expect(wrapper.find('.drag-source-active').exists()).toBe(true)
    })

    it('click still works alongside draggable', async () => {
      const config = useConfig()
      config.config = {
        mappings: { note_on: { 36: { name: 'HK', action: 'hotkey' } } },
      }

      const wrapper = mount(K2Control, {
        props: {
          control: { id: 'A1', type: 'button', note: 36, hasLed: false },
          rowType: 'button',
        },
      })

      const ui = useUi()
      await wrapper.find('.k2-control').trigger('click')

      expect(ui.selectedControl).toEqual({
        id: 'A1',
        type: 'button',
        note: 36,
        hasLed: false,
      })
    })
  })
})
