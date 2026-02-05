<template>
  <div class="k2-button flex flex-col items-center p-2 w-[100px]">
    <!-- LED + Button visual -->
    <div
      class="relative w-14 h-14 rounded-lg flex items-center justify-center"
      :class="buttonClasses"
    >
      <!-- LED indicator -->
      <K2Led v-if="control.hasLed" :color="ledState" class="absolute -top-1 -right-1" />

      <!-- Button icon/label -->
      <span class="text-lg font-bold">{{ control.id }}</span>
    </div>

    <!-- Action name -->
    <span class="mt-1 text-xs text-k2-text-secondary truncate max-w-full text-center">
      {{ mapping?.name || '—' }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import K2Led from './K2Led.vue'

const props = defineProps({
  control: { type: Object, required: true },
  ledState: { type: String, default: null },
  mapping: { type: Object, default: null },
})

const buttonClasses = computed(() => [
  'bg-k2-surface border-2 border-k2-border',
  'hover:border-k2-accent transition-colors',
])
</script>
