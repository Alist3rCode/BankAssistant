import { defineStore } from 'pinia'
import { ref } from 'vue'
import { transactionsApi, type Transaction, type TransactionFilters } from '@/api/transactions'

export const useTransactionsStore = defineStore('transactions', () => {
  const transactions = ref<Transaction[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const filters = ref<TransactionFilters>({ limit: 50, offset: 0 })

  async function fetchTransactions(newFilters?: TransactionFilters) {
    loading.value = true
    error.value = null
    if (newFilters) filters.value = { ...filters.value, ...newFilters }
    try {
      const { data } = await transactionsApi.list(filters.value)
      transactions.value = data
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'Erreur de chargement'
    } finally {
      loading.value = false
    }
  }

  async function updateTransaction(id: string, payload: { category_id?: string | null; notes?: string | null }) {
    const { data } = await transactionsApi.update(id, payload)
    const idx = transactions.value.findIndex((t) => t.id === id)
    if (idx !== -1) transactions.value[idx] = data
    return data
  }

  return { transactions, loading, error, filters, fetchTransactions, updateTransaction }
})
