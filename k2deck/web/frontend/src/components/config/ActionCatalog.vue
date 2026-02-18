<template>
  <div class="action-catalog p-6 h-full flex flex-col">
    <div class="mb-4">
      <h2 class="text-xl font-bold">Action Catalog</h2>
      <p class="text-sm text-k2-text-secondary">Drag an action onto a control</p>
    </div>

    <input
      v-model="search"
      type="text"
      class="form-input w-full mb-4"
      placeholder="Search actions..."
    />

    <div class="flex-1 overflow-y-auto">
      <template v-for="(actions, category) in filteredGroups" :key="category">
        <div v-if="actions.length" class="mb-4">
          <h3 class="text-xs font-semibold text-k2-text-secondary uppercase tracking-wider mb-2">
            {{ category }}
          </h3>
          <div class="grid grid-cols-2 gap-2">
            <div
              v-for="action in actions"
              :key="action"
              class="action-card bg-k2-surface rounded-lg p-3 cursor-grab border border-k2-border hover:border-k2-accent transition-colors"
              draggable="true"
              @dragstart="onDragStart($event, action)"
            >
              <p class="text-sm font-medium truncate">{{ formatName(action) }}</p>
            </div>
          </div>
        </div>
      </template>
      <div
        v-if="noResults"
        class="text-center text-k2-text-secondary py-8"
      >
        No actions match "{{ search }}"
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDragDrop, formatName } from '@/composables/useDragDrop'

const dragDrop = useDragDrop()
const search = ref('')

const ACTION_GROUPS = {
  'Media': [
    'spotify_play_pause', 'spotify_next', 'spotify_previous',
    'spotify_volume', 'spotify_like', 'spotify_shuffle', 'spotify_seek',
  ],
  'System': ['hotkey', 'volume', 'mouse_scroll', 'hotkey_relative'],
  'OBS': ['obs_scene', 'obs_source_toggle', 'obs_stream', 'obs_record'],
  'Twitch': ['twitch_marker', 'twitch_ad', 'twitch_prediction'],
  'Advanced': ['conditional', 'multi', 'multi_toggle', 'folder', 'counter', 'sound', 'tts'],
  'Utility': ['noop', 'system'],
}

const filteredGroups = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return ACTION_GROUPS

  const result = {}
  for (const [category, actions] of Object.entries(ACTION_GROUPS)) {
    const filtered = actions.filter(
      (a) =>
        a.includes(q) ||
        formatName(a).toLowerCase().includes(q) ||
        category.toLowerCase().includes(q),
    )
    result[category] = filtered
  }
  return result
})

const noResults = computed(() =>
  Object.values(filteredGroups.value).every((a) => a.length === 0),
)

function onDragStart(event, actionType) {
  dragDrop.onCatalogDragStart(event, actionType)
}
</script>
