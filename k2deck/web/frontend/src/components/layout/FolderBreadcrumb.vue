<template>
  <div class="folder-breadcrumb flex items-center gap-2 text-sm text-k2-text-secondary">
    <button
      class="hover:text-k2-text"
      @click="goToRoot"
    >
      /
    </button>
    <span>&gt;</span>
    <span class="text-k2-text">{{ k2State.folder }}</span>
  </div>
</template>

<script setup>
import { useK2State } from '@/stores/k2State'
import { useApi } from '@/composables/useApi'
import { useUi } from '@/stores/ui'

const k2State = useK2State()
const api = useApi()
const ui = useUi()

async function goToRoot() {
  try {
    await api.put('/k2/state/folder', { folder: null })
    k2State.setFolder(null)
  } catch (e) {
    ui.addToast('Failed to navigate: ' + e.message, 'error')
  }
}
</script>
