import { api } from './client'

export interface AdminProfile {
  id: number
  username: string
  csrf_token: string
}

export async function login(username: string, password: string) {
  return (await api.post<AdminProfile>('/api/admin/auth/login', { username, password })).data
}

export async function currentAdmin() {
  return (await api.get<AdminProfile>('/api/admin/auth/me')).data
}

export async function logout() {
  return api.post('/api/admin/auth/logout')
}

export async function changePassword(currentPassword: string, newPassword: string) {
  return api.put('/api/admin/auth/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}
