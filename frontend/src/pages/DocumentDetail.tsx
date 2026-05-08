import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { documentsApi, type Document } from '../api/client'
import toast from 'react-hot-toast'

type Tab = 'ocr' | 'summary' | 'data'

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const [doc, setDoc] = useState<Document | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('summary')
  const [downloading, setDownloading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    const fetchDoc = async () => {
      try {
        const res = await documentsApi.get(id)
        setDoc(res.data)
      } catch {
        toast.error('Document not found')
      } finally {
        setLoading(false)
      }
    }
    fetchDoc()
  }, [id])

  const handleDownload = async () => {
    if (!doc || doc.status !== 'completed') return
    setDownloading(true)
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
      setDownloading(false)
    }
  }

  const handleReport = async () => {
    if (!doc || doc.status !== 'completed') return
    setReportLoading(true)
    try {
      const res = await documentsApi.report(doc.id)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${doc.original_name.split('.')[0]}_report.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Report generation failed')
    } finally {
      setReportLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent-500" />
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 text-lg">Document not found</p>
        <Link to="/documents" className="text-accent-400 hover:text-accent-300 mt-2 inline-block">
          Back to Documents
        </Link>
      </div>
    )
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'summary', label: 'AI Summary' },
    { key: 'ocr', label: 'OCR Text' },
    { key: 'data', label: 'Extracted Data' },
  ]

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link to="/documents" className="text-gray-500 hover:text-gray-300 transition-colors">
          ← Back
        </Link>
        <h1 className="text-2xl font-bold text-gray-100">{doc.original_name}</h1>
      </div>

      {/* Meta card */}
      <div className="card mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Type</p>
            <p className="text-sm text-gray-200 font-medium mt-1">{doc.file_type.toUpperCase()}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Size</p>
            <p className="text-sm text-gray-200 font-medium mt-1">
              {(doc.file_size / 1024).toFixed(1)} KB
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Status</p>
            <p className={`text-sm font-medium mt-1 ${
              doc.status === 'completed' ? 'text-green-400' :
              doc.status === 'processing' ? 'text-blue-400' :
              doc.status === 'failed' ? 'text-red-400' : 'text-yellow-400'
            }`}>
              {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Uploaded</p>
            <p className="text-sm text-gray-200 font-medium mt-1">
              {new Date(doc.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {doc.status === 'completed' && (
          <div className="flex gap-3 mt-4 pt-4 border-t border-dark-700">
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn-secondary text-sm"
            >
              {downloading ? 'Downloading...' : 'Download Original'}
            </button>
            <button
              onClick={handleReport}
              disabled={reportLoading}
              className="btn-secondary text-sm"
            >
              {reportLoading ? 'Generating...' : 'Download Report (PDF)'}
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      {doc.status === 'completed' && (
        <div className="card">
          <div className="flex gap-1 border-b border-dark-700 mb-4">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  activeTab === tab.key
                    ? 'text-accent-400 border-accent-500'
                    : 'text-gray-500 border-transparent hover:text-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="min-h-[300px]">
            {activeTab === 'summary' && (
              <div>
                {doc.ai_summary ? (
                  <div className="prose prose-invert max-w-none">
                    <div className="bg-dark-700/50 rounded-lg p-5 border border-dark-600">
                      <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">{doc.ai_summary}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-10">No summary available</p>
                )}
              </div>
            )}

            {activeTab === 'ocr' && (
              <div>
                {doc.ocr_text ? (
                  <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap bg-dark-700/30 rounded-lg p-5 border border-dark-600 max-h-[500px] overflow-y-auto">
                    {doc.ocr_text}
                  </pre>
                ) : (
                  <p className="text-gray-500 text-center py-10">No OCR text extracted</p>
                )}
              </div>
            )}

            {activeTab === 'data' && (
              <div>
                {doc.extracted_data && Object.keys(doc.extracted_data).length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-dark-600">
                          <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-2 px-4">Field</th>
                          <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-2 px-4">Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-700">
                        {Object.entries(doc.extracted_data).map(([key, value]) => (
                          <tr key={key} className="hover:bg-dark-700/30">
                            <td className="py-2.5 px-4 text-sm text-gray-400 font-medium">{key}</td>
                            <td className="py-2.5 px-4 text-sm text-gray-200">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-10">No structured data extracted</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {doc.status === 'processing' && (
        <div className="card text-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-accent-500 mx-auto mb-4" />
          <p className="text-gray-400">Processing document...</p>
          <p className="text-gray-600 text-sm mt-1">OCR extraction and AI analysis in progress</p>
        </div>
      )}

      {doc.status === 'failed' && (
        <div className="card text-center py-12 border-red-500/20">
          <p className="text-red-400 text-lg font-medium">Processing Failed</p>
          {doc.error_message && (
            <p className="text-gray-500 text-sm mt-2">{doc.error_message}</p>
          )}
        </div>
      )}
    </div>
  )
}
