import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useK2State } from './k2State'

// Mock useApi with controllable responses
const mockGet = vi.fn()
const mockPut = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    get: mockGet,
    put: mockPut,
  }),
}))

describe('useK2State store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should initialize with default state', () => {
    const k2State = useK2State()

    expect(k2State.layout).toBeNull()
    expect(k2State.connected).toBe(false)
    expect(k2State.port).toBeNull()
    expect(k2State.layer).toBe(1)
    expect(k2State.folder).toBeNull()
    expect(k2State.leds).toEqual({})
    expect(k2State.loading).toBe(false)
    expect(k2State.error).toBeNull()
  })

  it('should set layer', () => {
    const k2State = useK2State()

    k2State.setLayer(2)
    expect(k2State.layer).toBe(2)

    k2State.setLayer(3)
    expect(k2State.layer).toBe(3)
  })

  it('should set folder', () => {
    const k2State = useK2State()

    k2State.setFolder('macros')
    expect(k2State.folder).toBe('macros')

    k2State.setFolder(null)
    expect(k2State.folder).toBeNull()
  })

  it('should set connection', () => {
    const k2State = useK2State()

    k2State.setConnection(true, 'XONE:K2')

    expect(k2State.connected).toBe(true)
    expect(k2State.port).toBe('XONE:K2')
  })

  it('should handle LED change - turn on', () => {
    const k2State = useK2State()

    k2State.handleLedChange({ note: 36, on: true, color: 'green' })

    expect(k2State.leds[36]).toBe('green')
  })

  it('should handle LED change - turn off', () => {
    const k2State = useK2State()

    k2State.leds[36] = 'green'
    k2State.handleLedChange({ note: 36, on: false })

    expect(k2State.leds[36]).toBeUndefined()
  })

  it('should get LED state', () => {
    const k2State = useK2State()

    expect(k2State.getLedState(36)).toBeNull()

    k2State.leds[36] = 'red'
    expect(k2State.getLedState(36)).toBe('red')
  })

  it('should get isConnected getter', () => {
    const k2State = useK2State()

    expect(k2State.isConnected).toBe(false)

    k2State.connected = true
    expect(k2State.isConnected).toBe(true)
  })

  it('should get empty rows when layout is null', () => {
    const k2State = useK2State()

    expect(k2State.getRows).toEqual([])
  })

  it('should get rows from layout', () => {
    const k2State = useK2State()

    k2State.layout = {
      rows: [
        { type: 'encoders', controls: [] },
        { type: 'buttons', controls: [] },
      ],
    }

    expect(k2State.getRows).toHaveLength(2)
    expect(k2State.getRows[0].type).toBe('encoders')
  })

  // --- NEW: async actions ---

  it('should fetchLayout successfully', async () => {
    const layoutData = {
      rows: [{ type: 'button-row', controls: [{ id: 'A', type: 'button' }] }],
      totalControls: 1,
    }
    mockGet.mockResolvedValueOnce(layoutData)

    const k2State = useK2State()
    await k2State.fetchLayout()

    expect(mockGet).toHaveBeenCalledWith('/k2/layout')
    expect(k2State.layout).toEqual(layoutData)
    expect(k2State.error).toBeNull()
  })

  it('should handle fetchLayout error', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network error'))

    const k2State = useK2State()
    await k2State.fetchLayout()

    expect(k2State.layout).toBeNull()
    expect(k2State.error).toBe('Network error')
  })

  it('should fetchState successfully', async () => {
    const stateData = {
      connected: true,
      port: 'XONE:K2',
      layer: 2,
      folder: 'macros',
      leds: { 36: 'green', 37: 'red' },
    }
    mockGet.mockResolvedValueOnce(stateData)

    const k2State = useK2State()
    await k2State.fetchState()

    expect(mockGet).toHaveBeenCalledWith('/k2/state')
    expect(k2State.connected).toBe(true)
    expect(k2State.port).toBe('XONE:K2')
    expect(k2State.layer).toBe(2)
    expect(k2State.folder).toBe('macros')
    expect(k2State.leds).toEqual({ 36: 'green', 37: 'red' })
  })

  it('should handle fetchState error', async () => {
    mockGet.mockRejectedValueOnce(new Error('Server down'))

    const k2State = useK2State()
    await k2State.fetchState()

    expect(k2State.error).toBe('Server down')
    expect(k2State.connected).toBe(false)
  })

  it('should setLed via API', async () => {
    mockPut.mockResolvedValueOnce({})

    const k2State = useK2State()
    await k2State.setLed(36, 'green')

    expect(mockPut).toHaveBeenCalledWith('/k2/state/leds/36', {
      note: 36,
      color: 'green',
      on: true,
    })
  })

  it('should setLed off via API', async () => {
    mockPut.mockResolvedValueOnce({})

    const k2State = useK2State()
    await k2State.setLed(36, null)

    expect(mockPut).toHaveBeenCalledWith('/k2/state/leds/36', {
      note: 36,
      color: null,
      on: false,
    })
  })
})
