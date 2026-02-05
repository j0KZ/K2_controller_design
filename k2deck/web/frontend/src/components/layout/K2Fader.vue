<template>
  <div class="k2-fader flex flex-col items-center p-2 w-[100px]">
    <!-- Fader track -->
    <div class="relative h-32 w-6 bg-k2-bg rounded-full border border-k2-border overflow-hidden">
      <!-- Value fill -->
      <div
        class="absolute bottom-0 w-full bg-k2-success rounded-full transition-all duration-75"
        :style="{ height: `${percent}%` }"
      />

      <!-- Knob -->
      <div
        class="absolute w-8 h-3 -left-1 bg-k2-text rounded shadow-md transition-all duration-75"
        :style="{ bottom: `calc(${percent}% - 6px)` }"
      />
    </div>

    <!-- Value display -->
    <span class="mt-2 text-sm font-mono text-k2-text-secondary">{{ analogValue }}</span>

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
