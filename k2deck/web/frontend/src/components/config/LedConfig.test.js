import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LedConfig from './LedConfig.vue'

describe('LedConfig', () => {
  it('should render with default values', () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: null },
    })

    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.text()).toContain('LED Settings')
  })

  it('should render mode select', () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { mode: 'static' } },
    })

    const select = wrapper.find('select')
    expect(select.element.value).toBe('static')

    const options = wrapper.findAll('select option')
    const values = options.map(o => o.element.value)
    expect(values).toContain('static')
    expect(values).toContain('toggle')
    expect(values).toContain('flash')
    expect(values).toContain('pulse')
  })

  it('should render color buttons', () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { color: 'red' } },
    })

    const colorButtons = wrapper.findAll('button')
    expect(colorButtons.length).toBeGreaterThanOrEqual(3)
  })

  it('should show selected color', () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { color: 'green' } },
    })

    const greenButton = wrapper.findAll('button').find(btn =>
      btn.classes().some(c => c.includes('green'))
    )
    expect(greenButton).toBeDefined()
  })

  it('should emit update on mode change', async () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { mode: 'static' } },
    })

    await wrapper.find('select').setValue('toggle')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0][0].mode).toBe('toggle')
  })

  it('should emit update on color click', async () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { mode: 'static', color: null } },
    })

    // Find first color button (red)
    const buttons = wrapper.findAll('button')
    const redButton = buttons.find(b => b.classes().some(c => c.includes('red')))

    if (redButton) {
      await redButton.trigger('click')
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    }
  })

  it('should show off color options in toggle mode', async () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { mode: 'toggle', color: 'green' } },
    })

    // In toggle mode, should show off color section
    expect(wrapper.text()).toContain('Off Color')
  })

  it('should show flash count in flash mode', async () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { mode: 'flash', color: 'red' } },
    })

    expect(wrapper.text()).toContain('Flash Count')
    expect(wrapper.find('input[type="number"]').exists()).toBe(true)
  })

  it('should show pulse speed in pulse mode', async () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { mode: 'pulse', color: 'amber' } },
    })

    expect(wrapper.text()).toContain('Pulse Speed')
  })

  it('should show preview LED', () => {
    const wrapper = mount(LedConfig, {
      props: { modelValue: { mode: 'static', color: 'green' } },
    })

    expect(wrapper.text()).toContain('Preview')
    const preview = wrapper.find('.led-glow')
    expect(preview.exists()).toBe(true)
  })
})
