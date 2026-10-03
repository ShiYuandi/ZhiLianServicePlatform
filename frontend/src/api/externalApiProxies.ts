import { api } from './client'

export interface ExternalApiProxy {
  proxyUuid: string
  targetUrl: string
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface ExternalApiProxyPayload {
  targetUrl: string
  enabled: boolean
}

interface Page {
  items: ExternalApiProxy[]
  page: number
  pageSize: number
  total: number
}

const path = '/api/admin/external-api-proxies'

export async function listExternalApiProxies(params: Record<string, unknown>) {
  return (await api.get<Page>(path, { params })).data
}

export async function createExternalApiProxy(data: ExternalApiProxyPayload) {
  return (await api.post<ExternalApiProxy>(path, data)).data
}

export async function updateExternalApiProxy(uuid: string, data: ExternalApiProxyPayload) {
  return (await api.put<ExternalApiProxy>(`${path}/${uuid}`, data)).data
}

export async function deleteExternalApiProxy(uuid: string) {
  return api.delete(`${path}/${uuid}`)
}
