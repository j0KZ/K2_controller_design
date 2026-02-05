import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMidi } from './midi'

describe('useMidi store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with empty events', () => {
    const midi = useMidi()
    expect(midi.events).toEqual([])
    expect(midi.paused).toBe(false)
    expect(midi.maxEvents).toBe(100)
  })

  it('should add events to the beginning', () => {
    const midi = useMidi()

    midi.addEvent({ type: 'note_on', note: 36, value: 127 })
    midi.addEvent({ type: 'note_off', note: 36, value: 0 })

    expect(midi.events).toHaveLength(2)
    expect(midi.events[0].type).toBe('note_off') // Most recent first
    expect(midi.events[1].type).toBe('note_on')
  })

  it('should add timestamp to events', () => {
    const midi = useMidi()

    midi.addEvent({ type: 'cc', cc: 1, value: 64 })

    expect(midi.events[0].timestamp).toBeDefined()
    expect(typeof midi.events[0].timestamp).toBe('number')
  })

  it('should not add events when paused', () => {
    const midi = useMidi()

    midi.togglePause()
    midi.addEvent({ type: 'note_on', note: 36, value: 127 })

    expect(midi.events).toHaveLength(0)
    expect(midi.paused).toBe(true)
  })

  it('should toggle pause state', () => {
    const midi = useMidi()

    expect(midi.paused).toBe(false)
    midi.togglePause()
    expect(midi.paused).toBe(true)
    midi.togglePause()
    expect(midi.paused).toBe(false)
  })

  it('should clear all events', () => {
    const midi = useMidi()

    midi.addEvent({ type: 'note_on', note: 36, value: 127 })
    midi.addEvent({ type: 'note_on', note: 37, value: 127 })

    midi.clear()

    expect(midi.events).toHaveLength(0)
  })

  it('should limit events to maxEvents', () => {
    const midi = useMidi()
    midi.maxEvents = 5

    for (let i = 0; i < 10; i++) {
      midi.addEvent({ type: 'note_on', note: i, value: 127 })
    }

    expect(midi.events).toHaveLength(5)
    expect(midi.events[0].note).toBe(9) // Most recent
    expect(midi.events[4].note).toBe(5) // Oldest remaining
  })
})
