import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { documentsApi, type Document } from '../api/client'

interface Stats {
  total: number
  completed: number
  processing: number
  failed: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({ total: 0, completed: 0, processing: 0, failed: 0 })
  const [recent, setRecent] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await documentsApi.list(1, 100)
        const docs = res.data.items
        setStats({
          total: res.data.pagination.total,
          completed: docs.filter((d) => d.status === 'completed').length,
          processing: docs.filter((d) => d.status === 'processing').length,
          failed: docs.filter((d) => d.status === 'failed').length,
        })
        setRecent(docs.slice(0, 5))
      } catch {
        // silently fail
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const cards = [
    { label: 'Total Documents', value: stats.total, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
    { label: 'Processed', value: stats.completed, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20' },
    { label: 'Processing', value: stats.processing, color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' },
    { label: 'Failed', value: stats.failed, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent-500" />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <Link to="/documents" className="btn-primary text-sm">
          Upload Document
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((card) => (
          <div key={card.label} className={`${card.bg} ${card.border} border rounded-xl p-5`}>
            <p className="text-sm text-gray-500 mb-1">{card.label}</p>
            <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* Recent Uploads */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-200 mb-4">Recent Uploads</h2>
        {recent.length === 0 ? (
          <p className="text-gray-500 text-sm py-6 text-center">No documents uploaded yet</p>
        ) : (
          <div className="space-y-2">
            {recent.map((doc) => (
              <Link
                key={doc.id}
                to={`/documents/${doc.id}`}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-dark-700 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">
                    {doc.file_type === 'pdf' ? '📕' : doc.file_type === 'png' ? '🖼️' : '🖼️'}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-200">{doc.original_name}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  doc.status === 'completed' ? 'text-green-400 bg-green-500/10' :
                  doc.status === 'processing' ? 'text-blue-400 bg-blue-500/10' :
                  doc.status === 'failed' ? 'text-red-400 bg-red-500/10' :
                  'text-yellow-400 bg-yellow-500/10'
                }`}>
                  {doc.status}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
