import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import MidiMonitor from './MidiMonitor.vue'
import { useMidi } from '@/stores/midi'

describe('MidiMonitor', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should render monitor panel', () => {
    const wrapper = mount(MidiMonitor)

    expect(wrapper.text()).toContain('MIDI Monitor')
  })

  it('should show waiting message when no events', () => {
    const wrapper = mount(MidiMonitor)

    expect(wrapper.text()).toContain('Waiting for MIDI events')
  })

  it('should render pause button', () => {
    const wrapper = mount(MidiMonitor)

    const pauseBtn = wrapper.findAll('button').find(b => b.text() === 'Pause')
    expect(pauseBtn).toBeDefined()
  })

  it('should render clear button', () => {
    const wrapper = mount(MidiMonitor)

    const clearBtn = wrapper.findAll('button').find(b => b.text() === 'Clear')
    expect(clearBtn).toBeDefined()
  })

  it('should toggle pause state', async () => {
    const wrapper = mount(MidiMonitor)
    const midi = useMidi()

    expect(midi.paused).toBe(false)

    const pauseBtn = wrapper.findAll('button').find(b => b.text() === 'Pause')
    await pauseBtn.trigger('click')

    expect(midi.paused).toBe(true)
    expect(wrapper.text()).toContain('Resume')
  })

  it('should clear events', async () => {
    const midi = useMidi()
    midi.addEvent({ type: 'note_on', note: 36, value: 127 })

    const wrapper = mount(MidiMonitor)

    const clearBtn = wrapper.findAll('button').find(b => b.text() === 'Clear')
    await clearBtn.trigger('click')

    expect(midi.events).toHaveLength(0)
  })

  it('should display events when present', () => {
    const midi = useMidi()
    midi.addEvent({ type: 'note_on', channel: 16, note: 36, value: 127 })

    const wrapper = mount(MidiMonitor)

    expect(wrapper.text()).not.toContain('Waiting for MIDI events')
  })
})
