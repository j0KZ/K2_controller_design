<template>
  <div
    class="k2-led w-3 h-3 rounded-full border border-k2-border transition-all duration-150"
    :class="ledClasses"
    :style="ledStyle"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  color: { type: String, default: null }, // 'red', 'amber', 'green', or null
})

const colorMap = {
  red: '#ff3333',
  amber: '#ffaa00',
  green: '#00ff66',
}

const ledClasses = computed(() => [
  props.color ? 'led-glow' : 'bg-led-off',
])

const ledStyle = computed(() =>
  props.color ? { backgroundColor: colorMap[props.color], color: colorMap[props.color] } : {}
)
</script>
