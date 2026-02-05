import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ProfileDropdown from './ProfileDropdown.vue'
import { useProfiles } from '@/stores/profiles'
import { useUi } from '@/stores/ui'

const mockApi = {
  get: vi.fn().mockResolvedValue({ profiles: [], active: 'default' }),
  put: vi.fn().mockResolvedValue({}),
  post: vi.fn().mockResolvedValue({}),
  del: vi.fn().mockResolvedValue({}),
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => mockApi,
}))

describe('ProfileDropdown', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockApi.get.mockResolvedValue({ profiles: [], active: 'default' })
  })

  it('should render active profile name', () => {
    const profiles = useProfiles()
    profiles.activeProfile = 'gaming'

    const wrapper = mount(ProfileDropdown)

    expect(wrapper.text()).toContain('gaming')
  })

  it('should toggle dropdown on click', async () => {
    const wrapper = mount(ProfileDropdown)

    // Dropdown should be closed initially
    expect(wrapper.find('.absolute').exists()).toBe(false)

    // Open dropdown
    await wrapper.find('button').trigger('click')

    expect(wrapper.find('.absolute').exists()).toBe(true)
  })

  it('should show profile list when open', async () => {
    const profiles = useProfiles()
    profiles.profiles = [
      { name: 'default', active: true },
      { name: 'gaming', active: false },
    ]

    const wrapper = mount(ProfileDropdown)

    await wrapper.find('button').trigger('click')

    expect(wrapper.text()).toContain('default')
    expect(wrapper.text()).toContain('gaming')
  })

  it('should show active indicator', async () => {
    const profiles = useProfiles()
    profiles.profiles = [
      { name: 'default', active: true },
    ]
    profiles.activeProfile = 'default'

    const wrapper = mount(ProfileDropdown)

    await wrapper.find('button').trigger('click')

    // Active profile should have the green dot indicator
    expect(wrapper.html()).toContain('text-k2-success')
  })

  it('should show New Profile button', async () => {
    const wrapper = mount(ProfileDropdown)

    await wrapper.find('button').trigger('click')

    expect(wrapper.text()).toContain('+ New Profile')
  })

  it('should show create form when New Profile clicked', async () => {
    const wrapper = mount(ProfileDropdown)

    // Open dropdown
    await wrapper.find('button').trigger('click')

    // Click New Profile
    const newBtn = wrapper.findAll('button').find(b => b.text().includes('+ New Profile'))
    await newBtn.trigger('click')

    // Should show input and Create/Cancel buttons
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Create')
    expect(wrapper.text()).toContain('Cancel')
  })

  it('should show copy from current checkbox in create form', async () => {
    const wrapper = mount(ProfileDropdown)

    await wrapper.find('button').trigger('click')

    const newBtn = wrapper.findAll('button').find(b => b.text().includes('+ New Profile'))
    await newBtn.trigger('click')

    expect(wrapper.text()).toContain('Copy from current profile')
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
  })

  it('should cancel create form', async () => {
    const wrapper = mount(ProfileDropdown)

    await wrapper.find('button').trigger('click')

    const newBtn = wrapper.findAll('button').find(b => b.text().includes('+ New Profile'))
    await newBtn.trigger('click')

    const cancelBtn = wrapper.findAll('button').find(b => b.text() === 'Cancel')
    await cancelBtn.trigger('click')

    // Should hide the form and show New Profile button again
    expect(wrapper.find('input[type="text"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('+ New Profile')
  })

  it('should disable Create button when name is empty', async () => {
    const wrapper = mount(ProfileDropdown)

    await wrapper.find('button').trigger('click')

    const newBtn = wrapper.findAll('button').find(b => b.text().includes('+ New Profile'))
    await newBtn.trigger('click')

    const createBtn = wrapper.findAll('button').find(b => b.text() === 'Create')
    expect(createBtn.attributes('disabled')).toBeDefined()
  })

  it('should close dropdown on outside click', async () => {
    const wrapper = mount(ProfileDropdown)

    // Open dropdown
    await wrapper.find('button').trigger('click')
    expect(wrapper.find('.absolute').exists()).toBe(true)

    // Click outside overlay
    const overlay = wrapper.find('.fixed.inset-0')
    await overlay.trigger('click')

    expect(wrapper.find('.absolute').exists()).toBe(false)
  })

  it('should render dropdown arrow', () => {
    const wrapper = mount(ProfileDropdown)

    expect(wrapper.text()).toContain('▼')
  })
})
