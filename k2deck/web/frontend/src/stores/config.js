import { defineStore } from 'pinia'
import { useApi } from '@/composables/useApi'

export const useConfig = defineStore('config', {
  state: () => ({
    config: null,
    dirty: false,
    loading: false,
    error: null,
  }),

  getters: {
    getMappingForControl: (state) => (control) => {
      if (!state.config?.mappings) return null

      // Check note_on for buttons
      if (control.note !== undefined) {
        return state.config.mappings.note_on?.[control.note] || null
      }
      // Check note_on for encoder push
      if (control.pushNote !== undefined) {
        return state.config.mappings.note_on?.[control.pushNote] || null
      }
      // Check cc_absolute for faders/pots
      if (control.cc !== undefined) {
        return state.config.mappings.cc_absolute?.[control.cc] ||
               state.config.mappings.cc_relative?.[control.cc] || null
      }
      return null
    },

    hasUnsavedChanges: (state) => state.dirty,
  },

  actions: {
    async fetchConfig() {
      const api = useApi()
      this.loading = true
      try {
        this.config = await api.get('/config')
        this.dirty = false
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },

    updateMapping(type, key, mapping) {
      if (!this.config) return
      if (!this.config.mappings) {
        this.config.mappings = {}
      }
      if (!this.config.mappings[type]) {
        this.config.mappings[type] = {}
      }
      this.config.mappings[type][key] = mapping
      this.dirty = true
    },

    deleteMapping(type, key) {
      if (this.config?.mappings?.[type]) {
        delete this.config.mappings[type][String(key)]
        this.dirty = true
      }
    },

    async saveConfig() {
      const api = useApi()
      this.loading = true
      try {
        await api.put('/config', { config: this.config })
        this.dirty = false
      } catch (e) {
        this.error = e.message
        throw e
      } finally {
        this.loading = false
      }
    },
  },
})
