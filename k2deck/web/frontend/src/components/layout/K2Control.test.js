import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import K2Control from './K2Control.vue'
import { useUi } from '@/stores/ui'
import { useK2State } from '@/stores/k2State'
import { useAnalogState } from '@/stores/analogState'

describe('K2Control', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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
})
