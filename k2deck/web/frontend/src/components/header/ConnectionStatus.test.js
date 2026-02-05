import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConnectionStatus from './ConnectionStatus.vue'
import { useK2State } from '@/stores/k2State'

describe('ConnectionStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should show disconnected when not connected', () => {
    const wrapper = mount(ConnectionStatus)

    expect(wrapper.text()).toContain('Disconnected')
  })

  it('should show port name when connected', () => {
    const k2State = useK2State()
    k2State.connected = true
    k2State.port = 'XONE:K2'

    const wrapper = mount(ConnectionStatus)

    expect(wrapper.text()).toContain('XONE:K2')
  })

  it('should show error class when disconnected', () => {
    const wrapper = mount(ConnectionStatus)

    expect(wrapper.html()).toContain('bg-k2-error')
  })

  it('should show success class when connected', () => {
    const k2State = useK2State()
    k2State.connected = true
    k2State.port = 'XONE:K2'

    const wrapper = mount(ConnectionStatus)

    expect(wrapper.html()).toContain('bg-k2-success')
  })

  it('should render indicator dot', () => {
    const wrapper = mount(ConnectionStatus)

    const dot = wrapper.find('.w-2.h-2.rounded-full')
    expect(dot.exists()).toBe(true)
  })
})
