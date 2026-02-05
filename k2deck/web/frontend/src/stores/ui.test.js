import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUi } from './ui'

describe('useUi store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should initialize with default state', () => {
    const ui = useUi()
    expect(ui.selectedControl).toBeNull()
    expect(ui.selectedLayer).toBe(1)
    expect(ui.toasts).toEqual([])
  })

  it('should select a control', () => {
    const ui = useUi()
    const control = { id: 'A1', type: 'button', note: 36 }

    ui.selectControl(control)

    expect(ui.selectedControl).toEqual(control)
  })

  it('should clear selection', () => {
    const ui = useUi()
    ui.selectControl({ id: 'A1' })

    ui.clearSelection()

    expect(ui.selectedControl).toBeNull()
  })

  it('should add a toast with auto-remove', () => {
    const ui = useUi()

    ui.addToast('Test message', 'success', 3000)

    expect(ui.toasts).toHaveLength(1)
    expect(ui.toasts[0].message).toBe('Test message')
    expect(ui.toasts[0].type).toBe('success')

    // Fast-forward timer
    vi.advanceTimersByTime(3000)

    expect(ui.toasts).toHaveLength(0)
  })

  it('should remove toast manually', () => {
    const ui = useUi()

    // Add first toast
    vi.setSystemTime(1000)
    ui.addToast('Test 1', 'info')

    // Add second toast with different timestamp
    vi.setSystemTime(2000)
    ui.addToast('Test 2', 'error')

    expect(ui.toasts).toHaveLength(2)

    // Remove the first toast
    const firstId = ui.toasts[0].id
    ui.removeToast(firstId)

    expect(ui.toasts).toHaveLength(1)
    expect(ui.toasts[0].message).toBe('Test 2')
  })

  it('should use info as default toast type', () => {
    const ui = useUi()

    ui.addToast('Default type')

    expect(ui.toasts[0].type).toBe('info')
  })
})
