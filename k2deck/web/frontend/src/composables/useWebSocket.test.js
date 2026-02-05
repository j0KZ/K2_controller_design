import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock ReconnectingWebSocket
const mockWs = {
  onopen: null,
  onclose: null,
  onmessage: null,
  send: vi.fn(),
  close: vi.fn(),
  readyState: 1, // WebSocket.OPEN
}

vi.mock('reconnecting-websocket', () => ({
  default: vi.fn(() => mockWs),
}))

import { useWebSocket } from './useWebSocket'
import { useK2State } from '@/stores/k2State'
import { useAnalogState } from '@/stores/analogState'
import { useMidi } from '@/stores/midi'
import { useIntegrations } from '@/stores/integrations'
import { useProfiles } from '@/stores/profiles'

describe('useWebSocket', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockWs.onopen = null
    mockWs.onclose = null
    mockWs.onmessage = null
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { protocol: 'http:', host: 'localhost:5173' },
      writable: true,
    })
  })

  it('should return connect, disconnect, connected, and send', () => {
    const ws = useWebSocket()

    expect(ws.connect).toBeInstanceOf(Function)
    expect(ws.disconnect).toBeInstanceOf(Function)
    expect(ws.send).toBeInstanceOf(Function)
    expect(ws.connected).toBeDefined()
  })

  it('should set connected to true on open', () => {
    const ws = useWebSocket()
    ws.connect()

    // Simulate WebSocket open
    mockWs.onopen()

    expect(ws.connected.value).toBe(true)
  })

  it('should set connected to false on close', () => {
    const ws = useWebSocket()
    ws.connect()

    mockWs.onopen()
    mockWs.onclose()

    expect(ws.connected.value).toBe(false)
  })

  it('should handle midi_event message', () => {
    const ws = useWebSocket()
    ws.connect()

    const midi = useMidi()
    const addEventSpy = vi.spyOn(midi, 'addEvent')

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'midi_event',
        data: { type: 'note_on', channel: 16, note: 36, value: 127 },
      }),
    })

    expect(addEventSpy).toHaveBeenCalledWith({
      type: 'note_on', channel: 16, note: 36, value: 127,
    })
  })

  it('should handle led_change message', () => {
    const ws = useWebSocket()
    ws.connect()

    const k2State = useK2State()
    const spy = vi.spyOn(k2State, 'handleLedChange')

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'led_change',
        data: { note: 36, color: 'green', on: true },
      }),
    })

    expect(spy).toHaveBeenCalledWith({ note: 36, color: 'green', on: true })
  })

  it('should handle layer_change message', () => {
    const ws = useWebSocket()
    ws.connect()

    const k2State = useK2State()

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'layer_change',
        data: { layer: 2 },
      }),
    })

    expect(k2State.layer).toBe(2)
  })

  it('should handle folder_change message', () => {
    const ws = useWebSocket()
    ws.connect()

    const k2State = useK2State()

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'folder_change',
        data: { folder: 'Streaming' },
      }),
    })

    expect(k2State.folder).toBe('Streaming')
  })

  it('should handle connection_change message', () => {
    const ws = useWebSocket()
    ws.connect()

    const k2State = useK2State()

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'connection_change',
        data: { connected: true, port: 'XONE:K2' },
      }),
    })

    expect(k2State.connected).toBe(true)
    expect(k2State.port).toBe('XONE:K2')
  })

  it('should handle integration_change message', () => {
    const ws = useWebSocket()
    ws.connect()

    const integrations = useIntegrations()

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'integration_change',
        data: { name: 'obs', status: 'connected' },
      }),
    })

    expect(integrations.obs.connected).toBe(true)
    expect(integrations.obs.status).toBe('connected')
  })

  it('should handle profile_change message', () => {
    const ws = useWebSocket()
    ws.connect()

    const profiles = useProfiles()

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'profile_change',
        data: { profile: 'gaming' },
      }),
    })

    expect(profiles.activeProfile).toBe('gaming')
  })

  it('should handle analog_change message', () => {
    const ws = useWebSocket()
    ws.connect()

    const analogState = useAnalogState()

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'analog_change',
        data: { cc: 16, value: 100 },
      }),
    })

    expect(analogState.positions[16]).toBe(100)
  })

  it('should handle analog_state message', () => {
    const ws = useWebSocket()
    ws.connect()

    const analogState = useAnalogState()

    mockWs.onmessage({
      data: JSON.stringify({
        type: 'analog_state',
        data: { controls: [{ cc: 16, value: 50 }, { cc: 17, value: 100 }] },
      }),
    })

    expect(analogState.positions[16]).toBe(50)
    expect(analogState.positions[17]).toBe(100)
  })

  it('should send messages when connected', () => {
    const ws = useWebSocket()
    ws.connect()

    // Mock WebSocket.OPEN
    global.WebSocket = { OPEN: 1 }
    mockWs.readyState = 1

    ws.send('set_led', { note: 36, color: 'green' })

    expect(mockWs.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'set_led', data: { note: 36, color: 'green' } })
    )
  })

  it('should not send when ws is not open', () => {
    const ws = useWebSocket()
    ws.connect()

    global.WebSocket = { OPEN: 1 }
    mockWs.readyState = 3 // CLOSED

    ws.send('set_led', { note: 36, color: 'green' })

    expect(mockWs.send).not.toHaveBeenCalled()
  })

  it('should disconnect websocket', () => {
    const ws = useWebSocket()
    ws.connect()

    ws.disconnect()

    expect(mockWs.close).toHaveBeenCalled()
  })
})
