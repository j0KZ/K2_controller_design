<template>
  <div class="k2-encoder flex flex-col items-center p-2 w-[100px]">
    <!-- Encoder visual -->
    <div class="relative">
      <!-- SVG arc for encoder -->
      <svg width="56" height="56" viewBox="0 0 56 56">
        <!-- Background arc -->
        <circle
          cx="28" cy="28" r="24"
          fill="none"
          stroke="currentColor"
          stroke-width="4"
          class="text-k2-border"
        />
        <!-- Value arc (if CC has value) -->
        <circle
          v-if="analogValue !== null"
          cx="28" cy="28" r="24"
          fill="none"
          stroke="currentColor"
          stroke-width="4"
          stroke-dasharray="150.8"
          :stroke-dashoffset="150.8 - (150.8 * percent / 100)"
          transform="rotate(-90 28 28)"
          class="text-k2-accent"
        />
        <!-- Center dot -->
        <circle cx="28" cy="28" r="8" class="fill-k2-surface" />
      </svg>

      <!-- LED (for push button) -->
      <K2Led v-if="control.hasLed" :color="ledState" class="absolute -top-1 -right-1" />
    </div>

    <!-- Label -->
    <span class="mt-1 text-xs text-k2-text-secondary truncate max-w-full">
      {{ mapping?.name || control.id }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import K2Led from './K2Led.vue'

const props = defineProps({
  control: { type: Object, required: true },
  ledState: { type: String, default: null },
  analogValue: { type: Number, default: null },
  mapping: { type: Object, default: null },
})

const percent = computed(() =>
  props.analogValue !== null ? Math.round((props.analogValue / 127) * 100) : 0
)
</script>
