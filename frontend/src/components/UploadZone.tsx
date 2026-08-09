import { useCallback, useState } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'
import { documentsApi } from '../api/client'
import toast from 'react-hot-toast'

interface UploadZoneProps {
  onUploadComplete: () => void
}

type FileStatus = 'queued' | 'uploading' | 'complete' | 'error'

interface FileState {
  status: FileStatus
  error?: string
}

/** filename -> status. Duplicate names within one batch collapse to a single row. */
type StatusMap = Record<string, FileState>

const STATUS_LABEL: Record<FileStatus, string> = {
  queued: 'Queued',
  uploading: 'Uploading...',
  complete: 'Uploaded',
  error: 'Failed',
}

const STATUS_CLASS: Record<FileStatus, string> = {
  queued: 'text-gray-400',
  uploading: 'text-accent-400',
  complete: 'text-green-400',
  error: 'text-red-400',
}

export default function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const [uploading, setUploading] = useState(false)
  const [statuses, setStatuses] = useState<StatusMap>({})

  const onDrop = useCallback(
    async (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      if (!acceptedFiles.length && !fileRejections.length) return

      // Seed the map: client-side rejects are terminal, accepted files start uploading.
      const initial: StatusMap = {}
      fileRejections.forEach(({ file, errors }) => {
        initial[file.name] = {
          status: 'error',
          error: errors.map((e) => e.message).join(', '),
        }
      })
      acceptedFiles.forEach((file) => {
        initial[file.name] = { status: 'queued' }
      })
      setStatuses(initial)

      if (!acceptedFiles.length) {
        onUploadComplete()
        return
      }

      setUploading(true)
      // One request carries the whole batch, so every accepted file goes in flight together.
      setStatuses((prev) => {
        const next = { ...prev }
        acceptedFiles.forEach((file) => {
          next[file.name] = { status: 'uploading' }
        })
        return next
      })
      try {
        const res = await documentsApi.uploadBatch(acceptedFiles)
        setStatuses((prev) => {
          const next = { ...prev }
          res.data.results.forEach((r) => {
            next[r.filename] =
              r.status === 'accepted'
                ? { status: 'complete' }
                : { status: 'error', error: r.error ?? 'Rejected' }
          })
          return next
        })

        const { accepted, rejected } = res.data
        if (accepted) toast.success(`${accepted} file${accepted > 1 ? 's' : ''} uploaded`)
        if (rejected) toast.error(`${rejected} file${rejected > 1 ? 's' : ''} rejected`)
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Upload failed'
        // Nothing came back — anything still in flight failed.
        setStatuses((prev) => {
          const next = { ...prev }
          Object.keys(next).forEach((name) => {
            if (next[name].status === 'uploading') {
              next[name] = { status: 'error', error: msg }
            }
          })
          return next
        })
        toast.error(msg)
      } finally {
        setUploading(false)
        onUploadComplete()
      }
    },
    [onUploadComplete]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    maxSize: 20 * 1024 * 1024,
    disabled: uploading,
  })

  const rows = Object.entries(statuses)

  return (
    <div className="flex flex-col gap-3">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200 ${
          isDragActive
            ? 'border-accent-500 bg-accent-500/5'
            : uploading
            ? 'border-dark-500 bg-dark-800 opacity-60'
            : 'border-dark-600 bg-dark-800/50 hover:border-dark-500 hover:bg-dark-800'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          <div className={`w-14 h-14 rounded-full flex items-center justify-center ${
            isDragActive ? 'bg-accent-500/20' : 'bg-dark-700'
          }`}>
            <svg className={`w-7 h-7 ${isDragActive ? 'text-accent-400' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          {isDragActive ? (
            <p className="text-accent-400 font-medium">Drop your files here</p>
          ) : (
            <>
              <p className="text-gray-300 font-medium">
                <span className="text-accent-400">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-gray-500">PDF, PNG, JPG (max 20MB each) — multiple files supported</p>
            </>
          )}
        </div>
      </div>

      {rows.length > 0 && (
        <ul className="flex flex-col gap-1 rounded-xl border border-dark-600 bg-dark-800/50 p-3">
          {rows.map(([name, state]) => (
            <li key={name} className="flex items-center justify-between gap-3 text-sm py-1">
              <span className="truncate text-gray-300" title={name}>{name}</span>
              <span className={`flex items-center gap-2 shrink-0 ${STATUS_CLASS[state.status]}`}>
                {state.status === 'uploading' && (
                  <span className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-accent-500" />
                )}
                <span className="text-xs">
                  {state.error ? `${STATUS_LABEL[state.status]}: ${state.error}` : STATUS_LABEL[state.status]}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
