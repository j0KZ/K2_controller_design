<template>
  <div class="action-picker">
    <label class="block text-sm font-medium mb-1">Action</label>
    <select
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
      class="form-select w-full"
    >
      <option value="">Select an action...</option>
      <optgroup v-for="(actions, category) in groupedActions" :key="category" :label="category">
        <option v-for="action in actions" :key="action" :value="action">
          {{ formatActionName(action) }}
        </option>
      </optgroup>
    </select>
  </div>
</template>

<script setup>
import { computed } from 'vue'

defineProps({
  modelValue: { type: String, default: '' },
})

defineEmits(['update:modelValue'])

// Action types grouped by category
const groupedActions = computed(() => ({
  'Media': [
    'spotify_play_pause',
    'spotify_next',
    'spotify_previous',
    'spotify_volume',
    'spotify_like',
    'spotify_shuffle',
    'spotify_seek',
  ],
  'System': [
    'hotkey',
    'volume',
    'mouse_scroll',
    'hotkey_relative',
  ],
  'OBS': [
    'obs_scene',
    'obs_source_toggle',
    'obs_stream',
    'obs_record',
  ],
  'Twitch': [
    'twitch_marker',
    'twitch_ad',
    'twitch_prediction',
  ],
  'Advanced': [
    'conditional',
    'multi',
    'multi_toggle',
    'folder',
    'counter',
    'sound',
    'tts',
  ],
  'Utility': [
    'noop',
    'system',
  ],
}))

function formatActionName(action) {
  return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}
</script>
