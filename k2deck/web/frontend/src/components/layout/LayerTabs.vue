<template>
  <div class="layer-tabs flex gap-2">
    <button
      v-for="layer in [1, 2, 3]"
      :key="layer"
      class="px-4 py-2 rounded font-medium transition-colors"
      :class="layer === k2State.layer ? 'bg-k2-accent text-white' : 'bg-k2-surface text-k2-text-secondary hover:bg-k2-surface-hover'"
      @click="setLayer(layer)"
    >
      Layer {{ layer }}
    </button>
  </div>
</template>

<script setup>
import { useK2State } from '@/stores/k2State'
import { useApi } from '@/composables/useApi'
import { useUi } from '@/stores/ui'

const k2State = useK2State()
const api = useApi()
const ui = useUi()

async function setLayer(layer) {
  try {
    await api.put('/k2/state/layer', { layer })
    k2State.setLayer(layer)
  } catch (e) {
    ui.addToast('Failed to switch layer: ' + e.message, 'error')
  }
}
</script>
