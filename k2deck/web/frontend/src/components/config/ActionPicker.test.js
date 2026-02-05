import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ActionPicker from './ActionPicker.vue'

describe('ActionPicker', () => {
  it('should render select with empty default', () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: '' },
    })

    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.find('select').element.value).toBe('')
  })

  it('should render all action categories', () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: '' },
    })

    const optgroups = wrapper.findAll('optgroup')
    expect(optgroups.length).toBeGreaterThanOrEqual(5)

    const labels = optgroups.map(og => og.attributes('label'))
    expect(labels).toContain('Media')
    expect(labels).toContain('System')
    expect(labels).toContain('OBS')
    expect(labels).toContain('Twitch')
    expect(labels).toContain('Advanced')
  })

  it('should render media actions', () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: '' },
    })

    expect(wrapper.find('option[value="spotify_play_pause"]').exists()).toBe(true)
    expect(wrapper.find('option[value="spotify_next"]').exists()).toBe(true)
    expect(wrapper.find('option[value="spotify_previous"]').exists()).toBe(true)
  })

  it('should render system actions', () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: '' },
    })

    expect(wrapper.find('option[value="hotkey"]').exists()).toBe(true)
    expect(wrapper.find('option[value="volume"]').exists()).toBe(true)
    expect(wrapper.find('option[value="mouse_scroll"]').exists()).toBe(true)
  })

  it('should render OBS actions', () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: '' },
    })

    expect(wrapper.find('option[value="obs_scene"]').exists()).toBe(true)
    expect(wrapper.find('option[value="obs_source_toggle"]').exists()).toBe(true)
    expect(wrapper.find('option[value="obs_stream"]').exists()).toBe(true)
    expect(wrapper.find('option[value="obs_record"]').exists()).toBe(true)
  })

  it('should emit update on change', async () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: '' },
    })

    await wrapper.find('select').setValue('hotkey')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['hotkey'])
  })

  it('should show selected value', () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: 'spotify_play_pause' },
    })

    expect(wrapper.find('select').element.value).toBe('spotify_play_pause')
  })

  it('should format action names correctly', () => {
    const wrapper = mount(ActionPicker, {
      props: { modelValue: '' },
    })

    const spotifyOption = wrapper.find('option[value="spotify_play_pause"]')
    expect(spotifyOption.text()).toBe('Spotify Play Pause')
  })
})
