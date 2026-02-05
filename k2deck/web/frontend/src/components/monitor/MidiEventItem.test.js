import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MidiEventItem from './MidiEventItem.vue'

describe('MidiEventItem', () => {
  it('should render note_on event', () => {
    const wrapper = mount(MidiEventItem, {
      props: {
        event: {
          type: 'note_on',
          channel: 16,
          note: 36,
          value: 127,
          timestamp: Date.now(),
        },
      },
    })

    expect(wrapper.text()).toContain('note_on')
    expect(wrapper.text()).toContain('ch=16')
    expect(wrapper.text()).toContain('note=36')
    expect(wrapper.text()).toContain('val=127')
  })

  it('should render note_off event', () => {
    const wrapper = mount(MidiEventItem, {
      props: {
        event: {
          type: 'note_off',
          channel: 16,
          note: 36,
          value: 0,
          timestamp: Date.now(),
        },
      },
    })

    expect(wrapper.text()).toContain('note_off')
  })

  it('should render cc event', () => {
    const wrapper = mount(MidiEventItem, {
      props: {
        event: {
          type: 'cc',
          channel: 16,
          cc: 1,
          value: 64,
          timestamp: Date.now(),
        },
      },
    })

    expect(wrapper.text()).toContain('cc')
    expect(wrapper.text()).toContain('cc=1')
    expect(wrapper.text()).toContain('val=64')
  })

  it('should format timestamp', () => {
    const wrapper = mount(MidiEventItem, {
      props: {
        event: {
          type: 'note_on',
          channel: 16,
          note: 36,
          value: 127,
          timestamp: new Date('2024-01-01T12:30:45.123').getTime(),
        },
      },
    })

    // Should contain time in HH:MM:SS format
    expect(wrapper.text()).toMatch(/\d{2}:\d{2}:\d{2}/)
  })

  it('should apply correct class for note_on', () => {
    const wrapper = mount(MidiEventItem, {
      props: {
        event: {
          type: 'note_on',
          channel: 16,
          note: 36,
          value: 127,
          timestamp: Date.now(),
        },
      },
    })

    expect(wrapper.html()).toContain('text-k2-success')
  })

  it('should apply correct class for note_off', () => {
    const wrapper = mount(MidiEventItem, {
      props: {
        event: {
          type: 'note_off',
          channel: 16,
          note: 36,
          value: 0,
          timestamp: Date.now(),
        },
      },
    })

    expect(wrapper.html()).toContain('text-k2-error')
  })

  it('should apply correct class for cc', () => {
    const wrapper = mount(MidiEventItem, {
      props: {
        event: {
          type: 'cc',
          channel: 16,
          cc: 1,
          value: 64,
          timestamp: Date.now(),
        },
      },
    })

    expect(wrapper.html()).toContain('text-k2-accent')
  })
})
