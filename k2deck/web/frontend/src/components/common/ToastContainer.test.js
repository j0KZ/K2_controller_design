import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ToastContainer from './ToastContainer.vue'
import { useUi } from '@/stores/ui'

describe('ToastContainer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should render empty when no toasts', () => {
    const wrapper = mount(ToastContainer)

    expect(wrapper.findAll('.px-4.py-2').length).toBe(0)
  })

  it('should render toast message', () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Hello', type: 'info' }]

    const wrapper = mount(ToastContainer)

    expect(wrapper.text()).toContain('Hello')
  })

  it('should render multiple toasts', () => {
    const ui = useUi()
    ui.toasts = [
      { id: 1, message: 'First', type: 'info' },
      { id: 2, message: 'Second', type: 'success' },
    ]

    const wrapper = mount(ToastContainer)

    expect(wrapper.text()).toContain('First')
    expect(wrapper.text()).toContain('Second')
  })

  it('should apply info classes', () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Info msg', type: 'info' }]

    const wrapper = mount(ToastContainer)

    expect(wrapper.html()).toContain('bg-k2-accent')
  })

  it('should apply success classes', () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Success msg', type: 'success' }]

    const wrapper = mount(ToastContainer)

    expect(wrapper.html()).toContain('bg-k2-success')
  })

  it('should apply warning classes', () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Warning msg', type: 'warning' }]

    const wrapper = mount(ToastContainer)

    expect(wrapper.html()).toContain('bg-k2-warning')
  })

  it('should apply error classes', () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Error msg', type: 'error' }]

    const wrapper = mount(ToastContainer)

    expect(wrapper.html()).toContain('bg-k2-error')
  })

  it('should default to info class for unknown type', () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Unknown', type: 'unknown_type' }]

    const wrapper = mount(ToastContainer)

    expect(wrapper.html()).toContain('bg-k2-accent')
  })

  it('should render dismiss button', () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Dismissable', type: 'info' }]

    const wrapper = mount(ToastContainer)

    const button = wrapper.find('button')
    expect(button.exists()).toBe(true)
  })

  it('should remove toast on dismiss click', async () => {
    const ui = useUi()
    ui.toasts = [{ id: 1, message: 'Dismissable', type: 'info' }]

    const wrapper = mount(ToastContainer)

    await wrapper.find('button').trigger('click')

    expect(ui.toasts.length).toBe(0)
  })
})
