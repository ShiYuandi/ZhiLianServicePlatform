import { api } from './client'

export interface DeviceAddPayload {
  name: string
  board: string
  appVersion: string
  macAddress: string
}

export async function addDevice(data: DeviceAddPayload) {
  return (await api.post<Record<string, unknown>>('/api/device/add', data)).data
}
