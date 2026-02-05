import { defineStore } from 'pinia'

export const useAnalogState = defineStore('analogState', {
  state: () => ({
    positions: {},  // { cc: value }
  }),

  getters: {
    getPosition: (state) => (cc) => state.positions[cc] ?? 0,
    getPercent: (state) => (cc) => Math.round((state.positions[cc] ?? 0) / 127 * 100),
  },

  actions: {
    handleChange(cc, value) {
      this.positions[cc] = value
    },

    initFromState(controls) {
      for (const { cc, value } of controls) {
        this.positions[cc] = value
      }
    },
  },
})
