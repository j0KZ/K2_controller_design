import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import FolderBreadcrumb from './FolderBreadcrumb.vue'
import { useK2State } from '@/stores/k2State'
import { useUi } from '@/stores/ui'

const mockApi = {
  get: vi.fn(),
  put: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => mockApi,
}))

describe('FolderBreadcrumb', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockApi.put.mockResolvedValue({})
  })

  it('should render root button', () => {
    const k2State = useK2State()
    k2State.folder = 'MyFolder'

    const wrapper = mount(FolderBreadcrumb)

    const rootBtn = wrapper.find('button')
    expect(rootBtn.text()).toBe('/')
  })

  it('should display current folder name', () => {
    const k2State = useK2State()
    k2State.folder = 'Streaming'

    const wrapper = mount(FolderBreadcrumb)

    expect(wrapper.text()).toContain('Streaming')
  })

  it('should navigate to root on click', async () => {
    const k2State = useK2State()
    k2State.folder = 'MyFolder'

    const wrapper = mount(FolderBreadcrumb)

    await wrapper.find('button').trigger('click')

    expect(mockApi.put).toHaveBeenCalledWith('/k2/state/folder', { folder: null })
  })

  it('should update state on successful navigation', async () => {
    const k2State = useK2State()
    k2State.folder = 'MyFolder'

    const wrapper = mount(FolderBreadcrumb)

    await wrapper.find('button').trigger('click')
    await vi.dynamicImportSettled()

    expect(k2State.folder).toBeNull()
  })

  it('should show toast on navigation error', async () => {
    mockApi.put.mockRejectedValueOnce(new Error('Nav error'))

    const k2State = useK2State()
    k2State.folder = 'MyFolder'
    const ui = useUi()

    const wrapper = mount(FolderBreadcrumb)

    await wrapper.find('button').trigger('click')
    await new Promise(r => setTimeout(r, 10))

    expect(ui.toasts.some(t => t.message.includes('Failed to navigate'))).toBe(true)
  })

  it('should render separator', () => {
    const k2State = useK2State()
    k2State.folder = 'Test'

    const wrapper = mount(FolderBreadcrumb)

    expect(wrapper.text()).toContain('>')
  })
})
