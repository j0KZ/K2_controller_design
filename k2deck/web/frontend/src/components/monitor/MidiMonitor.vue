<template>
  <div class="midi-monitor h-32 bg-k2-surface border-t border-k2-border">
    <div class="flex items-center justify-between px-4 py-2 border-b border-k2-border">
      <span class="text-sm font-medium">MIDI Monitor</span>
      <div class="flex gap-2">
        <button
          class="px-2 py-1 text-xs rounded transition-colors"
          :class="midi.paused ? 'bg-k2-warning text-black' : 'bg-k2-surface-hover hover:bg-k2-border'"
          @click="midi.togglePause()"
        >
          {{ midi.paused ? 'Resume' : 'Pause' }}
        </button>
        <button
          class="px-2 py-1 text-xs bg-k2-surface-hover hover:bg-k2-border rounded transition-colors"
          @click="midi.clear()"
        >
          Clear
        </button>
      </div>
    </div>

    <div class="h-20 overflow-y-auto font-mono text-xs p-2 space-y-1">
      <MidiEventItem
        v-for="(event, index) in midi.events"
        :key="`${event.timestamp}-${index}`"
        :event="event"
      />
      <p v-if="midi.events.length === 0" class="text-k2-text-secondary">
        Waiting for MIDI events...
      </p>
    </div>
  </div>
</template>

<script setup>
import { useMidi } from '@/stores/midi'
import MidiEventItem from './MidiEventItem.vue'

const midi = useMidi()
</script>
