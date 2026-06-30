import api from './client'

export interface Account {
  id: string
  name: string
  number_masked: string
  account_type: string
  balance: number
  currency: string
  ca_region: string
  is_active: boolean
  last_synced: string | null
}

export interface CARegion {
  id: string
  name: string
  url: string
}

export const accountsApi = {
  list: (): Promise<{ data: Account[] }> => api.get('/accounts/'),
  get: (id: string): Promise<{ data: Account }> => api.get(`/accounts/${id}`),
  listRegions: (): Promise<{ data: CARegion[] }> => api.get('/accounts/regions'),
}
