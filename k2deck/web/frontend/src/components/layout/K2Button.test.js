import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import K2Button from './K2Button.vue'

describe('K2Button', () => {
  it('should render with control id', () => {
    const wrapper = mount(K2Button, {
      props: {
        control: { id: 'A1', hasLed: false },
      },
    })

    expect(wrapper.text()).toContain('A1')
  })

  it('should show dash when no mapping', () => {
    const wrapper = mount(K2Button, {
      props: {
        control: { id: 'A1', hasLed: false },
        mapping: null,
      },
    })

    expect(wrapper.text()).toContain('—')
  })

  it('should show mapping name when provided', () => {
    const wrapper = mount(K2Button, {
      props: {
        control: { id: 'A1', hasLed: false },
        mapping: { name: 'Play/Pause' },
      },
    })

    expect(wrapper.text()).toContain('Play/Pause')
  })

  it('should render LED when control has LED', () => {
    const wrapper = mount(K2Button, {
      props: {
        control: { id: 'A1', hasLed: true },
        ledState: 'green',
      },
    })

    const led = wrapper.findComponent({ name: 'K2Led' })
    expect(led.exists()).toBe(true)
  })

  it('should not render LED when control has no LED', () => {
    const wrapper = mount(K2Button, {
      props: {
        control: { id: 'A1', hasLed: false },
      },
    })

    const led = wrapper.findComponent({ name: 'K2Led' })
    expect(led.exists()).toBe(false)
  })

  it('should apply button classes', () => {
    const wrapper = mount(K2Button, {
      props: {
        control: { id: 'A1', hasLed: false },
      },
    })

    expect(wrapper.html()).toContain('bg-k2-surface')
    expect(wrapper.html()).toContain('border-k2-border')
  })
})
