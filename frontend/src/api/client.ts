import axios from 'axios'

export const api = axios.create({
  baseURL: '/',
  withCredentials: true,
  timeout: 15000,
})

function readCookie(name: string): string {
  const prefix = `${name}=`
  const value = document.cookie.split('; ').find((entry) => entry.startsWith(prefix))
  return value ? decodeURIComponent(value.slice(prefix.length)) : ''
}

api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase()
  if (method && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = readCookie('xz_csrf')
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !location.pathname.endsWith('/login')) {
      location.assign('/admin/login')
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data
    if (data?.message) return data.message
    if (Array.isArray(data?.detail)) {
      const fields = data.detail.map((item: { loc?: unknown[]; msg?: string }) => {
        const loc = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body' && part !== 'query').join('.') : ''
        return loc ? `${loc}：${item.msg || '参数不合法'}` : item.msg || '参数不合法'
      })
      if (fields.length) return `请求参数校验失败：${fields.join('；')}`
    }
    return error.message || '请求失败'
  }
  return error instanceof Error ? error.message : '请求失败'
}
