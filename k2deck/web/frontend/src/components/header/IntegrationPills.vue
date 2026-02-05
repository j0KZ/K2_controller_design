<template>
  <div class="integration-pills flex gap-2">
    <div
      v-for="(integration, name) in integrations.$state"
      :key="name"
      class="flex items-center gap-1 px-2 py-1 rounded text-xs cursor-pointer"
      :class="pillClasses(integration)"
      :title="integration.error || integration.status"
      @click="toggleIntegration(name, integration)"
    >
      <span class="w-2 h-2 rounded-full" :class="dotClasses(integration)" />
      <span class="capitalize">{{ name }}</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useIntegrations } from '@/stores/integrations'
import { useUi } from '@/stores/ui'

const integrations = useIntegrations()
const ui = useUi()

onMounted(() => integrations.fetchAll())

function pillClasses(int) {
  if (int.connected) return 'bg-k2-success/20 text-k2-success hover:bg-k2-success/30'
  if (int.error) return 'bg-k2-error/20 text-k2-error hover:bg-k2-error/30'
  return 'bg-k2-surface text-k2-text-secondary hover:bg-k2-surface-hover'
}

function dotClasses(int) {
  if (int.connected) return 'bg-k2-success'
  if (int.error) return 'bg-k2-error'
  return 'bg-k2-text-secondary'
}

async function toggleIntegration(name, integration) {
  try {
    if (integration.connected) {
      await integrations.disconnect(name)
      ui.addToast(`${name} disconnected`, 'info')
    } else if (integration.available) {
      await integrations.connect(name)
      ui.addToast(`${name} connected`, 'success')
    }
  } catch (e) {
    ui.addToast(`Failed to toggle ${name}: ${e.message}`, 'error')
  }
}
</script>
