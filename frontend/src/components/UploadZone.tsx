import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { documentsApi } from '../api/client'
import toast from 'react-hot-toast'

interface UploadZoneProps {
  onUploadComplete: () => void
}

export default function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    try {
      await documentsApi.upload(file)
      toast.success(`${file.name} uploaded successfully`)
      onUploadComplete()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      toast.error(msg)
    } finally {
      setUploading(false)
    }
  }, [onUploadComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    maxSize: 20 * 1024 * 1024,
    maxFiles: 1,
    disabled: uploading,
  })

  return (
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
        {uploading ? (
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-accent-500" />
            <p className="text-sm text-gray-400">Uploading...</p>
          </div>
        ) : isDragActive ? (
          <p className="text-accent-400 font-medium">Drop your file here</p>
        ) : (
          <>
            <p className="text-gray-300 font-medium">
              <span className="text-accent-400">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-gray-500">PDF, PNG, JPG (max 20MB)</p>
          </>
        )}
      </div>
    </div>
  )
}
