import api from './client'

export interface Setting {
  key: string
  value: unknown
  is_encrypted: boolean
}

export const settingsApi = {
  getAll: (): Promise<{ data: Setting[] }> => api.get('/settings/'),

  get: (key: string): Promise<{ data: Setting }> => api.get(`/settings/${key}`),

  update: (key: string, value: unknown) =>
    api.put(`/settings/${key}`, { value }),

  updateBatch: (settings: Record<string, unknown>) =>
    api.put('/settings/batch', settings),

  testConnection: (region_id: string, login: string, password: string) =>
    api.post('/scraper/test-connection', { region_id, login, password }),

  triggerScraping: () => api.post('/scraper/trigger'),

  getScraperStatus: () => api.get('/scraper/status'),
}
