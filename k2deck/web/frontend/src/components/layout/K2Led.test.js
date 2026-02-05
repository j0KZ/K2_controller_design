import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import K2Led from './K2Led.vue'

describe('K2Led', () => {
  it('should render with off state by default', () => {
    const wrapper = mount(K2Led, {
      props: { color: null },
    })

    expect(wrapper.classes()).toContain('bg-led-off')
    expect(wrapper.classes()).not.toContain('led-glow')
  })

  it('should render red LED', () => {
    const wrapper = mount(K2Led, {
      props: { color: 'red' },
    })

    expect(wrapper.classes()).toContain('led-glow')
    // Style can be hex or rgb depending on environment
    expect(wrapper.element.style.backgroundColor).toMatch(/(#ff3333|rgb\(255,\s*51,\s*51\))/)
  })

  it('should render amber LED', () => {
    const wrapper = mount(K2Led, {
      props: { color: 'amber' },
    })

    expect(wrapper.classes()).toContain('led-glow')
    expect(wrapper.element.style.backgroundColor).toMatch(/(#ffaa00|rgb\(255,\s*170,\s*0\))/)
  })

  it('should render green LED', () => {
    const wrapper = mount(K2Led, {
      props: { color: 'green' },
    })

    expect(wrapper.classes()).toContain('led-glow')
    expect(wrapper.element.style.backgroundColor).toMatch(/(#00ff66|rgb\(0,\s*255,\s*102\))/)
  })

  it('should have transition classes', () => {
    const wrapper = mount(K2Led)

    expect(wrapper.classes()).toContain('transition-all')
    expect(wrapper.classes()).toContain('duration-150')
  })

  it('should have correct size classes', () => {
    const wrapper = mount(K2Led)

    expect(wrapper.classes()).toContain('w-3')
    expect(wrapper.classes()).toContain('h-3')
    expect(wrapper.classes()).toContain('rounded-full')
  })
})
