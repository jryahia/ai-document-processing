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

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Documents</h1>

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
