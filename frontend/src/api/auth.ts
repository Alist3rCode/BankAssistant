import api from './client'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  requires_totp: boolean
  user_id: string
}

export interface UserInfo {
  id: string
  email: string
  totp_enabled: boolean
  last_login: string | null
}

export const authApi = {
  register: (email: string, password: string) =>
    api.post('/auth/register', { email, password }),

  login: (email: string, password: string): Promise<{ data: LoginResponse }> =>
    api.post('/auth/login', null, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: new URLSearchParams({ username: email, password }),
    }),

  verifyTotp: (user_id: string, code: string, temp_token: string): Promise<{ data: LoginResponse }> =>
    api.post('/auth/totp/verify', { user_id, code, temp_token }),

  refresh: (refresh_token: string): Promise<{ data: LoginResponse }> =>
    api.post('/auth/refresh', { refresh_token }),

  me: (): Promise<{ data: UserInfo }> => api.get('/auth/me'),

  setupTotp: () => api.get('/auth/totp/setup'),

  confirmTotp: (code: string) => api.post('/auth/totp/confirm', { code }),

  disableTotp: () => api.delete('/auth/totp'),
}
