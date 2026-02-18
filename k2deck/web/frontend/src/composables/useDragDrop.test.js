import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock useApi (config store uses it in saveConfig/fetchConfig)
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue({ mappings: {} }),
    put: vi.fn().mockResolvedValue({ success: true }),
    post: vi.fn().mockResolvedValue({}),
  }),
}))

import {
  useDragDrop,
  CC_ONLY_ACTIONS,
  NOTE_ONLY_ACTIONS,
  isDropCompatible,
  formatName,
  defaultMapping,
} from './useDragDrop'
import { useConfig } from '@/stores/config'
import { useUi } from '@/stores/ui'

function createMockDragEvent(type, opts = {}) {
  const event = new Event(type, { bubbles: true })
  event.dataTransfer = {
    setData: vi.fn(),
    getData: vi.fn(),
    effectAllowed: 'none',
    dropEffect: 'none',
  }
  event.preventDefault = vi.fn()
  // ctrlKey, currentTarget, relatedTarget are read-only in happy-dom
  Object.defineProperty(event, 'ctrlKey', {
    value: opts.ctrlKey || false,
    configurable: true,
  })
  if (opts.currentTarget !== undefined) {
    Object.defineProperty(event, 'currentTarget', {
      value: opts.currentTarget,
      configurable: true,
    })
  }
  if (opts.relatedTarget !== undefined) {
    Object.defineProperty(event, 'relatedTarget', {
      value: opts.relatedTarget,
      configurable: true,
    })
  }
  return event
}

// Test controls
const button = { id: 'A1', type: 'button', note: 36 }
const button2 = { id: 'A2', type: 'button', note: 37 }
const fader = { id: 'F1', type: 'fader', cc: 1 }
const encoder = { id: 'E1', type: 'encoder', cc: 2, pushNote: 40 }
const layerBtn = { id: 'LAYER', type: 'button', note: 15, special: 'layer' }

