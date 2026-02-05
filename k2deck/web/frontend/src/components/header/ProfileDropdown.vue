<template>
  <div class="profile-dropdown relative">
    <button
      class="flex items-center gap-2 px-3 py-2 bg-k2-surface rounded hover:bg-k2-surface-hover border border-k2-border"
      @click="open = !open"
    >
      <span>{{ profiles.activeProfile }}</span>
      <span class="text-xs">▼</span>
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-full mt-1 w-56 bg-k2-surface border border-k2-border rounded shadow-lg z-50"
    >
      <!-- Profile list -->
      <button
        v-for="profile in profiles.profiles"
        :key="profile.name"
        class="w-full px-3 py-2 text-left hover:bg-k2-surface-hover flex justify-between items-center"
        @click="selectProfile(profile.name)"
      >
        <span>{{ profile.name }}</span>
        <span v-if="profiles.isActive(profile.name)" class="text-k2-success text-xs">●</span>
      </button>

      <hr class="border-k2-border" />

      <!-- Create new profile inline form -->
      <div v-if="showCreateForm" class="p-3 space-y-2">
        <input
          v-model="newProfileName"
          type="text"
          class="form-input w-full text-sm"
          placeholder="Profile name"
          @keyup.enter="createProfile"
          @keyup.escape="cancelCreate"
          ref="createInput"
        />
        <div class="flex gap-2">
          <button
            class="btn-primary text-xs py-1 flex-1"
            @click="createProfile"
            :disabled="!newProfileName.trim() || profiles.loading"
          >
            Create
          </button>
          <button
            class="btn-secondary text-xs py-1"
            @click="cancelCreate"
          >
            Cancel
          </button>
        </div>
        <label class="flex items-center gap-2 text-xs text-k2-text-secondary">
          <input
            v-model="copyFromCurrent"
            type="checkbox"
            class="w-3 h-3"
          />
          Copy from current profile
        </label>
      </div>

      <button
        v-else
        class="w-full px-3 py-2 text-left hover:bg-k2-surface-hover text-k2-accent"
        @click="showCreate"
      >
        + New Profile
      </button>
    </div>

    <!-- Click outside to close -->
    <div
      v-if="open"
      class="fixed inset-0 z-40"
      @click="closeDropdown"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useProfiles } from '@/stores/profiles'
import { useConfig } from '@/stores/config'
import { useUi } from '@/stores/ui'

const profiles = useProfiles()
const config = useConfig()
const ui = useUi()

const open = ref(false)
const showCreateForm = ref(false)
const newProfileName = ref('')
const copyFromCurrent = ref(true)
const createInput = ref(null)

onMounted(() => profiles.fetchProfiles())

async function selectProfile(name) {
  try {
    await profiles.activateProfile(name)
    await config.fetchConfig()
    ui.addToast(`Switched to ${name}`, 'success')
  } catch (e) {
    ui.addToast(`Failed to switch profile: ${e.message}`, 'error')
  }
  open.value = false
}

function showCreate() {
  showCreateForm.value = true
  newProfileName.value = ''
  copyFromCurrent.value = true
  nextTick(() => createInput.value?.focus())
}

function cancelCreate() {
  showCreateForm.value = false
  newProfileName.value = ''
}

async function createProfile() {
  const name = newProfileName.value.trim()
  if (!name) return

  try {
    const copyFrom = copyFromCurrent.value ? profiles.activeProfile : null
    await profiles.createProfile(name, copyFrom)
    await profiles.activateProfile(name)
    await config.fetchConfig()
    ui.addToast(`Created profile: ${name}`, 'success')
    showCreateForm.value = false
    newProfileName.value = ''
    open.value = false
  } catch (e) {
    ui.addToast(`Failed to create profile: ${e.message}`, 'error')
  }
}

function closeDropdown() {
  open.value = false
  showCreateForm.value = false
  newProfileName.value = ''
}
</script>
