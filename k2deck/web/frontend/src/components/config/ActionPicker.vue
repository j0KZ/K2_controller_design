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
import { ACTION_GROUPS, formatActionName } from '@/constants/actions'

defineProps({
  modelValue: { type: String, default: '' },
})

defineEmits(['update:modelValue'])

const groupedActions = ACTION_GROUPS
</script>
