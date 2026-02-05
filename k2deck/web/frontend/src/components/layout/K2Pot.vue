<template>
  <div class="k2-pot flex flex-col items-center p-2 w-[100px]">
    <!-- Pot visual (similar to encoder but smaller) -->
    <svg width="48" height="48" viewBox="0 0 48 48">
      <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" stroke-width="3" class="text-k2-border" />
      <circle
        cx="24" cy="24" r="20"
        fill="none" stroke="currentColor" stroke-width="3"
        stroke-dasharray="125.6"
        :stroke-dashoffset="125.6 - (125.6 * percent / 100)"
        transform="rotate(-90 24 24)"
        class="text-k2-success"
      />
      <circle cx="24" cy="24" r="6" class="fill-k2-surface" />
    </svg>

    <!-- Value -->
    <span class="text-xs font-mono text-k2-text-secondary">{{ analogValue }}</span>

    <!-- Label -->
    <span class="text-xs text-k2-text-secondary truncate max-w-full">
      {{ mapping?.name || control.id }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  control: { type: Object, required: true },
  analogValue: { type: Number, default: 0 },
  mapping: { type: Object, default: null },
})

const percent = computed(() => Math.round((props.analogValue / 127) * 100))
</script>
