import api from './client'

export interface Transaction {
  id: string
  account_id: string
  date: string
  amount: number
  label: string
  transaction_type: string
  category_id: string | null
  category_name: string | null
  is_categorized: boolean
  notes: string | null
}

export interface TransactionFilters {
  account_id?: string
  category_id?: string
  date_from?: string
  date_to?: string
  min_amount?: number
  max_amount?: number
  search?: string
  limit?: number
  offset?: number
}

export interface UpdateTransactionPayload {
  category_id?: string | null
  notes?: string | null
  label?: string
}

export const transactionsApi = {
  list: (filters: TransactionFilters = {}): Promise<{ data: Transaction[] }> =>
    api.get('/transactions/', { params: filters }),

  get: (id: string): Promise<{ data: Transaction }> => api.get(`/transactions/${id}`),

  update: (id: string, payload: UpdateTransactionPayload): Promise<{ data: Transaction }> =>
    api.patch(`/transactions/${id}`, payload),
}
