import { api } from './client'

export interface QaTable {
  id: number
  name: string
  description?: string
  item_count: number
  created_at: string
  updated_at: string
}

export interface QaItem {
  id: number
  table_id: number
  question: string
  answer: string
  sort_order: number
  created_at: string
  updated_at: string
}

interface Page<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export async function listQaTables(params: Record<string, unknown>) {
  return (await api.get<Page<QaTable>>('/api/admin/qa-tables', { params })).data
}
export async function createQaTable(data: { name: string; description?: string }) {
  return (await api.post<QaTable>('/api/admin/qa-tables', data)).data
}
export async function updateQaTable(id: number, data: { name: string; description?: string }) {
  return (await api.put<QaTable>(`/api/admin/qa-tables/${id}`, data)).data
}
export async function deleteQaTable(id: number) {
  return api.delete(`/api/admin/qa-tables/${id}`)
}
export async function listQaItems(tableId: number, params: Record<string, unknown>) {
  return (await api.get<Page<QaItem>>(`/api/admin/qa-tables/${tableId}/items`, { params })).data
}
export async function createQaItem(
  tableId: number,
  data: Omit<QaItem, 'id' | 'table_id' | 'created_at' | 'updated_at'>,
) {
  return (await api.post<QaItem>(`/api/admin/qa-tables/${tableId}/items`, data)).data
}
export async function updateQaItem(
  id: number,
  data: Omit<QaItem, 'id' | 'table_id' | 'created_at' | 'updated_at'>,
) {
  return (await api.put<QaItem>(`/api/admin/qa-items/${id}`, data)).data
}
export async function deleteQaItem(id: number) {
  return api.delete(`/api/admin/qa-items/${id}`)
}
export async function batchQaItems(
  tableId: number,
  items: Array<{ question: string; answer: string; sort_order: number }>,
) {
  return api.post(`/api/admin/qa-tables/${tableId}/items/batch`, { items })
}
export async function importQaExcel(tableId: number, file: File, mode: 'append' | 'replace') {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/api/admin/qa-tables/${tableId}/import`, form, { params: { mode } })
}
