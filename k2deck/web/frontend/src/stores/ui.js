import { defineStore } from 'pinia'

export const useUi = defineStore('ui', {
  state: () => ({
    selectedControl: null,  // { id, type, note?, cc? }
    selectedLayer: 1,
    toasts: [],
  }),

  actions: {
    selectControl(control) {
      this.selectedControl = control
    },

    clearSelection() {
      this.selectedControl = null
    },

    addToast(message, type = 'info', duration = 3000) {
      const id = Date.now()
      this.toasts.push({ id, message, type })
      setTimeout(() => this.removeToast(id), duration)
    },

    removeToast(id) {
      this.toasts = this.toasts.filter(t => t.id !== id)
    },
  },
})
