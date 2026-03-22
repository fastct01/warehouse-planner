'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { Upload, CheckCircle, XCircle, Loader, FileText, AlertTriangle } from 'lucide-react'
import { api, Upload as UploadRecord, BillRaw } from '../lib/api'

interface Props {
  projectId: number
  onBillApproved: () => void  // refresh parent when a bill is approved
}

type UploadState = UploadRecord & { result?: BillRaw }

export default function BillUploader({ projectId, onBillApproved }: Props) {
  const [uploads, setUploads] = useState<UploadState[]>([])
  const [dragging, setDragging] = useState(false)
  const [loadingIds, setLoadingIds] = useState<Set<number>>(new Set())
  const inputRef = useRef<HTMLInputElement>(null)
  const pollTimers = useRef<Map<number, NodeJS.Timeout>>(new Map())

  // Load existing uploads on mount
  useEffect(() => {
    api.bills.listUploads(projectId).then((list) => {
      setUploads(list)
      list.forEach((u) => {
        if (u.status === 'pending' || u.status === 'processing') startPolling(u.id)
        if (u.status === 'done') fetchResult(u.id)
      })
    }).catch(() => {})

    return () => {
      pollTimers.current.forEach(clearInterval)
    }
  }, [projectId])

  const startPolling = (uploadId: number) => {
    if (pollTimers.current.has(uploadId)) return
    const timer = setInterval(async () => {
      try {
        const updated = await api.bills.getUpload(projectId, uploadId)
        setUploads((prev) => prev.map((u) => u.id === uploadId ? { ...u, ...updated } : u))
        if (updated.status === 'done') {
          clearInterval(timer)
          pollTimers.current.delete(uploadId)
          fetchResult(uploadId)
        } else if (updated.status === 'failed') {
          clearInterval(timer)
          pollTimers.current.delete(uploadId)
        }
      } catch {}
    }, 2500)
    pollTimers.current.set(uploadId, timer)
  }

  const fetchResult = async (uploadId: number) => {
    try {
      const result = await api.bills.getUploadResult(projectId, uploadId)
      setUploads((prev) => prev.map((u) => u.id === uploadId ? { ...u, result } : u))
    } catch {}
  }

  const handleFiles = async (files: FileList | null) => {
    if (!files) return
    for (const file of Array.from(files)) {
      try {
        const upload = await api.bills.uploadFile(projectId, file)
        setUploads((prev) => [upload, ...prev])
        startPolling(upload.id)
      } catch (err: unknown) {
        alert(`Failed to upload ${file.name}: ${err instanceof Error ? err.message : 'Unknown error'}`)
      }
    }
  }

  const handleApprove = async (uploadId: number) => {
    setLoadingIds((s) => new Set(s).add(uploadId))
    try {
      await api.bills.patchUploadResult(projectId, uploadId, { status: 'approved' })
      setUploads((prev) => prev.map((u) =>
        u.id === uploadId ? { ...u, result: u.result ? { ...u.result, status: 'approved' } : u.result } : u
      ))
      onBillApproved()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to approve')
    } finally {
      setLoadingIds((s) => { const next = new Set(s); next.delete(uploadId); return next })
    }
  }

  const handleReject = async (uploadId: number) => {
    await api.bills.patchUploadResult(projectId, uploadId, { status: 'rejected' })
    setUploads((prev) => prev.map((u) =>
      u.id === uploadId ? { ...u, result: u.result ? { ...u.result, status: 'rejected' } : u.result } : u
    ))
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }, [projectId])

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
          ${dragging ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-green-400 hover:bg-gray-50'}`}
      >
        <Upload className="mx-auto mb-2 text-gray-400" size={32} />
        <p className="text-sm font-medium text-gray-600">
          Drag & drop bill PDFs here, or <span className="text-green-600 underline">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">PDF, JPEG, PNG accepted</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Upload list */}
      {uploads.length > 0 && (
        <div className="space-y-3">
          {uploads.map((u) => (
            <UploadCard
              key={u.id}
              upload={u}
              loading={loadingIds.has(u.id)}
              onApprove={() => handleApprove(u.id)}
              onReject={() => handleReject(u.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}


function UploadCard({
  upload,
  loading,
  onApprove,
  onReject,
}: {
  upload: UploadState
  loading: boolean
  onApprove: () => void
  onReject: () => void
}) {
  const { status, filename, result } = upload

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm">
      {/* Header row */}
      <div className="flex items-center gap-3 mb-3">
        <FileText size={18} className="text-gray-400 shrink-0" />
        <span className="text-sm font-medium text-gray-700 truncate flex-1">{filename}</span>
        <StatusBadge status={status} />
      </div>

      {/* Spinner while processing */}
      {(status === 'pending' || status === 'processing') && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Loader size={14} className="animate-spin" />
          Extracting bill data…
        </div>
      )}

      {/* Error */}
      {status === 'failed' && (
        <p className="text-xs text-red-600 flex items-center gap-1">
          <XCircle size={14} /> {upload.error_message || 'Processing failed'}
        </p>
      )}

      {/* Extracted result */}
      {status === 'done' && result && result.status !== 'rejected' && (
        <div className="mt-2 space-y-2">
          <ConfidenceBar confidence={result.confidence} />
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-700">
            <Field label="Period" value={formatPeriod(result.bill_period_start, result.bill_period_end)} />
            <Field label="kWh" value={result.kwh != null ? result.kwh.toLocaleString() : null} />
            <Field label="Total cost" value={result.total_cost != null ? `£${result.total_cost.toFixed(2)}` : null} />
            <Field label="Supplier" value={result.supplier} />
            {result.peak_kw != null && <Field label="Peak kW" value={String(result.peak_kw)} />}
            {result.tariff_name && <Field label="Tariff" value={result.tariff_name} />}
          </div>

          {result.status === 'pending_review' && (
            <div className="flex gap-2 mt-3">
              <button
                onClick={onApprove}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-xs rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? <Loader size={12} className="animate-spin" /> : <CheckCircle size={12} />}
                Approve & save
              </button>
              <button
                onClick={onReject}
                className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 text-gray-600 text-xs rounded-md hover:bg-gray-50"
              >
                <XCircle size={12} /> Reject
              </button>
            </div>
          )}

          {result.status === 'approved' && (
            <p className="text-xs text-green-600 flex items-center gap-1 mt-2">
              <CheckCircle size={12} /> Added to monthly data
            </p>
          )}

          {result.status === 'rejected' && (
            <p className="text-xs text-gray-400 flex items-center gap-1 mt-2">
              <XCircle size={12} /> Rejected
            </p>
          )}
        </div>
      )}
    </div>
  )
}


function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    pending:    { label: 'Queued',     cls: 'bg-gray-100 text-gray-500' },
    processing: { label: 'Processing', cls: 'bg-blue-100 text-blue-600' },
    done:       { label: 'Done',       cls: 'bg-green-100 text-green-700' },
    failed:     { label: 'Failed',     cls: 'bg-red-100 text-red-600' },
  }
  const { label, cls } = map[status] || map.pending
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{label}</span>
}


function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const colour = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      {pct < 70 && <AlertTriangle size={12} className="text-yellow-500" />}
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${colour}`} style={{ width: `${pct}%` }} />
      </div>
      <span>{pct}% confidence</span>
    </div>
  )
}


function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <span className="text-gray-400">{label}: </span>
      <span className={value ? 'font-medium' : 'text-gray-300'}>{value ?? '—'}</span>
    </div>
  )
}


function formatPeriod(start: string | null, end: string | null) {
  if (!start && !end) return null
  const fmt = (d: string) => new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  if (start && end) return `${fmt(start)} – ${fmt(end)}`
  return end ? fmt(end) : start ? fmt(start) : null
}
