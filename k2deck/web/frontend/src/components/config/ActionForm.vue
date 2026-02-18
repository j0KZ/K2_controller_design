<template>
  <div class="action-form space-y-3">
    <!-- Hotkey action -->
    <template v-if="actionType === 'hotkey'">
      <div>
        <label class="block text-sm font-medium mb-1">Keys</label>
        <input
          :value="modelValue.keys?.join(' + ')"
          @input="updateKeys($event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="ctrl + alt + m"
        />
        <p class="text-xs text-k2-text-secondary mt-1">Separate keys with +</p>
      </div>
    </template>

    <!-- Hotkey Relative (for encoders) -->
    <template v-else-if="actionType === 'hotkey_relative'">
      <div>
        <label class="block text-sm font-medium mb-1">Clockwise Keys</label>
        <input
          :value="modelValue.cw?.join(' + ')"
          @input="updateCwKeys($event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="ctrl + plus"
        />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Counter-clockwise Keys</label>
        <input
          :value="modelValue.ccw?.join(' + ')"
          @input="updateCcwKeys($event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="ctrl + minus"
        />
      </div>
    </template>

    <!-- Volume action -->
    <template v-else-if="actionType === 'volume'">
      <div>
        <label class="block text-sm font-medium mb-1">Target Process</label>
        <input
          :value="modelValue.target_process"
          @input="update('target_process', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Discord.exe or __master__"
        />
        <p class="text-xs text-k2-text-secondary mt-1">
          Use __master__ for system volume
        </p>
      </div>
    </template>

    <!-- Mouse scroll action -->
    <template v-else-if="actionType === 'mouse_scroll'">
      <div>
        <label class="block text-sm font-medium mb-1">Step Size</label>
        <input
          :value="modelValue.step || 3"
          @input="update('step', parseInt($event.target.value) || 3)"
          type="number"
          class="form-input w-full"
          min="1"
          max="20"
        />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Target App (optional)</label>
        <input
          :value="modelValue.target_app"
          @input="update('target_app', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Discord.exe"
        />
      </div>
    </template>

    <!-- OBS Scene action -->
    <template v-else-if="actionType === 'obs_scene'">
      <div>
        <label class="block text-sm font-medium mb-1">Scene Name</label>
        <input
          :value="modelValue.scene"
          @input="update('scene', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Gaming"
        />
      </div>
    </template>

    <!-- OBS Source Toggle action -->
    <template v-else-if="actionType === 'obs_source_toggle'">
      <div>
        <label class="block text-sm font-medium mb-1">Source Name</label>
        <input
          :value="modelValue.source"
          @input="update('source', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Webcam"
        />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Scene (optional)</label>
        <input
          :value="modelValue.scene"
          @input="update('scene', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Leave empty for current scene"
        />
      </div>
    </template>

    <!-- OBS Stream action -->
    <template v-else-if="actionType === 'obs_stream'">
      <div>
        <label class="block text-sm font-medium mb-1">Action</label>
        <select
          :value="modelValue.action || 'toggle'"
          @change="update('action', $event.target.value)"
          class="form-select w-full"
        >
          <option value="toggle">Toggle Stream</option>
          <option value="start">Start Stream</option>
          <option value="stop">Stop Stream</option>
        </select>
      </div>
    </template>

    <!-- OBS Record action -->
    <template v-else-if="actionType === 'obs_record'">
      <div>
        <label class="block text-sm font-medium mb-1">Action</label>
        <select
          :value="modelValue.action || 'toggle'"
          @change="update('action', $event.target.value)"
          class="form-select w-full"
        >
          <option value="toggle">Toggle Recording</option>
          <option value="start">Start Recording</option>
          <option value="stop">Stop Recording</option>
          <option value="pause">Pause Recording</option>
        </select>
      </div>
    </template>

    <!-- Spotify Play/Pause - no config needed -->
    <template v-else-if="actionType === 'spotify_play_pause'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        Toggles Spotify playback. No configuration needed.
      </p>
    </template>

    <!-- Spotify Next/Previous - no config needed -->
    <template v-else-if="actionType === 'spotify_next' || actionType === 'spotify_previous'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        {{ actionType === 'spotify_next' ? 'Skip to next track' : 'Go to previous track' }}. No configuration needed.
      </p>
    </template>

    <!-- Spotify Like - no config needed -->
    <template v-else-if="actionType === 'spotify_like'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        Toggles like status of currently playing track. No configuration needed.
      </p>
    </template>

    <!-- Spotify Shuffle - no config needed -->
    <template v-else-if="actionType === 'spotify_shuffle'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        Toggles shuffle mode. No configuration needed.
      </p>
    </template>

    <!-- Spotify Volume action -->
    <template v-else-if="actionType === 'spotify_volume'">
      <div class="flex items-center gap-2">
        <label class="text-sm font-medium">Relative Mode</label>
        <input
          type="checkbox"
          :checked="modelValue.relative"
          @change="update('relative', $event.target.checked)"
          class="w-4 h-4"
        />
      </div>
      <p class="text-xs text-k2-text-secondary">
        When enabled, CC value changes volume relatively. Otherwise, CC 0-127 maps to 0-100%.
      </p>
    </template>

    <!-- Spotify Seek action -->
    <template v-else-if="actionType === 'spotify_seek'">
      <div>
        <label class="block text-sm font-medium mb-1">Seek Mode</label>
        <select
          :value="modelValue.mode || 'relative'"
          @change="update('mode', $event.target.value)"
          class="form-select w-full"
        >
          <option value="relative">Relative (encoder)</option>
          <option value="absolute">Absolute (fader)</option>
        </select>
      </div>
      <div v-if="modelValue.mode === 'relative'">
        <label class="block text-sm font-medium mb-1">Step (seconds)</label>
        <input
          :value="modelValue.step || 5"
          @input="update('step', parseInt($event.target.value) || 5)"
          type="number"
          class="form-input w-full"
          min="1"
          max="30"
        />
      </div>
    </template>

    <!-- Twitch Marker action -->
    <template v-else-if="actionType === 'twitch_marker'">
      <div>
        <label class="block text-sm font-medium mb-1">Description (optional)</label>
        <input
          :value="modelValue.description"
          @input="update('description', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Highlight moment"
        />
      </div>
    </template>

    <!-- Folder action -->
    <template v-else-if="actionType === 'folder'">
      <div>
        <label class="block text-sm font-medium mb-1">Folder Name</label>
        <input
          :value="modelValue.folder"
          @input="update('folder', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="My Macros"
        />
      </div>
    </template>

    <!-- Counter action -->
    <template v-else-if="actionType === 'counter'">
      <div>
        <label class="block text-sm font-medium mb-1">Counter Name</label>
        <input
          :value="modelValue.counter"
          @input="update('counter', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="deaths"
        />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Operation</label>
        <select
          :value="modelValue.operation || 'increment'"
          @change="update('operation', $event.target.value)"
          class="form-select w-full"
        >
          <option value="increment">Increment (+1)</option>
          <option value="decrement">Decrement (-1)</option>
          <option value="reset">Reset to 0</option>
        </select>
      </div>
    </template>

    <!-- System action -->
    <template v-else-if="actionType === 'system'">
      <div>
        <label class="block text-sm font-medium mb-1">Command</label>
        <select
          :value="modelValue.command"
          @change="update('command', $event.target.value)"
          class="form-select w-full"
        >
          <option value="lock">Lock Screen</option>
          <option value="sleep">Sleep</option>
          <option value="screenshot">Screenshot</option>
          <option value="screenshot_region">Screenshot Region</option>
        </select>
      </div>
    </template>

    <!-- Sound Play action -->
    <template v-else-if="actionType === 'sound_play'">
      <div>
        <label class="block text-sm font-medium mb-1">Sound File</label>
        <input
          :value="modelValue.file"
          @input="update('file', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="sounds/click.wav"
        />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Volume</label>
        <input
          :value="modelValue.volume || 100"
          @input="update('volume', parseInt($event.target.value) || 100)"
          type="number"
          class="form-input w-full"
          min="0"
          max="100"
        />
      </div>
    </template>

    <!-- TTS action -->
    <template v-else-if="actionType === 'tts'">
      <div>
        <label class="block text-sm font-medium mb-1">Text to Speak</label>
        <input
          :value="modelValue.text"
          @input="update('text', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Hello world"
        />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Voice (optional)</label>
        <input
          :value="modelValue.voice"
          @input="update('voice', $event.target.value)"
          type="text"
          class="form-input w-full"
          placeholder="Default system voice"
        />
      </div>
    </template>

    <!-- Multi action -->
    <template v-else-if="actionType === 'multi'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        Executes multiple actions in sequence. Configure in JSON:
      </p>
      <textarea
        :value="JSON.stringify(modelValue.actions || [], null, 2)"
        @input="updateActions($event.target.value)"
        class="form-input w-full font-mono text-xs"
        rows="4"
        placeholder='[{"action": "hotkey", "keys": ["ctrl", "c"]}]'
      />
    </template>

    <!-- Multi Toggle action -->
    <template v-else-if="actionType === 'multi_toggle'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        Cycles through multiple actions on each press.
      </p>
      <textarea
        :value="JSON.stringify(modelValue.actions || [], null, 2)"
        @input="updateActions($event.target.value)"
        class="form-input w-full font-mono text-xs"
        rows="4"
        placeholder='[{"action": "obs_scene", "scene": "Gaming"}, {"action": "obs_scene", "scene": "Desktop"}]'
      />
    </template>

    <!-- Conditional action -->
    <template v-else-if="actionType === 'conditional'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        Executes different actions based on conditions. Advanced feature - configure in JSON.
      </p>
    </template>

    <!-- Noop action -->
    <template v-else-if="actionType === 'noop'">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        No operation. Use to disable a control or as a placeholder.
      </p>
    </template>

    <!-- Default fallback -->
    <template v-else-if="actionType">
      <p class="text-sm text-k2-text-secondary bg-k2-surface-hover rounded p-3">
        Action: <span class="text-k2-text">{{ formatActionName(actionType) }}</span>
      </p>
    </template>
  </div>
</template>

<script setup>
const props = defineProps({
  actionType: { type: String, required: true },
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue'])

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function updateKeys(value) {
  const keys = value.split('+').map(k => k.trim().toLowerCase()).filter(Boolean)
  emit('update:modelValue', { ...props.modelValue, keys })
}

function updateCwKeys(value) {
  const cw = value.split('+').map(k => k.trim().toLowerCase()).filter(Boolean)
  emit('update:modelValue', { ...props.modelValue, cw })
}

function updateCcwKeys(value) {
  const ccw = value.split('+').map(k => k.trim().toLowerCase()).filter(Boolean)
  emit('update:modelValue', { ...props.modelValue, ccw })
}

function updateActions(value) {
  try {
    const actions = JSON.parse(value)
    emit('update:modelValue', { ...props.modelValue, actions })
  } catch {
    // Invalid JSON, don't update
  }
}

function formatActionName(action) {
  return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}
</script>
