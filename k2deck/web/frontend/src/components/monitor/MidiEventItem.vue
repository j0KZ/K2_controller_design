<template>
  <div class="midi-event flex gap-4 text-k2-text-secondary">
    <span class="text-k2-text-secondary w-20">{{ formattedTime }}</span>
    <span :class="typeClass" class="w-16">{{ event.type }}</span>
    <span class="w-12">ch={{ event.channel }}</span>
    <span v-if="event.note !== undefined" class="w-16">note={{ event.note }}</span>
    <span v-if="event.cc !== undefined" class="w-16">cc={{ event.cc }}</span>
    <span class="w-16">val={{ event.value }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  event: { type: Object, required: true },
})

const formattedTime = computed(() => {
  const d = new Date(props.event.timestamp)
  return d.toLocaleTimeString('en-US', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0')
})

const typeClass = computed(() => ({
  'text-k2-success': props.event.type === 'note_on',
  'text-k2-error': props.event.type === 'note_off',
  'text-k2-accent': props.event.type === 'cc',
}))
</script>
