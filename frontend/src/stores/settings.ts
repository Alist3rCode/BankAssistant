import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi, type Setting } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Record<string, unknown>>({})
  const loading = ref(false)

  async function fetchSettings() {
    loading.value = true
    try {
      const { data } = await settingsApi.getAll()
      settings.value = Object.fromEntries(data.map((s: Setting) => [s.key, s.value]))
    } finally {
      loading.value = false
    }
  }

  function get(key: string, defaultValue: unknown = ''): unknown {
    return settings.value[key] ?? defaultValue
  }

  async function set(key: string, value: unknown) {
    await settingsApi.update(key, value)
    settings.value[key] = value
  }

  async function setBatch(updates: Record<string, unknown>) {
    await settingsApi.updateBatch(updates)
    Object.assign(settings.value, updates)
  }

  return { settings, loading, fetchSettings, get, set, setBatch }
})
