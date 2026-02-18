<template>
  <div class="app h-screen flex flex-col bg-k2-bg text-k2-text overflow-hidden">
    <AppHeader />

    <main class="flex-1 flex overflow-hidden">
      <!-- Left: K2 Grid -->
      <div class="w-[520px] flex-shrink-0 p-4 overflow-y-auto border-r border-k2-border">
        <K2Grid />
      </div>

      <!-- Right: Config Panel -->
      <div class="flex-1 overflow-y-auto">
        <ControlConfig v-if="ui.selectedControl" />
        <ActionCatalog v-else />
      </div>
    </main>

    <MidiMonitor />
    <ToastContainer />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUi } from '@/stores/ui'
import { useK2State } from '@/stores/k2State'
import { useConfig } from '@/stores/config'
import { useWebSocket } from '@/composables/useWebSocket'
import { useKeyboard } from '@/composables/useKeyboard'
import AppHeader from '@/components/header/AppHeader.vue'
import K2Grid from '@/components/layout/K2Grid.vue'
import ControlConfig from '@/components/config/ControlConfig.vue'
import ActionCatalog from '@/components/config/ActionCatalog.vue'
import MidiMonitor from '@/components/monitor/MidiMonitor.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'

const ui = useUi()
const k2State = useK2State()
const config = useConfig()
const { connect } = useWebSocket()

// Enable keyboard shortcuts
useKeyboard()

onMounted(async () => {
  await k2State.fetchLayout()
  await k2State.fetchState()
  await config.fetchConfig()
  connect()
})
</script>
