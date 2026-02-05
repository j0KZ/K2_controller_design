<template>
  <div class="k2-grid">
    <!-- Layer Tabs -->
    <LayerTabs class="mb-4" />

    <!-- Folder Breadcrumb -->
    <FolderBreadcrumb v-if="k2State.folder" class="mb-4" />

    <!-- Control Rows -->
    <div class="space-y-2">
      <K2Row
        v-for="(row, idx) in k2State.getRows"
        :key="idx"
        :row="row"
      />
    </div>
  </div>
</template>

<script setup>
import { useK2State } from '@/stores/k2State'
import LayerTabs from './LayerTabs.vue'
import FolderBreadcrumb from './FolderBreadcrumb.vue'
import K2Row from './K2Row.vue'

const k2State = useK2State()
</script>
