import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import K2Fader from './K2Fader.vue'

describe('K2Fader', () => {
  it('should render with control id as default label', () => {
    const wrapper = mount(K2Fader, {
      props: {
        control: { id: 'Fader1' },
        analogValue: 0,
      },
    })

    expect(wrapper.text()).toContain('Fader1')
  })

  it('should show mapping name when provided', () => {
    const wrapper = mount(K2Fader, {
      props: {
        control: { id: 'Fader1' },
        analogValue: 64,
        mapping: { name: 'Master Volume' },
      },
    })

    expect(wrapper.text()).toContain('Master Volume')
  })

  it('should display analog value', () => {
    const wrapper = mount(K2Fader, {
      props: {
        control: { id: 'Fader1' },
        analogValue: 100,
      },
    })

    expect(wrapper.text()).toContain('100')
  })

  it('should calculate percent correctly at 0', () => {
    const wrapper = mount(K2Fader, {
      props: {
        control: { id: 'Fader1' },
        analogValue: 0,
      },
    })

    const fill = wrapper.find('.bg-k2-success')
    expect(fill.attributes('style')).toContain('height: 0%')
  })

  it('should calculate percent correctly at 127', () => {
    const wrapper = mount(K2Fader, {
      props: {
        control: { id: 'Fader1' },
        analogValue: 127,
      },
    })

    const fill = wrapper.find('.bg-k2-success')
    expect(fill.attributes('style')).toContain('height: 100%')
  })

  it('should calculate percent correctly at midpoint', () => {
    const wrapper = mount(K2Fader, {
      props: {
        control: { id: 'Fader1' },
        analogValue: 64,
      },
    })

    const fill = wrapper.find('.bg-k2-success')
    // 64/127 * 100 = ~50%
    expect(fill.attributes('style')).toContain('height: 50%')
  })

  it('should render knob element', () => {
    const wrapper = mount(K2Fader, {
      props: {
        control: { id: 'Fader1' },
        analogValue: 64,
      },
    })

    const knob = wrapper.find('.bg-k2-text')
    expect(knob.exists()).toBe(true)
  })
})
