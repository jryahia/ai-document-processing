import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText } from 'lucide-react'
import {
  documentsApi,
  isProcessed,
  STATUS_LABELS,
  type Document,
  type DocumentStatus,
  type PaginationMeta,
} from '../api/client'
import toast from 'react-hot-toast'

interface DocumentListProps {
  documents: Document[]
  pagination: PaginationMeta
  onPageChange: (page: number) => void
  onDelete: (id: string) => void
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const STATUS_STYLES: Record<DocumentStatus, string> = {
  uploaded: 'status-uploaded',
  processing: 'status-processing',
  completed: 'status-completed',
  failed: 'status-failed',
  // index.css has no needs_review class; amber keeps it distinct from both the
  // green "completed" badge and the yellow "uploaded" one.
  needs_review: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
}

function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[status] || ''}`}>
      {status === 'processing' && (
        <svg className="animate-spin -ml-1 mr-1.5 h-3 w-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {status === 'needs_review' && (
        <svg className="-ml-0.5 mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
      )}
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

/** Colour bands for the heuristic score: green >= 80, amber >= 60, red below. */
function confidenceColor(score: number): string {
  if (score >= 80) return 'bg-green-500/10 text-green-400 border-green-500/30'
  if (score >= 60) return 'bg-amber-500/10 text-amber-400 border-amber-500/30'
  return 'bg-red-500/10 text-red-400 border-red-500/30'
}

function ConfidenceBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) {
    return <span className="text-xs text-gray-600">—</span>
  }
  return (
    <span
      title={`Extraction confidence: ${score}%`}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs font-medium ${confidenceColor(score)}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {score}%
    </span>
  )
}

export default function DocumentList({ documents, pagination, onPageChange, onDelete }: DocumentListProps) {
  const [deleting, setDeleting] = useState<string | null>(null)
  const [loadingDownload, setLoadingDownload] = useState<string | null>(null)

  const totalPages = Math.ceil(pagination.total / pagination.per_page)

  const handleDownload = async (doc: Document) => {
    if (!isProcessed(doc.status)) {
      toast.error('Document not ready for download')
      return
    }
    setLoadingDownload(doc.id)
    try {
      const res = await documentsApi.download(doc.id)
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = doc.original_name
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Download failed')
    } finally {
      setLoadingDownload(null)
    }
  }

  const handleDelete = async (doc: Document) => {
    if (!window.confirm(`Delete "${doc.original_name}"?`)) return
    setDeleting(doc.id)
    try {
      await documentsApi.delete(doc.id)
      toast.success('Document deleted')
      onDelete(doc.id)
    } catch {
      toast.error('Delete failed')
    } finally {
      setDeleting(null)
    }
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="text-gray-600 text-5xl mb-4"><FileText className="w-16 h-16 mx-auto" /></div>
        <p className="text-gray-500 text-lg">No documents yet</p>
        <p className="text-gray-600 text-sm mt-1">Upload a PDF or image to get started</p>
      </div>
    )
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dark-700">
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Name</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Size</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Status</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Confidence</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Date</th>
              <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700">
            {documents.map((doc) => (
              <tr
                key={doc.id}
                className={`hover:bg-dark-800/50 transition-colors ${
                  doc.needs_review ? 'bg-amber-500/[0.04] border-l-2 border-l-amber-500/60' : ''
                }`}
              >
                <td className="py-3 px-4">
                  <Link to={`/documents/${doc.id}`} className="text-sm font-medium text-gray-200 hover:text-accent-400 transition-colors">
                    {doc.original_name}
                  </Link>
                </td>
                <td className="py-3 px-4 text-sm text-gray-500">{formatSize(doc.file_size)}</td>
                <td className="py-3 px-4"><StatusBadge status={doc.status} /></td>
                <td className="py-3 px-4"><ConfidenceBadge score={doc.confidence_score} /></td>
                <td className="py-3 px-4 text-sm text-gray-500">{formatDate(doc.created_at)}</td>
                <td className="py-3 px-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {isProcessed(doc.status) && (
                      <>
                        <button
                          onClick={() => handleDownload(doc)}
                          disabled={loadingDownload === doc.id}
                          className="text-xs text-gray-400 hover:text-accent-400 transition-colors disabled:opacity-50"
                        >
                          {loadingDownload === doc.id ? '...' : 'Download'}
                        </button>
                        <Link
                          to={`/documents/${doc.id}`}
                          className="text-xs text-gray-400 hover:text-accent-400 transition-colors"
                        >
                          View
                        </Link>
                      </>
                    )}
                    <button
                      onClick={() => handleDelete(doc)}
                      disabled={deleting === doc.id}
                      className="text-xs text-gray-400 hover:text-red-400 transition-colors disabled:opacity-50"
                    >
                      {deleting === doc.id ? '...' : 'Delete'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4">
          <p className="text-sm text-gray-500">
            Page {pagination.page} of {totalPages} ({pagination.total} total)
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="btn-secondary text-sm py-1.5 px-3"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={pagination.page >= totalPages}
              className="btn-secondary text-sm py-1.5 px-3"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
