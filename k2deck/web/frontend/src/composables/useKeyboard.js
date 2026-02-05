import { onMounted, onUnmounted } from 'vue'
import { useUi } from '@/stores/ui'
import { useConfig } from '@/stores/config'
import { useK2State } from '@/stores/k2State'
import { useApi } from '@/composables/useApi'

export function useKeyboard() {
  const ui = useUi()
  const config = useConfig()
  const k2State = useK2State()
  const api = useApi()

  function handleKeydown(event) {
    // Ignore if typing in input
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.tagName === 'SELECT') {
      return
    }

    const key = event.key.toLowerCase()
    const ctrl = event.ctrlKey || event.metaKey

    // Ctrl+S: Save
    if (ctrl && key === 's') {
      event.preventDefault()
      if (config.dirty) {
        config.saveConfig()
          .then(() => ui.addToast('Configuration saved', 'success'))
          .catch((e) => ui.addToast('Failed to save: ' + e.message, 'error'))
      }
    }

    // Escape: Clear selection
    if (key === 'escape') {
      ui.clearSelection()
    }

    // 1, 2, 3: Switch layers (when not ctrl)
    if (['1', '2', '3'].includes(key) && !ctrl && !event.altKey) {
      const layer = parseInt(key)
      api.put('/k2/state/layer', { layer })
        .then(() => k2State.setLayer(layer))
        .catch((e) => ui.addToast('Failed to switch layer: ' + e.message, 'error'))
    }

    // Ctrl+Z: Revert unsaved changes
    if (ctrl && key === 'z') {
      if (config.dirty) {
        event.preventDefault()
        // Refetch config from server to revert all changes
        config.fetchConfig()
          .then(() => ui.addToast('Changes reverted', 'info'))
          .catch((e) => ui.addToast('Failed to revert: ' + e.message, 'error'))
      }
    }
  }

  onMounted(() => window.addEventListener('keydown', handleKeydown))
  onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
}
