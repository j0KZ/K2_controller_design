import { defineStore } from 'pinia'
import { useApi } from '@/composables/useApi'

export const useProfiles = defineStore('profiles', {
  state: () => ({
    profiles: [],
    activeProfile: 'default',
    loading: false,
    error: null,
  }),

  getters: {
    profileNames: (state) => state.profiles.map(p => p.name),
    isActive: (state) => (name) => name === state.activeProfile,
  },

  actions: {
    async fetchProfiles() {
      const api = useApi()
      this.loading = true
      try {
        const data = await api.get('/profiles')
        this.profiles = data.profiles || []
        this.activeProfile = data.active || 'default'
        this.error = null
      } catch (e) {
        this.error = e.message
        // Fallback defaults
        this.profiles = [{ name: 'default' }]
        this.activeProfile = 'default'
      } finally {
        this.loading = false
      }
    },

    async createProfile(name, copyFrom = null) {
      const api = useApi()
      this.loading = true
      try {
        await api.post('/profiles', { name, copy_from: copyFrom })
        await this.fetchProfiles()
        this.error = null
        return true
      } catch (e) {
        this.error = e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    async deleteProfile(name) {
      const api = useApi()
      this.loading = true
      try {
        await api.del(`/profiles/${name}`)
        await this.fetchProfiles()
        this.error = null
        return true
      } catch (e) {
        this.error = e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    async activateProfile(name) {
      const api = useApi()
      this.loading = true
      try {
        await api.put(`/profiles/${name}/activate`)
        this.activeProfile = name
        this.error = null
        return true
      } catch (e) {
        this.error = e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    exportProfile(name) {
      window.location.href = `/api/profiles/${name}/export`
    },

    async importProfile(file) {
      this.loading = true
      try {
        const form = new FormData()
        form.append('file', file)
        const resp = await fetch('/api/profiles/import', { method: 'POST', body: form })
        if (!resp.ok) {
          const err = await resp.json().catch(() => null)
          const detail = err?.detail
          const msg = typeof detail === 'string' ? detail : detail?.message || 'Import failed'
          throw new Error(msg)
        }
        const data = await resp.json()
        await this.fetchProfiles()
        this.error = null
        return data
      } catch (e) {
        this.error = e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    handleChange(profile) {
      this.activeProfile = profile
    },
  },
})
