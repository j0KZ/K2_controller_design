import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ActionForm from './ActionForm.vue'

describe('ActionForm', () => {
  it('should render hotkey form', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'hotkey',
        modelValue: { keys: ['ctrl', 'c'] },
      },
    })

    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input').element.value).toBe('ctrl + c')
  })

  it('should render volume form', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'volume',
        modelValue: { target_process: 'Discord.exe' },
      },
    })

    expect(wrapper.find('input').element.value).toBe('Discord.exe')
  })

  it('should render obs_scene form', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'obs_scene',
        modelValue: { scene: 'Gaming' },
      },
    })

    expect(wrapper.find('input').element.value).toBe('Gaming')
  })

  it('should render noop message', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'noop',
        modelValue: {},
      },
    })

    expect(wrapper.text()).toContain('No operation')
  })

  it('should emit update on hotkey change', async () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'hotkey',
        modelValue: {},
      },
    })

    await wrapper.find('input').setValue('ctrl + v')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0][0].keys).toEqual(['ctrl', 'v'])
  })

  it('should render mouse_scroll form with step', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'mouse_scroll',
        modelValue: { step: 5 },
      },
    })

    const stepInput = wrapper.find('input[type="number"]')
    expect(stepInput.exists()).toBe(true)
    // Input values can be number or string depending on environment
    expect(Number(stepInput.element.value)).toBe(5)
  })

  it('should render obs_stream select', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'obs_stream',
        modelValue: { action: 'toggle' },
      },
    })

    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.find('option[value="start"]').exists()).toBe(true)
    expect(wrapper.find('option[value="stop"]').exists()).toBe(true)
  })

  it('should render spotify_play_pause info message', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'spotify_play_pause',
        modelValue: {},
      },
    })

    expect(wrapper.text()).toContain('Toggles Spotify playback')
    expect(wrapper.text()).toContain('No configuration needed')
  })

  it('should render twitch_ad duration select', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'twitch_ad',
        modelValue: { duration: 60 },
      },
    })

    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.find('option[value="30"]').exists()).toBe(true)
    expect(wrapper.find('option[value="180"]').exists()).toBe(true)
  })

  it('should render tts form fields', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'tts',
        modelValue: { text: 'Hello', voice: 'default' },
      },
    })

    const inputs = wrapper.findAll('input')
    expect(inputs).toHaveLength(2)
    expect(inputs[0].element.value).toBe('Hello')
  })

  it('should format action name correctly', () => {
    const wrapper = mount(ActionForm, {
      props: {
        actionType: 'unknown_action_type',
        modelValue: {},
      },
    })

    expect(wrapper.text()).toContain('Unknown Action Type')
  })
})
