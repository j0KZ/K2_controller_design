import { reactive } from 'vue'
import { nextTick } from 'vue'
import { useConfig } from '@/stores/config'
import { useUi } from '@/stores/ui'

// Module-level singleton — one drag operation at a time
const state = reactive({
  isDragging: false,
  dragType: null, // 'catalog' | 'control'
  dragPayload: null, // action type string (catalog) | control object (control)
  dragOverControlId: null,
})

// Actions that REQUIRE CC events — cannot go on buttons
const CC_ONLY_ACTIONS = new Set([
  'hotkey_relative',
  'volume',
  'mouse_scroll',
  'spotify_volume',
  'spotify_seek',
  'spotify_prev_next',
  'osc_send_relative',
  'osc_send_trigger',
])

// Actions that REQUIRE note_on events — cannot go on encoders/faders/pots
const NOTE_ONLY_ACTIONS = new Set([
  'spotify_play_pause', 'spotify_next', 'spotify_previous',
  'spotify_like', 'spotify_shuffle', 'spotify_repeat',
  'obs_scene', 'obs_source_toggle', 'obs_stream', 'obs_record', 'obs_mute',
  'osc_send',
  'system',
  'open_url', 'clipboard_paste', 'launch', 'focus',
  'sound_play', 'sound_stop', 'audio_switch', 'audio_list',
  'twitch_marker', 'twitch_clip', 'twitch_chat', 'twitch_title', 'twitch_game',
  'timer_start', 'timer_stop', 'timer_toggle',
  'folder', 'folder_back', 'folder_root',
  'multi', 'multi_toggle',
  'counter', 'tts',
])

