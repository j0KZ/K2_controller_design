import { defineStore } from 'pinia'
import { useApi } from '@/composables/useApi'

export const useIntegrations = defineStore('integrations', {
  state: () => ({
    obs: { available: false, connected: false, status: 'unavailable', error: null },
    spotify: { available: false, connected: false, status: 'unavailable', error: null },
    twitch: { available: false, connected: false, status: 'unavailable', error: null },
  }),

  actions: {
    async fetchAll() {
      const api = useApi()
      try {
        const data = await api.get('/integrations')
        this.obs = data.obs
        this.spotify = data.spotify
        this.twitch = data.twitch
      } catch (e) {
        console.error('Failed to fetch integrations:', e)
      }
    },

    handleChange(name, status) {
      if (this[name]) {
        this[name].status = status
        this[name].connected = status === 'connected'
      }
    },

    async connect(name, params = {}) {
      const api = useApi()
      try {
        const result = await api.post(`/integrations/${name}/connect`, params)
        this[name] = result
      } catch (e) {
        this[name].error = e.message
      }
    },

    async disconnect(name) {
      const api = useApi()
      try {
        const result = await api.post(`/integrations/${name}/disconnect`)
        this[name] = result
      } catch (e) {
        this[name].error = e.message
      }
    },
  },
})
