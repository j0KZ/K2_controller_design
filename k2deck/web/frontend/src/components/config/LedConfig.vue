<template>
  <div class="led-config bg-k2-surface-hover rounded-lg p-4">
    <h3 class="text-sm font-medium mb-3">LED Settings</h3>

    <div class="grid grid-cols-2 gap-4">
      <!-- Mode -->
      <div>
        <label class="block text-xs text-k2-text-secondary mb-1">Mode</label>
        <select
          :value="modelValue?.mode || 'static'"
          @change="update('mode', $event.target.value)"
          class="form-select w-full text-sm"
        >
          <option value="static">Static</option>
          <option value="toggle">Toggle</option>
          <option value="flash">Flash</option>
          <option value="pulse">Pulse</option>
        </select>
      </div>

      <!-- On Color -->
      <div>
        <label class="block text-xs text-k2-text-secondary mb-1">On Color</label>
        <div class="flex gap-2">
          <button
            v-for="color in ['red', 'amber', 'green']"
            :key="color"
            class="w-8 h-8 rounded border-2 transition-all"
            :class="[
              colorClass(color),
              modelValue?.color === color ? 'border-white scale-110' : 'border-transparent'
            ]"
            @click="update('color', color)"
          />
        </div>
      </div>

      <!-- Off Color (for toggle mode) -->
      <div v-if="modelValue?.mode === 'toggle'">
        <label class="block text-xs text-k2-text-secondary mb-1">Off Color</label>
        <div class="flex gap-2">
          <button
            v-for="color in ['red', 'amber', 'green', null]"
            :key="color || 'off'"
            class="w-8 h-8 rounded border-2 transition-all"
            :class="[
              color ? colorClass(color) : 'bg-led-off',
              modelValue?.off_color === color ? 'border-white scale-110' : 'border-transparent'
            ]"
            @click="update('off_color', color)"
          />
        </div>
      </div>

      <!-- Flash count (for flash mode) -->
      <div v-if="modelValue?.mode === 'flash'">
        <label class="block text-xs text-k2-text-secondary mb-1">Flash Count</label>
        <input
          :value="modelValue?.flash_count || 3"
          @input="update('flash_count', parseInt($event.target.value) || 3)"
          type="number"
          class="form-input w-full text-sm"
          min="1"
          max="10"
        />
      </div>

      <!-- Pulse speed (for pulse mode) -->
      <div v-if="modelValue?.mode === 'pulse'">
        <label class="block text-xs text-k2-text-secondary mb-1">Pulse Speed (ms)</label>
        <input
          :value="modelValue?.pulse_speed || 500"
          @input="update('pulse_speed', parseInt($event.target.value) || 500)"
          type="number"
          class="form-input w-full text-sm"
          min="100"
          max="2000"
          step="100"
        />
      </div>
    </div>

    <!-- Preview -->
    <div class="mt-4 flex items-center gap-2">
      <span class="text-xs text-k2-text-secondary">Preview:</span>
      <div
        class="w-4 h-4 rounded-full"
        :class="modelValue?.color ? 'led-glow' : 'bg-led-off'"
        :style="modelValue?.color ? { backgroundColor: colorHex(modelValue.color), color: colorHex(modelValue.color) } : {}"
      />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])

const colorMap = {
  red: '#ff3333',
  amber: '#ffaa00',
  green: '#00ff66',
}

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function colorClass(color) {
  return {
    red: 'bg-led-red',
    amber: 'bg-led-amber',
    green: 'bg-led-green',
  }[color] || 'bg-led-off'
}

function colorHex(color) {
  return colorMap[color] || null
}
</script>
