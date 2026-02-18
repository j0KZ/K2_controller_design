import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ActionCatalog from './ActionCatalog.vue'

// Mock useDragDrop composable
const mockOnCatalogDragStart = vi.fn()
vi.mock('@/composables/useDragDrop', () => ({
  useDragDrop: () => ({
    onCatalogDragStart: mockOnCatalogDragStart,
  }),
  formatName: (type) =>
    type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
}))

describe('ActionCatalog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders heading and search input', () => {
    const wrapper = mount(ActionCatalog)

    expect(wrapper.find('h2').text()).toBe('Action Catalog')
    expect(wrapper.find('input[placeholder="Search actions..."]').exists()).toBe(true)
  })

  it('renders all category headers', () => {
    const wrapper = mount(ActionCatalog)
    const headers = wrapper.findAll('h3').map((h) => h.text())

    expect(headers).toContain('Media')
    expect(headers).toContain('System')
    expect(headers).toContain('Audio')
    expect(headers).toContain('OBS')
    expect(headers).toContain('Twitch')
    expect(headers).toContain('OSC')
    expect(headers).toContain('Timers')
    expect(headers).toContain('Advanced')
    expect(headers).toContain('Utility')
  })

  it('renders draggable action cards', () => {
    const wrapper = mount(ActionCatalog)
    const cards = wrapper.findAll('[draggable="true"]')

    expect(cards.length).toBeGreaterThan(0)
  })

  it('displays formatted action names on cards', () => {
    const wrapper = mount(ActionCatalog)

    expect(wrapper.text()).toContain('Spotify Play Pause')
    expect(wrapper.text()).toContain('Hotkey')
    expect(wrapper.text()).toContain('Noop')
  })

  it('filters actions by search query', async () => {
    const wrapper = mount(ActionCatalog)
    await wrapper.find('input').setValue('spotify')

    const cards = wrapper.findAll('.action-card')
    expect(cards.length).toBeGreaterThan(0)
    cards.forEach((card) => {
      expect(card.text().toLowerCase()).toContain('spotify')
    })
  })

  it('filters by category name', async () => {
    const wrapper = mount(ActionCatalog)
    await wrapper.find('input').setValue('obs')

    const cards = wrapper.findAll('.action-card')
    expect(cards.length).toBe(5) // obs_scene, obs_source_toggle, obs_stream, obs_record, obs_mute
  })

  it('shows empty state when no results', async () => {
    const wrapper = mount(ActionCatalog)
    await wrapper.find('input').setValue('xyznonexistent')

    expect(wrapper.text()).toContain('No actions match')
    expect(wrapper.text()).toContain('xyznonexistent')
  })

  it('calls onCatalogDragStart on card dragstart', async () => {
    const wrapper = mount(ActionCatalog)
    const card = wrapper.find('.action-card')

    await card.trigger('dragstart')

    expect(mockOnCatalogDragStart).toHaveBeenCalled()
  })

  it('shows all actions when search is empty', async () => {
    const wrapper = mount(ActionCatalog)

    // 48 actions across 9 groups = all backend ACTION_TYPES
    const cards = wrapper.findAll('.action-card')
    expect(cards.length).toBe(48)
  })
})
