import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ControlConfig from './ControlConfig.vue'
import { useUi } from '@/stores/ui'
import { useConfig } from '@/stores/config'

const mockApi = {
  get: vi.fn().mockResolvedValue({}),
  put: vi.fn().mockResolvedValue({}),
  post: vi.fn().mockResolvedValue({}),
  del: vi.fn(),
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => mockApi,
}))

describe('ControlConfig', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  function setupWithControl(control = { id: 'A1', type: 'button', hasLed: true, note: 36 }) {
    const ui = useUi()
    const config = useConfig()
    ui.selectControl(control)
    config.config = { mappings: { note_on: {}, cc_absolute: {}, cc_relative: {} } }
    return { ui, config }
  }

  it('should render selected control id', () => {
    setupWithControl()
    const wrapper = mount(ControlConfig)

    expect(wrapper.text()).toContain('A1')
  })

  it('should show control type label for button', () => {
    setupWithControl({ id: 'A1', type: 'button', hasLed: false, note: 36 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.text()).toContain('Button')
  })

  it('should show control type label for encoder', () => {
    setupWithControl({ id: 'E1', type: 'encoder', hasLed: false, cc: 1 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.text()).toContain('Encoder')
  })

  it('should show control type label for fader', () => {
    setupWithControl({ id: 'F1', type: 'fader', cc: 10 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.text()).toContain('Fader')
  })

  it('should show control type label for pot', () => {
    setupWithControl({ id: 'P1', type: 'pot', cc: 5 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.text()).toContain('Potentiometer')
  })

  it('should render name input', () => {
    setupWithControl()
    const wrapper = mount(ControlConfig)

    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
  })

  it('should render close button', () => {
    setupWithControl()
    const wrapper = mount(ControlConfig)

    // Close button with ✕
    const closeBtn = wrapper.findAll('button').find(b => b.text().includes('✕'))
    expect(closeBtn).toBeDefined()
  })

  it('should render close button', () => {
    setupWithControl()
    const wrapper = mount(ControlConfig)

    const closeBtn = wrapper.findAll('button').find(b => b.text().includes('✕'))
    expect(closeBtn).toBeDefined()
    // Note: In the real app, App.vue unmounts ControlConfig when selection is cleared
  })

  it('should render ActionPicker', () => {
    setupWithControl()
    const wrapper = mount(ControlConfig)

    expect(wrapper.findComponent({ name: 'ActionPicker' }).exists()).toBe(true)
  })

  it('should render LedConfig when control has LED', () => {
    setupWithControl({ id: 'A1', type: 'button', hasLed: true, note: 36 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.findComponent({ name: 'LedConfig' }).exists()).toBe(true)
  })

  it('should not render LedConfig when control has no LED', () => {
    setupWithControl({ id: 'F1', type: 'fader', hasLed: false, cc: 10 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.findComponent({ name: 'LedConfig' }).exists()).toBe(false)
  })

  it('should render Save and Cancel buttons', () => {
    setupWithControl()
    const wrapper = mount(ControlConfig)

    const buttons = wrapper.findAll('button')
    expect(buttons.some(b => b.text() === 'Save')).toBe(true)
    expect(buttons.some(b => b.text() === 'Cancel')).toBe(true)
  })

  it('should disable Save and Cancel when not dirty', () => {
    const { config } = setupWithControl()
    config.dirty = false

    const wrapper = mount(ControlConfig)

    const saveBtn = wrapper.findAll('button').find(b => b.text() === 'Save')
    const cancelBtn = wrapper.findAll('button').find(b => b.text() === 'Cancel')
    expect(saveBtn.attributes('disabled')).toBeDefined()
    expect(cancelBtn.attributes('disabled')).toBeDefined()
  })

  it('should show note info for button control', () => {
    setupWithControl({ id: 'A1', type: 'button', hasLed: true, note: 36 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.text()).toContain('Note:')
    expect(wrapper.text()).toContain('36')
  })

  it('should show CC info for fader control', () => {
    setupWithControl({ id: 'F1', type: 'fader', cc: 10 })
    const wrapper = mount(ControlConfig)

    expect(wrapper.text()).toContain('CC:')
    expect(wrapper.text()).toContain('10')
  })

  it('should mark config dirty on name input', async () => {
    const { config } = setupWithControl()
    const wrapper = mount(ControlConfig)

    const nameInput = wrapper.find('input[type="text"]')
    await nameInput.setValue('Test Action')
    await nameInput.trigger('input')

    expect(config.dirty).toBe(true)
  })

  it('should load existing mapping when available', () => {
    const ui = useUi()
    const config = useConfig()
    ui.selectControl({ id: 'A1', type: 'button', hasLed: false, note: 36 })
    config.config = {
      mappings: {
        note_on: { 36: { name: 'Play', action: 'spotify_play_pause' } },
        cc_absolute: {},
        cc_relative: {},
      },
    }

    const wrapper = mount(ControlConfig)

    const nameInput = wrapper.find('input[type="text"]')
    expect(nameInput.element.value).toBe('Play')
  })

  // --- Save and Revert ---

  it('should save button mapping via config store', async () => {
    const { config } = setupWithControl({ id: 'A1', type: 'button', hasLed: false, note: 36 })
    config.dirty = true
    config.saveConfig = vi.fn().mockResolvedValue()
    config.updateMapping = vi.fn()

    const wrapper = mount(ControlConfig)

    // Set name to make it dirty
    const nameInput = wrapper.find('input[type="text"]')
    await nameInput.setValue('My Action')

    const saveBtn = wrapper.findAll('button').find(b => b.text() === 'Save')
    await saveBtn.trigger('click')

    expect(config.updateMapping).toHaveBeenCalledWith(
      'note_on',
      36,
      expect.objectContaining({ name: 'My Action' })
    )
    expect(config.saveConfig).toHaveBeenCalled()
  })

  it('should save encoder mapping as cc_relative', async () => {
    const { config } = setupWithControl({ id: 'E1', type: 'encoder', hasLed: false, cc: 1 })
    config.dirty = true
    config.saveConfig = vi.fn().mockResolvedValue()
    config.updateMapping = vi.fn()

    const wrapper = mount(ControlConfig)

    const saveBtn = wrapper.findAll('button').find(b => b.text() === 'Save')
    await saveBtn.trigger('click')

    expect(config.updateMapping).toHaveBeenCalledWith(
      'cc_relative',
      1,
      expect.any(Object)
    )
  })

  it('should save fader mapping as cc_absolute', async () => {
    const { config } = setupWithControl({ id: 'F1', type: 'fader', cc: 16 })
    config.dirty = true
    config.saveConfig = vi.fn().mockResolvedValue()
    config.updateMapping = vi.fn()

    const wrapper = mount(ControlConfig)

    const saveBtn = wrapper.findAll('button').find(b => b.text() === 'Save')
    await saveBtn.trigger('click')

    expect(config.updateMapping).toHaveBeenCalledWith(
      'cc_absolute',
      16,
      expect.any(Object)
    )
  })

  it('should show error toast on save failure', async () => {
    const { config, ui } = setupWithControl()
    config.dirty = true
    config.saveConfig = vi.fn().mockRejectedValue(new Error('Save failed'))
    config.updateMapping = vi.fn()
    ui.addToast = vi.fn()

    const wrapper = mount(ControlConfig)

    const saveBtn = wrapper.findAll('button').find(b => b.text() === 'Save')
    await saveBtn.trigger('click')

    // Wait for promise
    await vi.waitFor(() => {
      expect(ui.addToast).toHaveBeenCalledWith(
        expect.stringContaining('Failed to save'),
        'error'
      )
    })
  })

  it('should revert mapping on Cancel click', async () => {
    const { config } = setupWithControl({ id: 'A1', type: 'button', hasLed: false, note: 36 })
    config.config = {
      mappings: {
        note_on: { 36: { name: 'Original', action: 'hotkey' } },
        cc_absolute: {},
        cc_relative: {},
      },
    }
    config.dirty = true

    const wrapper = mount(ControlConfig)

    // Change name
    const nameInput = wrapper.find('input[type="text"]')
    await nameInput.setValue('Changed')

    // Click Cancel
    const cancelBtn = wrapper.findAll('button').find(b => b.text() === 'Cancel')
    await cancelBtn.trigger('click')

    // Should revert to original
    expect(nameInput.element.value).toBe('Original')
    expect(config.dirty).toBe(false)
  })

  it('should revert to empty mapping when no existing mapping', async () => {
    const { config } = setupWithControl({ id: 'A1', type: 'button', hasLed: false, note: 36 })
    config.dirty = true

    const wrapper = mount(ControlConfig)

    const nameInput = wrapper.find('input[type="text"]')
    await nameInput.setValue('Temp')

    const cancelBtn = wrapper.findAll('button').find(b => b.text() === 'Cancel')
    await cancelBtn.trigger('click')

    expect(nameInput.element.value).toBe('')
    expect(config.dirty).toBe(false)
  })
})
