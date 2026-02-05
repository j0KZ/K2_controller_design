<template>
  <div class="k2-row flex gap-2 justify-center">
    <K2Control
      v-for="control in row.controls"
      :key="control.id"
      :control="control"
      :row-type="row.type"
    />
  </div>
</template>

<script setup>
import K2Control from './K2Control.vue'

defineProps({
  row: { type: Object, required: true },
})
</script>
