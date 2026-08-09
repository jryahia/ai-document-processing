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
export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'needs_review'

/** Statuses where OCR/AI output exists and the document can be viewed or downloaded. */
export function isProcessed(status: DocumentStatus): boolean {
  return status === 'completed' || status === 'needs_review'
}

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: 'Uploaded',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
  needs_review: 'Needs Review',
}

export interface Document {
  id: string
  original_name: string
  filename: string
  file_size: number
  file_type: string
  status: DocumentStatus
  ocr_text: string | null
  ai_summary: string | null
  extracted_data: Record<string, unknown> | null
  /** Heuristic extraction-completeness score, 0-100. Null until processing finishes. */
  confidence_score: number | null
  needs_review: boolean
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface PaginationMeta {
  page: number
  per_page: number
  total: number
}

/** Raw shape the FastAPI backend returns for paginated document lists. */
interface BackendListResponse {
  items: Document[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface DocumentListResponse {
  items: Document[]
  pagination: PaginationMeta
}

/** Map backend top-level {items,total,page,page_size,pages} -> {items,pagination}. */
function toListResponse(data: BackendListResponse): DocumentListResponse {
  return {
    items: data.items,
    pagination: {
      page: data.page,
      per_page: data.page_size,
      total: data.total,
    },
  }
}

export interface BatchUploadItem {
  filename: string
  document_id: string | null
  status: 'accepted' | 'rejected'
  error?: string | null
}

export interface BatchUploadResponse {
  results: BatchUploadItem[]
  accepted: number
  rejected: number
}

export const documentsApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<Document>('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  uploadBatch: (files: File[]) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return api.post<BatchUploadResponse>('/documents/upload/batch', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: async (page = 1, perPage = 20) => {
    const res = await api.get<BackendListResponse>('/documents', {
      params: { page, per_page: perPage },
    })
    return { ...res, data: toListResponse(res.data) }
  },
  search: async (q: string, page = 1, perPage = 20) => {
    const res = await api.get<BackendListResponse>('/documents/search', {
      params: { q, page, per_page: perPage },
    })
    return { ...res, data: toListResponse(res.data) }
  },
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
  update: (data: { email_address: string; email_enabled: boolean; webhook_url?: string }) =>
    api.put('/notifications', data),
}
