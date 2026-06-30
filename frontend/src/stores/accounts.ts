import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { accountsApi, type Account } from '@/api/accounts'

export const useAccountsStore = defineStore('accounts', () => {
  const accounts = ref<Account[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const totalBalance = computed(() =>
    accounts.value.reduce((sum, a) => sum + a.balance, 0)
  )

  async function fetchAccounts() {
    loading.value = true
    error.value = null
    try {
      const { data } = await accountsApi.list()
      accounts.value = data
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'Erreur de chargement des comptes'
    } finally {
      loading.value = false
    }
  }

  return { accounts, loading, error, totalBalance, fetchAccounts }
})
