import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAnalogState } from './analogState'

describe('useAnalogState store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with empty positions', () => {
    const analog = useAnalogState()
    expect(analog.positions).toEqual({})
  })

  it('should handle analog change', () => {
    const analog = useAnalogState()

    analog.handleChange(1, 64)

    expect(analog.positions[1]).toBe(64)
  })

  it('should get position with default 0', () => {
    const analog = useAnalogState()

    expect(analog.getPosition(999)).toBe(0)

    analog.handleChange(1, 127)
    expect(analog.getPosition(1)).toBe(127)
  })

  it('should calculate percent correctly', () => {
    const analog = useAnalogState()

    analog.handleChange(1, 0)
    expect(analog.getPercent(1)).toBe(0)

    analog.handleChange(2, 127)
    expect(analog.getPercent(2)).toBe(100)

    analog.handleChange(3, 64)
    expect(analog.getPercent(3)).toBe(50) // 64/127 ≈ 50%
  })

  it('should initialize from state', () => {
    const analog = useAnalogState()

    analog.initFromState([
      { cc: 1, value: 100 },
      { cc: 2, value: 50 },
      { cc: 3, value: 25 },
    ])

    expect(analog.positions[1]).toBe(100)
    expect(analog.positions[2]).toBe(50)
    expect(analog.positions[3]).toBe(25)
  })

  it('should update existing positions on change', () => {
    const analog = useAnalogState()

    analog.handleChange(1, 50)
    expect(analog.positions[1]).toBe(50)

    analog.handleChange(1, 100)
    expect(analog.positions[1]).toBe(100)
  })
})
