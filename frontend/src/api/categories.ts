import api from './client'

export interface Category {
  id: string
  name: string
  icon: string | null
  color: string | null
  is_income: boolean
  is_system: boolean
}

export interface CategoryCreate {
  name: string
  icon?: string | null
  color?: string | null
  is_income?: boolean
}

export interface CategoryRule {
  id: string
  pattern: string
  match_type: string
  category_id: string
  category_name: string
  priority: number
  is_active: boolean
}

export interface RuleCreate {
  pattern: string
  match_type: string
  category_id: string
  priority: number
  is_active: boolean
}

export const categoriesApi = {
  list: () => api.get<Category[]>('/categories/'),
  create: (data: CategoryCreate) => api.post<Category>('/categories/', data),
  update: (id: string, data: CategoryCreate) => api.put<Category>(`/categories/${id}`, data),
  delete: (id: string) => api.delete(`/categories/${id}`),
}

export const categoryRulesApi = {
  list: () => api.get<CategoryRule[]>('/category-rules/'),
  create: (data: RuleCreate) => api.post<CategoryRule>('/category-rules/', data),
  update: (id: string, data: RuleCreate) => api.put<CategoryRule>(`/category-rules/${id}`, data),
  delete: (id: string) => api.delete(`/category-rules/${id}`),
  apply: (allTransactions = false) =>
    api.post<{ updated: number; message: string }>(`/category-rules/apply?all_transactions=${allTransactions}`),
}
