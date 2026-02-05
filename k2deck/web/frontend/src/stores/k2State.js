import { defineStore } from 'pinia'
import { useApi } from '@/composables/useApi'

export const useK2State = defineStore('k2State', {
  state: () => ({
    layout: null,
    connected: false,
    port: null,
    layer: 1,
    folder: null,
    leds: {},  // { note: color }
    loading: false,
    error: null,
  }),

  getters: {
    getLedState: (state) => (note) => state.leds[note] || null,
    isConnected: (state) => state.connected,
    getRows: (state) => state.layout?.rows || [],
  },

  actions: {
    async fetchLayout() {
      const api = useApi()
      try {
        this.layout = await api.get('/k2/layout')
      } catch (e) {
        this.error = e.message
      }
    },

    async fetchState() {
      const api = useApi()
      try {
        const state = await api.get('/k2/state')
        this.connected = state.connected
        this.port = state.port
        this.layer = state.layer
        this.folder = state.folder
        this.leds = state.leds
      } catch (e) {
        this.error = e.message
      }
    },

    handleLedChange(data) {
      if (data.on && data.color) {
        this.leds[data.note] = data.color
      } else {
        delete this.leds[data.note]
      }
    },

    setLayer(layer) { this.layer = layer },
    setFolder(folder) { this.folder = folder },
    setConnection(connected, port) {
      this.connected = connected
      this.port = port
    },

    async setLed(note, color) {
      const api = useApi()
      await api.put(`/k2/state/leds/${note}`, { note, color, on: !!color })
    },
  },
})
