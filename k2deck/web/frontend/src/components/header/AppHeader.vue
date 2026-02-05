<template>
  <header class="app-header h-14 bg-k2-surface border-b border-k2-border flex items-center justify-between px-4">
    <div class="flex items-center gap-4">
      <h1 class="text-lg font-bold">K2 Deck</h1>
      <ConnectionStatus />
    </div>

    <div class="flex items-center gap-4">
      <IntegrationPills />
      <ProfileDropdown />
    </div>
  </header>
</template>

<script setup>
import ConnectionStatus from './ConnectionStatus.vue'
import IntegrationPills from './IntegrationPills.vue'
import ProfileDropdown from './ProfileDropdown.vue'
</script>
