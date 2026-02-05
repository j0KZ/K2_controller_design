import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import K2Encoder from './K2Encoder.vue'

describe('K2Encoder', () => {
  it('should render with control id as default label', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: false },
      },
    })

    expect(wrapper.text()).toContain('Enc1')
  })

  it('should show mapping name when provided', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: false },
        mapping: { name: 'Scroll' },
      },
    })

    expect(wrapper.text()).toContain('Scroll')
  })

  it('should render LED when control has LED', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: true },
        ledState: 'amber',
      },
    })

    const led = wrapper.findComponent({ name: 'K2Led' })
    expect(led.exists()).toBe(true)
  })

  it('should not render LED when control has no LED', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: false },
      },
    })

    const led = wrapper.findComponent({ name: 'K2Led' })
    expect(led.exists()).toBe(false)
  })

  it('should render SVG encoder visual', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: false },
      },
    })

    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.findAll('circle').length).toBeGreaterThanOrEqual(2)
  })

  it('should render value arc when analog value is provided', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: false },
        analogValue: 64,
      },
    })

    // Should have 3 circles: background, value arc, center dot
    expect(wrapper.findAll('circle').length).toBe(3)
  })

  it('should not render value arc when analog value is null', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: false },
        analogValue: null,
      },
    })

    // Should have 2 circles: background, center dot
    expect(wrapper.findAll('circle').length).toBe(2)
  })

  it('should calculate percent as 0 when analog value is null', () => {
    const wrapper = mount(K2Encoder, {
      props: {
        control: { id: 'Enc1', hasLed: false },
        analogValue: null,
      },
    })

    // The component should handle null gracefully
    expect(wrapper.text()).toContain('Enc1')
  })
})
