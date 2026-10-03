import { api } from './client'

export interface DashboardStats {
  qaTableCount: number
  qaItemCount: number
  deviceMappingCount: number
  database: string
}

export async function getDashboard() {
  return (await api.get<DashboardStats>('/api/admin/dashboard')).data
}
