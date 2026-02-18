import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useConfig } from './config'

// Mock useApi
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue({
      mappings: {
        note_on: { 36: { name: 'Test', action: 'hotkey' } },
        cc_absolute: { 1: { name: 'Volume', action: 'volume' } },
        cc_relative: { 2: { name: 'Scroll', action: 'mouse_scroll' } },
      },
    }),
    put: vi.fn().mockResolvedValue({ success: true }),
    post: vi.fn().mockResolvedValue({ valid: true }),
  }),
}))

describe('useConfig store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with default state', () => {
    const config = useConfig()

    expect(config.config).toBeNull()
    expect(config.dirty).toBe(false)
    expect(config.loading).toBe(false)
    expect(config.error).toBeNull()
  })

  it('should fetch config', async () => {
    const config = useConfig()

    await config.fetchConfig()

    expect(config.config).not.toBeNull()
    expect(config.config.mappings.note_on[36].name).toBe('Test')
    expect(config.dirty).toBe(false)
  })

  it('should get mapping for button control', () => {
    const config = useConfig()
    config.config = {
      mappings: {
        note_on: { 36: { name: 'Test Button', action: 'hotkey' } },
      },
    }

    const mapping = config.getMappingForControl({ note: 36 })

    expect(mapping.name).toBe('Test Button')
  })

  it('should get mapping for encoder push', () => {
    const config = useConfig()
    config.config = {
      mappings: {
        note_on: { 40: { name: 'Encoder Push', action: 'hotkey' } },
      },
    }

    const mapping = config.getMappingForControl({ pushNote: 40 })

    expect(mapping.name).toBe('Encoder Push')
  })

  it('should get mapping for CC absolute control', () => {
    const config = useConfig()
    config.config = {
      mappings: {
        cc_absolute: { 1: { name: 'Fader', action: 'volume' } },
      },
    }

    const mapping = config.getMappingForControl({ cc: 1 })

    expect(mapping.name).toBe('Fader')
  })

  it('should get mapping for CC relative control', () => {
    const config = useConfig()
    config.config = {
      mappings: {
        cc_relative: { 2: { name: 'Encoder', action: 'mouse_scroll' } },
      },
    }

    const mapping = config.getMappingForControl({ cc: 2 })

    expect(mapping.name).toBe('Encoder')
  })

  it('should return null for unmapped control', () => {
    const config = useConfig()
    config.config = { mappings: {} }

    const mapping = config.getMappingForControl({ note: 999 })

    expect(mapping).toBeNull()
  })

  it('should return null when config is null', () => {
    const config = useConfig()

    const mapping = config.getMappingForControl({ note: 36 })

    expect(mapping).toBeNull()
  })

  it('should update mapping and set dirty', () => {
    const config = useConfig()
    config.config = { mappings: {} }

    config.updateMapping('note_on', 36, { name: 'New', action: 'hotkey' })

    expect(config.config.mappings.note_on[36].name).toBe('New')
    expect(config.dirty).toBe(true)
  })

  it('should create mapping type if not exists', () => {
    const config = useConfig()
    config.config = { mappings: {} }

    config.updateMapping('cc_absolute', 1, { name: 'Volume', action: 'volume' })

    expect(config.config.mappings.cc_absolute).toBeDefined()
    expect(config.config.mappings.cc_absolute[1].name).toBe('Volume')
  })

  it('should save config and clear dirty', async () => {
    const config = useConfig()
    config.config = { mappings: {} }
    config.dirty = true

    await config.saveConfig()

    expect(config.dirty).toBe(false)
    expect(config.loading).toBe(false)
  })

  it('should report hasUnsavedChanges', () => {
    const config = useConfig()

    expect(config.hasUnsavedChanges).toBe(false)

    config.dirty = true
    expect(config.hasUnsavedChanges).toBe(true)
  })

  it('should delete mapping and set dirty', () => {
    const config = useConfig()
    config.config = {
      mappings: {
        note_on: { 36: { name: 'Test', action: 'hotkey' } },
      },
    }

    config.deleteMapping('note_on', 36)

    expect(config.config.mappings.note_on[36]).toBeUndefined()
    expect(config.dirty).toBe(true)
  })

  it('should not throw when deleting non-existent mapping', () => {
    const config = useConfig()
    config.config = { mappings: {} }

    expect(() => config.deleteMapping('note_on', 999)).not.toThrow()
    expect(() => config.deleteMapping('nonexistent', 1)).not.toThrow()
  })

  it('should not crash updateMapping when config is null', () => {
    const config = useConfig()
    // config.config is null by default

    expect(() => config.updateMapping('note_on', 36, { name: 'X', action: 'hotkey' })).not.toThrow()
    expect(config.config).toBeNull()
    expect(config.dirty).toBe(false)
  })

  it('should initialize mappings object if missing', () => {
    const config = useConfig()
    config.config = {} // config exists but no mappings key

    config.updateMapping('note_on', 36, { name: 'New', action: 'hotkey' })

    expect(config.config.mappings).toBeDefined()
    expect(config.config.mappings.note_on[36].name).toBe('New')
    expect(config.dirty).toBe(true)
  })
})
