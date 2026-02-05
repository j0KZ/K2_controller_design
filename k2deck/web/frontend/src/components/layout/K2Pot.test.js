import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import K2Pot from './K2Pot.vue'

describe('K2Pot', () => {
  it('should render with control id as default label', () => {
    const wrapper = mount(K2Pot, {
      props: {
        control: { id: 'Pot1' },
        analogValue: 0,
      },
    })

    expect(wrapper.text()).toContain('Pot1')
  })

  it('should show mapping name when provided', () => {
    const wrapper = mount(K2Pot, {
      props: {
        control: { id: 'Pot1' },
        analogValue: 64,
        mapping: { name: 'EQ Bass' },
      },
    })

    expect(wrapper.text()).toContain('EQ Bass')
  })

  it('should display analog value', () => {
    const wrapper = mount(K2Pot, {
      props: {
        control: { id: 'Pot1' },
        analogValue: 75,
      },
    })

    expect(wrapper.text()).toContain('75')
  })

  it('should render SVG pot visual', () => {
    const wrapper = mount(K2Pot, {
      props: {
        control: { id: 'Pot1' },
        analogValue: 64,
      },
    })

    expect(wrapper.find('svg').exists()).toBe(true)
    // Should have 3 circles: background, value arc, center dot
    expect(wrapper.findAll('circle').length).toBe(3)
  })

  it('should calculate percent correctly at 0', () => {
    const wrapper = mount(K2Pot, {
      props: {
        control: { id: 'Pot1' },
        analogValue: 0,
      },
    })

    // At 0%, dashoffset should be 125.6 (full dasharray)
    const valueArc = wrapper.findAll('circle')[1]
    expect(valueArc.attributes('stroke-dashoffset')).toContain('125.6')
  })

  it('should calculate percent correctly at 127', () => {
    const wrapper = mount(K2Pot, {
      props: {
        control: { id: 'Pot1' },
        analogValue: 127,
      },
    })

    // At 100%, dashoffset should be 0 (125.6 - 125.6)
    const valueArc = wrapper.findAll('circle')[1]
    // Close to 0
    const offset = parseFloat(valueArc.attributes('stroke-dashoffset'))
    expect(offset).toBeLessThan(1)
  })

  it('should have correct SVG dimensions', () => {
    const wrapper = mount(K2Pot, {
      props: {
        control: { id: 'Pot1' },
        analogValue: 64,
      },
    })

    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBe('48')
    expect(svg.attributes('height')).toBe('48')
  })
})