function formatName(type) {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function defaultMapping(actionType) {
  return { name: formatName(actionType), action: actionType }
}

function isDropCompatible(actionType, targetControl) {
  const targetIsCC = targetControl.cc !== undefined
  if (!targetIsCC && CC_ONLY_ACTIONS.has(actionType)) return false
  if (targetIsCC && NOTE_ONLY_ACTIONS.has(actionType)) return false
  return true
}

export function useDragDrop() {
  const config = useConfig()
  const ui = useUi()

  // --- Mapping resolution ---

  function findMapping(control) {
    const cfg = config.config?.mappings
    if (!cfg) return null
    if (control.note !== undefined && cfg.note_on?.[control.note])
      return { type: 'note_on', key: control.note, mapping: cfg.note_on[control.note] }
    if (control.pushNote !== undefined && cfg.note_on?.[control.pushNote])
      return { type: 'note_on', key: control.pushNote, mapping: cfg.note_on[control.pushNote] }
    if (control.cc !== undefined) {
      if (cfg.cc_absolute?.[control.cc])
        return { type: 'cc_absolute', key: control.cc, mapping: cfg.cc_absolute[control.cc] }
      if (cfg.cc_relative?.[control.cc])
        return { type: 'cc_relative', key: control.cc, mapping: cfg.cc_relative[control.cc] }
    }
    return null
  }

  function getMappingKey(control) {
    if (control.cc !== undefined) {
      return {
        type: control.type === 'encoder' ? 'cc_relative' : 'cc_absolute',
        key: control.cc,
      }
    }
    return { type: 'note_on', key: control.note || control.pushNote }
  }

  // --- Drag event handlers ---

  function onCatalogDragStart(event, actionType) {
    state.isDragging = true
    state.dragType = 'catalog'
    state.dragPayload = actionType
    event.dataTransfer.effectAllowed = 'copy'
    event.dataTransfer.setData('text/plain', actionType)
  }

  function onControlDragStart(event, control) {
    if (control.special) return
    if (!config.config) return
    const mapping = findMapping(control)
    if (!mapping) {
      event.preventDefault()
      return
    }
    state.isDragging = true
    state.dragType = 'control'
    state.dragPayload = control
    event.dataTransfer.effectAllowed = 'copyMove'
    event.dataTransfer.setData('text/plain', control.id)
  }

  function onDragOver(event, control) {
    if (control.special) return
    event.preventDefault()
    state.dragOverControlId = control.id
  }

  function onDragEnter(event, control) {
    if (control.special) return
    event.preventDefault()
    state.dragOverControlId = control.id
  }

  function onDragLeave(event, control) {
    if (event.currentTarget && event.relatedTarget &&
        event.currentTarget.contains(event.relatedTarget)) {
      return
    }
    if (state.dragOverControlId === control.id) {
      state.dragOverControlId = null
    }
  }

  async function onDrop(event, targetControl) {
    event.preventDefault()
    state.dragOverControlId = null

    if (targetControl.special) return
    if (!config.config) return
    if (config.dirty) {
      ui.addToast('Save or revert current changes first', 'warning')
      resetDragState()
      return
    }

    if (state.dragType === 'catalog') {
      await handleCatalogDrop(targetControl)
    } else if (state.dragType === 'control') {
      await handleControlDrop(event, targetControl)
    }

    resetDragState()
  }

  function onDragEnd() {
    resetDragState()
  }

  // --- Drop handlers ---

  async function handleCatalogDrop(targetControl) {
    const actionType = state.dragPayload
    if (!isDropCompatible(actionType, targetControl)) {
      ui.addToast(
        `'${formatName(actionType)}' is not compatible with this control`,
        'warning',
      )
      return
    }

    const targetInfo = findMapping(targetControl)
    const targetWrite = targetInfo
      ? { type: targetInfo.type, key: targetInfo.key }
      : getMappingKey(targetControl)
    const snapshot = targetInfo?.mapping

    config.updateMapping(targetWrite.type, targetWrite.key, defaultMapping(actionType))

    try {
      await config.saveConfig()
      if (ui.selectedControl?.id === targetControl.id) {
        ui.clearSelection()
        await nextTick()
      }
      ui.selectControl(targetControl)
      ui.addToast(`Added ${formatName(actionType)} to ${targetControl.id}`, 'success')
    } catch (e) {
      if (snapshot) config.updateMapping(targetWrite.type, targetWrite.key, snapshot)
      else config.deleteMapping(targetWrite.type, targetWrite.key)
      config.dirty = false
      ui.addToast('Failed to save: ' + e.message, 'error')
    }
  }

  async function handleControlDrop(event, targetControl) {
    const sourceControl = state.dragPayload
    if (sourceControl.id === targetControl.id) return

    const sourceInfo = findMapping(sourceControl)
    if (!sourceInfo) return

    const sourceAction = sourceInfo.mapping.action
    if (!isDropCompatible(sourceAction, targetControl)) {
      ui.addToast(
        `'${formatName(sourceAction)}' is not compatible with this control`,
        'warning',
      )
      return
    }

    const targetInfo = findMapping(targetControl)
    const isCopy = event.ctrlKey
    const isSwap = !!targetInfo

    // Bidirectional compatibility check for swap
    if (isSwap && !isCopy) {
      const targetAction = targetInfo.mapping.action
      if (!isDropCompatible(targetAction, sourceControl)) {
        ui.addToast(
          `Cannot swap: '${formatName(targetAction)}' is not compatible with source control`,
          'warning',
        )
        return
      }
    }

    // Snapshots for rollback
    const sourceSnapshot = { ...sourceInfo.mapping }
    const targetSnapshot = targetInfo ? { ...targetInfo.mapping } : undefined

    const targetWrite = targetInfo
      ? { type: targetInfo.type, key: targetInfo.key }
      : getMappingKey(targetControl)

    // Execute operation
    config.updateMapping(targetWrite.type, targetWrite.key, { ...sourceInfo.mapping })

    if (isSwap && !isCopy) {
      config.updateMapping(sourceInfo.type, sourceInfo.key, { ...targetInfo.mapping })
    } else if (!isCopy) {
      config.deleteMapping(sourceInfo.type, sourceInfo.key)
    }

    try {
      await config.saveConfig()
      if (ui.selectedControl?.id === targetControl.id) {
        ui.clearSelection()
        await nextTick()
      }
      ui.selectControl(targetControl)
      const op = isCopy ? 'Copied' : isSwap ? 'Swapped' : 'Moved'
      ui.addToast(`${op} ${formatName(sourceAction)} to ${targetControl.id}`, 'success')
    } catch (e) {
      // Rollback
      config.updateMapping(sourceInfo.type, sourceInfo.key, sourceSnapshot)
      if (targetSnapshot) config.updateMapping(targetWrite.type, targetWrite.key, targetSnapshot)
      else config.deleteMapping(targetWrite.type, targetWrite.key)
      config.dirty = false
      ui.addToast('Failed to save: ' + e.message, 'error')
    }
  }

  // --- Getters ---

  function isDragOver(controlId) {
    return state.isDragging && state.dragOverControlId === controlId
  }

  function isSourceControl(controlId) {
    return (
      state.isDragging &&
      state.dragType === 'control' &&
      state.dragPayload?.id === controlId
    )
  }

  function resetDragState() {
    state.isDragging = false
    state.dragType = null
    state.dragPayload = null
    state.dragOverControlId = null
  }

  return {
    state,
    onCatalogDragStart,
    onControlDragStart,
    onDragOver,
    onDragEnter,
    onDragLeave,
    onDrop,
    onDragEnd,
    isDragOver,
    isSourceControl,
    resetDragState,
  }
}

// Exported for testing
export { CC_ONLY_ACTIONS, NOTE_ONLY_ACTIONS, isDropCompatible, formatName, defaultMapping }
