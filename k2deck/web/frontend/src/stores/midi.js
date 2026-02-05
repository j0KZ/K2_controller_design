import { defineStore } from 'pinia'

export const useMidi = defineStore('midi', {
  state: () => ({
    events: [],
    maxEvents: 100,
    paused: false,
  }),

  actions: {
    addEvent(event) {
      if (this.paused) return
      this.events.unshift({ ...event, timestamp: Date.now() })
      if (this.events.length > this.maxEvents) {
        this.events.pop()
      }
    },

    clear() { this.events = [] },
    togglePause() { this.paused = !this.paused },
  },
})
