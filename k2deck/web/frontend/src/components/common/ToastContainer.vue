<template>
  <div class="toast-container fixed bottom-20 right-4 space-y-2 z-50">
    <TransitionGroup name="toast">
      <div
        v-for="toast in ui.toasts"
        :key="toast.id"
        class="px-4 py-2 rounded shadow-lg text-sm flex items-center gap-2"
        :class="toastClasses(toast.type)"
      >
        <span>{{ toast.message }}</span>
        <button
          class="opacity-70 hover:opacity-100"
          @click="ui.removeToast(toast.id)"
        >
          ✕
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useUi } from '@/stores/ui'

const ui = useUi()

function toastClasses(type) {
  const classes = {
    info: 'bg-k2-accent text-white',
    success: 'bg-k2-success text-black',
    warning: 'bg-k2-warning text-black',
    error: 'bg-k2-error text-white',
  }
  return classes[type] || classes.info
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(100px);
}
</style>
