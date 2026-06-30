import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface Budget {
  id: string
  name: string
  description: string | null
  target_amount: number | null
  currency: string
  period_type: string
  color: string | null
  is_active: boolean
  is_default: boolean
  spent: number
  income: number
  entry_count: number
}

export const useBudgetsStore = defineStore('budgets', () => {
  const budgets = ref<Budget[]>([])
  const loading = ref(false)

  async function fetchBudgets() {
    loading.value = true
    try {
      const { data } = await api.get<Budget[]>('/budgets/')
      budgets.value = data
    } finally {
      loading.value = false
    }
  }

  async function createBudget(payload: Partial<Budget>) {
    const { data } = await api.post<Budget>('/budgets/', payload)
    budgets.value.push(data)
    return data
  }

  async function updateBudget(id: string, payload: Partial<Budget>) {
    const { data } = await api.put<Budget>(`/budgets/${id}`, payload)
    const idx = budgets.value.findIndex(b => b.id === id)
    if (idx !== -1) budgets.value[idx] = data
    return data
  }

  async function deleteBudget(id: string) {
    await api.delete(`/budgets/${id}`)
    budgets.value = budgets.value.filter(b => b.id !== id)
  }

  return { budgets, loading, fetchBudgets, createBudget, updateBudget, deleteBudget }
})
