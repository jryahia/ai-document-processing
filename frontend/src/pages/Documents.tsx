import { useState, useEffect, useCallback } from 'react'
import { documentsApi, type Document, type PaginationMeta } from '../api/client'
import UploadZone from '../components/UploadZone'
import DocumentList from '../components/DocumentList'
import SearchBar from '../components/SearchBar'

export default function Documents() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [pagination, setPagination] = useState<PaginationMeta>({ page: 1, per_page: 20, total: 0 })
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    try {
      if (searchQuery.trim()) {
        const res = await documentsApi.search(searchQuery, page)
        setDocuments(res.data.items)
        setPagination(res.data.pagination)
      } else {
        const res = await documentsApi.list(page)
        setDocuments(res.data.items)
        setPagination(res.data.pagination)
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [searchQuery, page])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  const handleSearch = useCallback((q: string) => {
    setSearchQuery(q)
    setPage(1)
  }, [])

  const handleUploadComplete = () => {
    fetchDocuments()
  }

  const handleDelete = () => {
    fetchDocuments()
  }

  const needsReviewCount = documents.filter((d) => d.needs_review).length

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Documents</h1>
        {needsReviewCount > 0 && (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            {needsReviewCount} need{needsReviewCount === 1 ? 's' : ''} review
          </span>
        )}
      </div>

      <div className="mb-6">
        <UploadZone onUploadComplete={handleUploadComplete} />
      </div>

      <div className="mb-4">
        <SearchBar onSearch={handleSearch} />
      </div>

      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent-500" />
          </div>
        ) : (
          <DocumentList
            documents={documents}
            pagination={pagination}
            onPageChange={setPage}
            onDelete={handleDelete}
          />
        )}
      </div>
    </div>
  )
}
