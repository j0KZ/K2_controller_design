<template>
  <div class="connection-status flex items-center gap-2">
    <div
      class="w-2 h-2 rounded-full"
      :class="k2State.connected ? 'bg-k2-success' : 'bg-k2-error'"
    />
    <span class="text-sm text-k2-text-secondary">
      {{ k2State.connected ? k2State.port : 'Disconnected' }}
    </span>
  </div>
</template>

<script setup>
import { useK2State } from '@/stores/k2State'
const k2State = useK2State()
</script>
