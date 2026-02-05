import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import K2Row from './K2Row.vue'

describe('K2Row', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should render controls in a row', () => {
    const wrapper = mount(K2Row, {
      props: {
        row: {
          type: 'button',
          controls: [
            { id: 'A1', type: 'button', hasLed: false },
            { id: 'A2', type: 'button', hasLed: false },
          ],
        },
      },
    })

    expect(wrapper.find('.k2-row').exists()).toBe(true)
  })

  it('should render K2Control for each control', () => {
    const wrapper = mount(K2Row, {
      props: {
        row: {
          type: 'button',
          controls: [
            { id: 'A1', type: 'button', hasLed: false },
            { id: 'A2', type: 'button', hasLed: false },
            { id: 'A3', type: 'button', hasLed: false },
          ],
        },
      },
    })

    const controls = wrapper.findAllComponents({ name: 'K2Control' })
    expect(controls.length).toBe(3)
  })

  it('should render empty row', () => {
    const wrapper = mount(K2Row, {
      props: {
        row: { type: 'button', controls: [] },
      },
    })

    expect(wrapper.find('.k2-row').exists()).toBe(true)
    const controls = wrapper.findAllComponents({ name: 'K2Control' })
    expect(controls.length).toBe(0)
  })

  it('should have flex layout with gap', () => {
    const wrapper = mount(K2Row, {
      props: {
        row: {
          type: 'button',
          controls: [{ id: 'A1', type: 'button', hasLed: false }],
        },
      },
    })

    expect(wrapper.find('.flex.gap-2.justify-center').exists()).toBe(true)
  })
})
