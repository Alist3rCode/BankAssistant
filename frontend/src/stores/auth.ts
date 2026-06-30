import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<UserInfo | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const { data } = await authApi.login(email, password)
      if (data.requires_totp) {
        return { requires_totp: true, user_id: data.user_id }
      }
      setTokens(data.access_token, data.refresh_token)
      await fetchMe()
      return { requires_totp: false }
    } finally {
      loading.value = false
    }
  }

  async function loginWithTotp(user_id: string, code: string, temp_token: string) {
    loading.value = true
    try {
      const { data } = await authApi.verifyTotp(user_id, code, temp_token)
      setTokens(data.access_token, data.refresh_token)
      await fetchMe()
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    try {
      const { data } = await authApi.me()
      user.value = data
    } catch {
      clearTokens()
    }
  }

  function logout() {
    clearTokens()
  }

  // Init : charger le user si token présent
  if (accessToken.value) {
    fetchMe()
  }

  return { accessToken, refreshToken, user, loading, isAuthenticated, login, loginWithTotp, logout, fetchMe }
})
