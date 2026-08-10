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

// LLM provider settings (AI Provider section)
export type LLMProvider = 'openai' | 'deepseek' | 'openrouter' | 'groq' | 'custom'

export const LLM_PROVIDER_PRESETS: Record<LLMProvider, { base_url: string; model: string }> = {
  openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  deepseek: { base_url: 'https://api.deepseek.com', model: 'deepseek-chat' },
  openrouter: { base_url: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o-mini' },
  groq: { base_url: 'https://api.groq.com/openai/v1', model: 'llama-3.1-8b-instant' },
  custom: { base_url: '', model: '' },
}

export const LLM_PROVIDER_LABELS: Record<LLMProvider, string> = {
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
  openrouter: 'OpenRouter',
  groq: 'Groq',
  custom: 'Custom / Other',
}

export interface LLMSettings {
  provider: LLMProvider
  base_url: string
  model: string
  has_api_key: boolean
  last_test_status: 'ok' | 'failed' | null
  last_test_message: string | null
  last_test_at: string | null
}

export interface LLMTestResult {
  success: boolean
  provider: string
  model: string
  message: string
  tested_at: string
}

export const llmSettingsApi = {
  get: () => api.get<LLMSettings>('/llm-settings'),
  update: (data: { provider: LLMProvider; base_url: string; model: string; api_key?: string }) =>
    api.put<LLMSettings>('/llm-settings', data),
  test: (data: { provider: LLMProvider; base_url: string; model: string; api_key?: string }) =>
    api.post<LLMTestResult>('/llm-settings/test', data),
}