describe('useDragDrop', () => {
  let dragDrop, config, ui

  beforeEach(() => {
    setActivePinia(createPinia())
    config = useConfig()
    ui = useUi()
    dragDrop = useDragDrop()
    dragDrop.resetDragState()
  })

  // --- Pure functions ---

  describe('formatName', () => {
    it('converts snake_case to Title Case', () => {
      expect(formatName('spotify_play_pause')).toBe('Spotify Play Pause')
      expect(formatName('hotkey')).toBe('Hotkey')
      expect(formatName('obs_scene')).toBe('Obs Scene')
    })
  })

  describe('defaultMapping', () => {
    it('creates mapping with name and action', () => {
      expect(defaultMapping('spotify_play_pause')).toEqual({
        name: 'Spotify Play Pause',
        action: 'spotify_play_pause',
      })
    })
  })

  describe('isDropCompatible', () => {
    it('blocks CC-only action on button', () => {
      expect(isDropCompatible('volume', button)).toBe(false)
      expect(isDropCompatible('hotkey_relative', button)).toBe(false)
      expect(isDropCompatible('mouse_scroll', button)).toBe(false)
    })

    it('blocks note-only action on CC control', () => {
      expect(isDropCompatible('spotify_play_pause', fader)).toBe(false)
      expect(isDropCompatible('multi', encoder)).toBe(false)
      expect(isDropCompatible('folder', fader)).toBe(false)
    })

    it('allows dual-mode action on any control', () => {
      expect(isDropCompatible('hotkey', button)).toBe(true)
      expect(isDropCompatible('hotkey', fader)).toBe(true)
      expect(isDropCompatible('noop', encoder)).toBe(true)
      expect(isDropCompatible('conditional', button)).toBe(true)
    })

    it('allows CC-only on CC control and note-only on button', () => {
      expect(isDropCompatible('volume', fader)).toBe(true)
      expect(isDropCompatible('mouse_scroll', encoder)).toBe(true)
      expect(isDropCompatible('spotify_play_pause', button)).toBe(true)
      expect(isDropCompatible('multi', button)).toBe(true)
    })

    it('allows unknown action type on any control', () => {
      expect(isDropCompatible('unknown_future', button)).toBe(true)
      expect(isDropCompatible('unknown_future', fader)).toBe(true)
    })
  })

  describe('compatibility sets', () => {
    it('CC_ONLY has 8 actions', () => {
      expect(CC_ONLY_ACTIONS.size).toBe(8)
    })

    it('NOTE_ONLY has 36 actions', () => {
      expect(NOTE_ONLY_ACTIONS.size).toBe(36)
    })
  })

  // --- State ---

  describe('initial state', () => {
    it('has clean default state', () => {
      expect(dragDrop.state.isDragging).toBe(false)
      expect(dragDrop.state.dragType).toBeNull()
      expect(dragDrop.state.dragPayload).toBeNull()
      expect(dragDrop.state.dragOverControlId).toBeNull()
    })
  })

  // --- Catalog drag start ---

  describe('onCatalogDragStart', () => {
    it('sets drag state for catalog', () => {
      const event = createMockDragEvent('dragstart')
      dragDrop.onCatalogDragStart(event, 'hotkey')

      expect(dragDrop.state.isDragging).toBe(true)
      expect(dragDrop.state.dragType).toBe('catalog')
      expect(dragDrop.state.dragPayload).toBe('hotkey')
      expect(event.dataTransfer.effectAllowed).toBe('copy')
      expect(event.dataTransfer.setData).toHaveBeenCalledWith('text/plain', 'hotkey')
    })
  })

  // --- Control drag start ---

  describe('onControlDragStart', () => {
    it('starts drag when control has mapping', () => {
      config.config = { mappings: { note_on: { 36: { name: 'Test', action: 'hotkey' } } } }
      const event = createMockDragEvent('dragstart')

      dragDrop.onControlDragStart(event, button)

      expect(dragDrop.state.isDragging).toBe(true)
      expect(dragDrop.state.dragType).toBe('control')
      expect(dragDrop.state.dragPayload).toEqual(button)
      expect(event.dataTransfer.effectAllowed).toBe('copyMove')
    })

    it('prevents drag when control has no mapping', () => {
      config.config = { mappings: {} }
      const event = createMockDragEvent('dragstart')

      dragDrop.onControlDragStart(event, button)

      expect(dragDrop.state.isDragging).toBe(false)
      expect(event.preventDefault).toHaveBeenCalled()
    })

    it('no-ops when config is null', () => {
      config.config = null
      const event = createMockDragEvent('dragstart')

      dragDrop.onControlDragStart(event, button)

      expect(dragDrop.state.isDragging).toBe(false)
    })

    it('no-ops on special control', () => {
      config.config = { mappings: { note_on: { 15: { name: 'L', action: 'noop' } } } }
      const event = createMockDragEvent('dragstart')

      dragDrop.onControlDragStart(event, layerBtn)

      expect(dragDrop.state.isDragging).toBe(false)
    })
  })

  // --- Drag over / enter / leave ---

  describe('onDragOver', () => {
    it('sets dragOverControlId and prevents default', () => {
      const event = createMockDragEvent('dragover')
      dragDrop.onDragOver(event, button)

      expect(dragDrop.state.dragOverControlId).toBe('A1')
      expect(event.preventDefault).toHaveBeenCalled()
    })

    it('no-ops on special control', () => {
      const event = createMockDragEvent('dragover')
      dragDrop.onDragOver(event, layerBtn)

      expect(dragDrop.state.dragOverControlId).toBeNull()
      expect(event.preventDefault).not.toHaveBeenCalled()
    })
  })

  describe('onDragLeave', () => {
    it('clears dragOverControlId', () => {
      dragDrop.state.dragOverControlId = 'A1'
      const event = createMockDragEvent('dragleave')

      dragDrop.onDragLeave(event, button)

      expect(dragDrop.state.dragOverControlId).toBeNull()
    })

    it('does not clear if leaving to child element', () => {
      dragDrop.state.dragOverControlId = 'A1'
      const parent = document.createElement('div')
      const child = document.createElement('span')
      parent.appendChild(child)

      const event = createMockDragEvent('dragleave', {
        currentTarget: parent,
        relatedTarget: child,
      })

      dragDrop.onDragLeave(event, button)

      expect(dragDrop.state.dragOverControlId).toBe('A1')
    })
  })

  // --- Getters ---

  describe('isDragOver', () => {
    it('returns true when dragging over matching control', () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragOverControlId = 'A1'
      expect(dragDrop.isDragOver('A1')).toBe(true)
    })

    it('returns false when not dragging', () => {
      dragDrop.state.isDragging = false
      dragDrop.state.dragOverControlId = 'A1'
      expect(dragDrop.isDragOver('A1')).toBe(false)
    })
  })

  describe('isSourceControl', () => {
    it('returns true for source control during control drag', () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button
      expect(dragDrop.isSourceControl('A1')).toBe(true)
    })

    it('returns false for catalog drag type', () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'
      expect(dragDrop.isSourceControl('A1')).toBe(false)
    })
  })

  // --- onDragEnd ---

  describe('onDragEnd', () => {
    it('resets all drag state', () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'
      dragDrop.state.dragOverControlId = 'A1'

      dragDrop.onDragEnd()

      expect(dragDrop.state.isDragging).toBe(false)
      expect(dragDrop.state.dragType).toBeNull()
      expect(dragDrop.state.dragPayload).toBeNull()
      expect(dragDrop.state.dragOverControlId).toBeNull()
    })
  })

  // --- Catalog drop ---

  describe('catalog drop', () => {
    beforeEach(() => {
      config.config = { mappings: { note_on: {} } }
      config.saveConfig = vi.fn().mockResolvedValue()
    })

    it('assigns action to empty button', async () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(config.config.mappings.note_on[36]).toEqual({
        name: 'Hotkey',
        action: 'hotkey',
      })
      expect(config.saveConfig).toHaveBeenCalled()
      expect(ui.selectedControl).toEqual(button)
      expect(ui.toasts[0].type).toBe('success')
    })

    it('rejects incompatible drop with warning toast', async () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'volume' // CC-only → button

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(config.saveConfig).not.toHaveBeenCalled()
      expect(ui.toasts[0].type).toBe('warning')
      expect(ui.toasts[0].message).toContain('not compatible')
    })

    it('blocks drop on special control', async () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'

      await dragDrop.onDrop(createMockDragEvent('drop'), layerBtn)

      expect(config.saveConfig).not.toHaveBeenCalled()
    })

    it('blocks drop when config is dirty', async () => {
      config.dirty = true
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(config.saveConfig).not.toHaveBeenCalled()
      expect(ui.toasts[0].message).toContain('Save or revert')
    })

    it('overwrites existing mapping', async () => {
      config.config.mappings.note_on[36] = { name: 'Old', action: 'noop' }
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(config.config.mappings.note_on[36].action).toBe('hotkey')
    })

    it('rolls back existing mapping on save failure', async () => {
      config.config.mappings.note_on[36] = { name: 'Old', action: 'noop' }
      config.saveConfig = vi.fn().mockRejectedValue(new Error('Network'))
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(config.config.mappings.note_on[36]).toEqual({ name: 'Old', action: 'noop' })
      expect(ui.toasts[0].type).toBe('error')
      expect(ui.selectedControl).toBeNull()
    })

    it('deletes mapping on save failure when target was empty', async () => {
      config.saveConfig = vi.fn().mockRejectedValue(new Error('Network'))
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(config.config.mappings.note_on[36]).toBeUndefined()
    })

    it('force-refreshes when target already selected', async () => {
      ui.selectControl(button)
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'catalog'
      dragDrop.state.dragPayload = 'hotkey'

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(ui.selectedControl).toEqual(button)
      expect(config.saveConfig).toHaveBeenCalled()
    })
  })

  // --- Control-to-control drop ---

  describe('control drop', () => {
    beforeEach(() => {
      config.config = {
        mappings: {
          note_on: { 36: { name: 'Hotkey', action: 'hotkey' } },
        },
      }
      config.saveConfig = vi.fn().mockResolvedValue()
    })

    it('moves mapping to empty target', async () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button

      await dragDrop.onDrop(createMockDragEvent('drop'), button2)

      expect(config.config.mappings.note_on[37].action).toBe('hotkey')
      expect(config.config.mappings.note_on[36]).toBeUndefined()
      expect(ui.toasts[0].message).toContain('Moved')
    })

    it('swaps mappings between two controls', async () => {
      config.config.mappings.note_on[37] = { name: 'Noop', action: 'noop' }
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button

      await dragDrop.onDrop(createMockDragEvent('drop'), button2)

      expect(config.config.mappings.note_on[37].action).toBe('hotkey')
      expect(config.config.mappings.note_on[36].action).toBe('noop')
      expect(ui.toasts[0].message).toContain('Swapped')
    })

    it('copies with Ctrl key held', async () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button

      await dragDrop.onDrop(createMockDragEvent('drop', { ctrlKey: true }), button2)

      expect(config.config.mappings.note_on[37].action).toBe('hotkey')
      expect(config.config.mappings.note_on[36].action).toBe('hotkey') // Source untouched
      expect(ui.toasts[0].message).toContain('Copied')
    })

    it('self-drop is no-op', async () => {
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      expect(config.saveConfig).not.toHaveBeenCalled()
    })

    it('rejects incompatible source action on target', async () => {
      config.config.mappings.note_on[36] = { name: 'Play', action: 'spotify_play_pause' }
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button

      await dragDrop.onDrop(createMockDragEvent('drop'), fader)

      expect(config.saveConfig).not.toHaveBeenCalled()
      expect(ui.toasts[0].type).toBe('warning')
    })

    it('rejects swap when reverse direction is incompatible', async () => {
      // button has hotkey (dual) → fader: OK
      // fader has volume (CC-only) → button: FAIL
      config.config.mappings.cc_absolute = { 1: { name: 'Vol', action: 'volume' } }
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button

      await dragDrop.onDrop(createMockDragEvent('drop'), fader)

      expect(config.saveConfig).not.toHaveBeenCalled()
      expect(ui.toasts[0].message).toContain('Cannot swap')
    })

    it('rolls back move on save failure', async () => {
      config.saveConfig = vi.fn().mockRejectedValue(new Error('fail'))
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = button

      await dragDrop.onDrop(createMockDragEvent('drop'), button2)

      // Source restored
      expect(config.config.mappings.note_on[36]).toEqual({ name: 'Hotkey', action: 'hotkey' })
      // Target cleaned up
      expect(config.config.mappings.note_on[37]).toBeUndefined()
      expect(ui.toasts[0].type).toBe('error')
    })
  })

  // --- findMapping priority ---

  describe('findMapping priority', () => {
    it('prefers cc_absolute over cc_relative for same CC number', async () => {
      config.config = {
        mappings: {
          cc_absolute: { 2: { name: 'Abs', action: 'hotkey' } },
          cc_relative: { 2: { name: 'Rel', action: 'hotkey' } },
        },
      }
      config.saveConfig = vi.fn().mockResolvedValue()
      dragDrop.state.isDragging = true
      dragDrop.state.dragType = 'control'
      dragDrop.state.dragPayload = encoder

      await dragDrop.onDrop(createMockDragEvent('drop'), button)

      // findMapping found cc_absolute first → that's what gets deleted (move)
      expect(config.config.mappings.cc_absolute[2]).toBeUndefined()
      expect(config.config.mappings.cc_relative[2]).toEqual({ name: 'Rel', action: 'hotkey' })
    })

    it('finds encoder pushNote mapping', () => {
      config.config = { mappings: { note_on: { 40: { name: 'Push', action: 'hotkey' } } } }
      const event = createMockDragEvent('dragstart')

      dragDrop.onControlDragStart(event, encoder)

      expect(dragDrop.state.isDragging).toBe(true)
      expect(dragDrop.state.dragPayload).toEqual(encoder)
    })
  })
})
