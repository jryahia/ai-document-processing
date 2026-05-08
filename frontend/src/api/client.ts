import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// Auth
export const authApi = {
  register: (data: { email: string; password: string; name: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

// Documents
export interface Document {
  id: string
  original_name: string
  filename: string
  file_size: number
  file_type: string
  status: 'uploaded' | 'processing' | 'completed' | 'failed'
  ocr_text: string | null
  ai_summary: string | null
  extracted_data: Record<string, unknown> | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface PaginationMeta {
  page: number
  per_page: number
  total: number
}

export interface DocumentListResponse {
  items: Document[]
  pagination: PaginationMeta
}

export const documentsApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<Document>('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: (page = 1, perPage = 20) =>
    api.get<DocumentListResponse>('/documents', { params: { page, per_page: perPage } }),
  search: (q: string, page = 1, perPage = 20) =>
    api.get<DocumentListResponse>('/documents/search', { params: { q, page, per_page: perPage } }),
  get: (id: string) => api.get<Document>(`/documents/${id}`),
  download: (id: string) =>
    api.get(`/documents/${id}/download`, { responseType: 'blob' }),
  delete: (id: string) => api.delete(`/documents/${id}`),
  report: (id: string) =>
    api.get(`/documents/${id}/report`, { responseType: 'blob' }),
}

// Notifications
export const notificationsApi = {
  get: () => api.get('/notifications'),
  update: (data: { email_address: string; email_enabled: boolean }) =>
    api.put('/notifications', data),
}
