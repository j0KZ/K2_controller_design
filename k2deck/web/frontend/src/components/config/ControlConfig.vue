<template>
  <div class="control-config p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-bold">{{ selectedControl.id }}</h2>
        <p class="text-sm text-k2-text-secondary">{{ controlTypeLabel }}</p>
      </div>
      <button
        @click="ui.clearSelection()"
        class="text-k2-text-secondary hover:text-k2-text text-xl"
      >
        ✕
      </button>
    </div>

    <!-- Name -->
    <div class="mb-4">
      <label class="block text-sm font-medium mb-1">Name</label>
      <input
        v-model="localMapping.name"
        type="text"
        class="form-input w-full"
        placeholder="Action name"
        @input="markDirty"
      />
    </div>

    <!-- Action Type -->
    <ActionPicker
      :model-value="localMapping.action"
      @update:model-value="onActionChange"
      class="mb-4"
    />

    <!-- Action-specific fields -->
    <ActionForm
      v-if="localMapping.action"
      :action-type="localMapping.action"
      :model-value="localMapping"
      @update:model-value="onMappingUpdate"
      class="mb-4"
    />

    <!-- LED Config (for controls with LEDs) -->
    <LedConfig
      v-if="selectedControl.hasLed"
      :model-value="localMapping.led"
      @update:model-value="onLedUpdate"
      class="mb-4"
    />

    <!-- Control Info -->
    <div class="bg-k2-surface-hover rounded-lg p-3 mb-4 text-xs text-k2-text-secondary">
      <div class="grid grid-cols-2 gap-2">
        <div v-if="selectedControl.note !== undefined">
          <span class="text-k2-text">Note:</span> {{ selectedControl.note }}
        </div>
        <div v-if="selectedControl.pushNote !== undefined">
          <span class="text-k2-text">Push Note:</span> {{ selectedControl.pushNote }}
        </div>
        <div v-if="selectedControl.cc !== undefined">
          <span class="text-k2-text">CC:</span> {{ selectedControl.cc }}
        </div>
        <div v-if="selectedControl.ledNote !== undefined">
          <span class="text-k2-text">LED Note:</span> {{ selectedControl.ledNote }}
        </div>
      </div>
    </div>

    <!-- Save/Cancel -->
    <div class="flex gap-2 mt-6">
      <button
        class="btn-primary flex-1"
        @click="save"
        :disabled="!config.dirty"
      >
        Save
      </button>
      <button
        class="btn-secondary"
        @click="revert"
        :disabled="!config.dirty"
      >
        Cancel
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useUi } from '@/stores/ui'
import { useConfig } from '@/stores/config'
import ActionPicker from './ActionPicker.vue'
import ActionForm from './ActionForm.vue'
import LedConfig from './LedConfig.vue'

const ui = useUi()
const config = useConfig()

const selectedControl = computed(() => ui.selectedControl)
const localMapping = ref({})

const controlTypeLabel = computed(() => {
  const types = {
    button: 'Button',
    encoder: 'Encoder',
    pot: 'Potentiometer',
    fader: 'Fader',
  }
  return types[selectedControl.value?.type] || 'Control'
})

// Load mapping when control changes
watch(selectedControl, (control) => {
  if (control) {
    const existing = config.getMappingForControl(control)
    localMapping.value = existing ? { ...existing } : { name: '', action: '' }
  }
}, { immediate: true })

function markDirty() {
  config.dirty = true
}

function onActionChange(action) {
  localMapping.value.action = action
  markDirty()
}

function onMappingUpdate(updates) {
  localMapping.value = { ...localMapping.value, ...updates }
  markDirty()
}

function onLedUpdate(led) {
  localMapping.value.led = led
  markDirty()
}

async function save() {
  const control = selectedControl.value
  let type = 'note_on'
  let key = control.note || control.pushNote

  if (control.cc !== undefined) {
    // Determine CC type based on control type
    type = control.type === 'encoder' ? 'cc_relative' : 'cc_absolute'
    key = control.cc
  }

  config.updateMapping(type, key, localMapping.value)

  try {
    await config.saveConfig()
    ui.addToast('Configuration saved', 'success')
  } catch (e) {
    ui.addToast('Failed to save: ' + e.message, 'error')
  }
}

function revert() {
  const existing = config.getMappingForControl(selectedControl.value)
  localMapping.value = existing ? { ...existing } : { name: '', action: '' }
  config.dirty = false
}
</script>
