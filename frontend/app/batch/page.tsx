'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Upload,
  FileText,
  X,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  AlertCircle,
  Download,
  Trash2,
  StopCircle,
  Layers,
  ChevronDown,
  ChevronRight,
  Search,
} from 'lucide-react';
import {
  fetchDefinitions,
  createBatch,
  fetchBatches,
  cancelBatch,
  deleteBatch,
  exportBatchCSV,
  exportBatchJSON,
  type AgentDefinition,
  type Batch,
} from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  queued: 'text-blue-400',
  running: 'text-yellow-400',
  paused: 'text-yellow-400',
  completed: 'text-green-400',
  failed: 'text-red-400',
  cancelled: 'text-gray-400',
  max_iterations_reached: 'text-orange-400',
};

const STATUS_ICONS: Record<string, React.ElementType> = {
  queued: Clock,
  running: Loader2,
  paused: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
  cancelled: StopCircle,
  max_iterations_reached: AlertCircle,
};

export default function BatchPage() {
  const [definitions, setDefinitions] = useState<AgentDefinition[]>([]);
  const [selectedDefId, setSelectedDefId] = useState<string>('auto');
  const [files, setFiles] = useState<File[]>([]);
  const [batchName, setBatchName] = useState('');
  const [creating, setCreating] = useState(false);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expandedBatch, setExpandedBatch] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchDefinitions().then(setDefinitions).catch((err) => {
      setError(`Failed to load agent definitions: ${err instanceof Error ? err.message : 'unknown error'}`);
    });
  }, []);

  const loadBatches = useCallback(async () => {
    try {
      const data = await fetchBatches();
      setBatches(data);
    } catch (err) {
      setError(`Failed to load batches: ${err instanceof Error ? err.message : 'unknown error'}`);
    }
  }, []);

  useEffect(() => {
    loadBatches();
  }, [loadBatches]);

  // Poll while any batch is running or queued
  useEffect(() => {
    const hasActive = batches.some(
      (b) => b.status === 'running' || b.status === 'queued' || b.running_runs > 0 || b.queued_runs > 0,
    );
    if (hasActive && !pollRef.current) {
      pollRef.current = setInterval(loadBatches, 3000);
    } else if (!hasActive && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [batches, loadBatches]);

  const handleFileSelect = (selected: FileList | null) => {
    if (!selected) return;
    const valid = Array.from(selected).filter((f) => {
      const ext = f.name.split('.').pop()?.toLowerCase();
      return ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp'].includes(ext || '');
    });
    setFiles((prev) => [...prev, ...valid]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleCreateBatch = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const batch = await createBatch(selectedDefId, files, batchName || undefined);
      setSuccess(`Batch "${batch.name}" created with ${batch.total_runs} runs`);
      setFiles([]);
      setBatchName('');
      await loadBatches();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create batch');
    } finally {
      setCreating(false);
    }
  };

  const handleCancelBatch = async (batchId: string) => {
    try {
      await cancelBatch(batchId);
      await loadBatches();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel batch');
    }
  };

  const handleDeleteBatch = async (batchId: string) => {
    try {
      await deleteBatch(batchId);
      await loadBatches();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete batch');
    }
  };

  const handleExportCSV = async (batchId: string) => {
    try {
      const blob = await exportBatchCSV(batchId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${batchId}_export.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export CSV');
    }
  };

  const handleExportJSON = async (batchId: string) => {
    try {
      const blob = await exportBatchJSON(batchId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${batchId}_export.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export JSON');
    }
  };

  const filteredBatches = batches.filter((b) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      b.name.toLowerCase().includes(q) ||
      b.id.toLowerCase().includes(q) ||
      b.definition_id.toLowerCase().includes(q)
    );
  });

  const totalProgress = (b: Batch) => {
    if (b.total_runs === 0) return 0;
    return Math.round(((b.completed_runs + b.failed_runs + b.cancelled_runs) / b.total_runs) * 100);
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--primary-text)]">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <Layers className="w-6 h-6 text-[var(--brand-accent)]" />
          <div>
            <h1 className="text-xl font-bold">Batch Processing Queue</h1>
            <p className="text-xs text-muted">Upload and process hundreds of documents in a single batch</p>
          </div>
        </div>

        {/* Error / Success */}
        {error && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto"><X className="w-4 h-4" /></button>
          </div>
        )}
        {success && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{success}</span>
            <button onClick={() => setSuccess(null)} className="ml-auto"><X className="w-4 h-4" /></button>
          </div>
        )}

        {/* Upload Section */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-5 space-y-4">
          <h2 className="text-sm font-semibold">Create New Batch</h2>

          {/* Definition Selector + Batch Name */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-[11px] text-muted font-medium uppercase tracking-wide mb-1 block">Agent Definition</label>
              <select
                value={selectedDefId}
                onChange={(e) => setSelectedDefId(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-[var(--primary-text)] focus:outline-none focus:ring-1 focus:ring-[var(--brand-primary)]"
              >
                <option value="auto">Auto-detect (classify each document)</option>
                {definitions.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] text-muted font-medium uppercase tracking-wide mb-1 block">Batch Name (optional)</label>
              <input
                type="text"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                placeholder="e.g. Q1 Invoices Batch"
                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-[var(--primary-text)] focus:outline-none focus:ring-1 focus:ring-[var(--brand-primary)]"
              />
            </div>
          </div>

          {/* Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-[var(--brand-primary)] bg-[var(--brand-primary-muted)]/20'
                : 'border-[var(--border)] hover:border-[var(--brand-primary)]/50'
            }`}
          >
            <Upload className="w-8 h-8 mx-auto mb-2 text-muted" />
            <p className="text-sm text-muted">
              {dragOver ? 'Release to upload files' : 'Drag & drop files here, or click to browse'}
            </p>
            <p className="text-[10px] text-muted mt-1">PDF, PNG, JPG, TIFF, BMP — up to 20MB each</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp"
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
            />
          </div>

          {/* Selected Files */}
          {files.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">{files.length} file(s) selected</span>
                <button
                  onClick={() => setFiles([])}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  Clear all
                </button>
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {files.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-base)] border border-[var(--border)] text-sm"
                  >
                    <FileText className="w-4 h-4 text-muted shrink-0" />
                    <span className="truncate flex-1">{file.name}</span>
                    <span className="text-[10px] text-muted">{(file.size / 1024).toFixed(0)} KB</span>
                    <button onClick={() => removeFile(idx)} className="text-red-400 hover:text-red-300">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Create Button */}
          <button
            onClick={handleCreateBatch}
            disabled={creating || files.length === 0}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-primary)]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {creating ? 'Creating Batch...' : `Start Batch (${files.length} files)`}
          </button>
        </div>

        {/* Existing Batches */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Batch History</h2>
            <div className="relative w-48">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search batches..."
                className="w-full pl-7 pr-3 py-1.5 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-[var(--primary-text)] focus:outline-none focus:ring-1 focus:ring-[var(--brand-primary)]"
              />
            </div>
          </div>

          {filteredBatches.length === 0 ? (
            <p className="text-xs text-muted text-center py-8">No batches yet. Create one above to get started.</p>
          ) : (
            <div className="space-y-2">
              {filteredBatches.map((batch) => {
                const isExpanded = expandedBatch === batch.id;
                const progress = totalProgress(batch);
                const StatusIcon = STATUS_ICONS[batch.status] || Clock;

                return (
                  <div
                    key={batch.id}
                    className="rounded-lg border border-[var(--border)] bg-[var(--bg-base)] overflow-hidden"
                  >
                    {/* Batch Header */}
                    <div
                      className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-[var(--bg-elevated)] transition-colors"
                      onClick={() => setExpandedBatch(isExpanded ? null : batch.id)}
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-muted shrink-0" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted shrink-0" />
                      )}
                      <StatusIcon
                        className={`w-4 h-4 shrink-0 ${STATUS_COLORS[batch.status] || 'text-muted'} ${
                          batch.status === 'running' ? 'animate-spin' : ''
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">{batch.name}</span>
                          <span className={`text-[10px] uppercase ${STATUS_COLORS[batch.status] || 'text-muted'}`}>
                            {batch.status}
                          </span>
                        </div>
                        <div className="text-[10px] text-muted">
                          {batch.id} · {batch.definition_id} · {new Date(batch.created_at).toLocaleString()}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="hidden sm:flex items-center gap-2 w-40">
                        <div className="flex-1 h-1.5 rounded-full bg-[var(--border)] overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[var(--brand-primary)] transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-muted">{progress}%</span>
                      </div>

                      {/* Stats */}
                      <div className="hidden md:flex items-center gap-3 text-[10px]">
                        <span className="text-green-400">{batch.completed_runs} done</span>
                        <span className="text-yellow-400">{batch.running_runs} running</span>
                        <span className="text-blue-400">{batch.queued_runs} queued</span>
                        {batch.failed_runs > 0 && <span className="text-red-400">{batch.failed_runs} failed</span>}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        {(batch.status === 'running' || batch.status === 'queued') && (
                          <button
                            onClick={() => handleCancelBatch(batch.id)}
                            title="Cancel batch"
                            className="p-1.5 rounded text-red-400 hover:bg-red-500/10"
                          >
                            <StopCircle className="w-4 h-4" />
                          </button>
                        )}
                        {batch.completed_runs > 0 && (
                          <>
                            <button
                              onClick={() => handleExportCSV(batch.id)}
                              title="Export CSV"
                              className="p-1.5 rounded text-muted hover:bg-[var(--border)]"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleExportJSON(batch.id)}
                              title="Export JSON"
                              className="p-1.5 rounded text-muted hover:bg-[var(--border)]"
                            >
                              <FileText className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => handleDeleteBatch(batch.id)}
                          title="Delete batch"
                          className="p-1.5 rounded text-muted hover:bg-red-500/10 hover:text-red-400"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Expanded Run List */}
                    {isExpanded && (
                      <div className="border-t border-[var(--border)] p-3 space-y-1 max-h-64 overflow-y-auto">
                        {batch.runs.map((run) => {
                          const RunIcon = STATUS_ICONS[run.status] || Clock;
                          return (
                            <div
                              key={run.run_id}
                              className="flex items-center gap-2 px-2 py-1.5 text-xs rounded hover:bg-[var(--bg-elevated)]"
                            >
                              <RunIcon
                                className={`w-3.5 h-3.5 shrink-0 ${STATUS_COLORS[run.status] || 'text-muted'} ${
                                  run.status === 'running' ? 'animate-spin' : ''
                                }`}
                              />
                              <span className="truncate flex-1">{run.original_filename}</span>
                              <span className="text-[10px] text-muted">{run.run_id}</span>
                              <span className={`text-[10px] uppercase ${STATUS_COLORS[run.status] || 'text-muted'}`}>
                                {run.status}
                              </span>
                            </div>
                          );
                        })}
                        {batch.failed_uploads && batch.failed_uploads.length > 0 && (
                          <div className="pt-2 border-t border-[var(--border)]">
                            <p className="text-[10px] text-red-400 font-medium mb-1">Failed Uploads:</p>
                            {batch.failed_uploads.map((f, i) => (
                              <div key={i} className="flex items-center gap-2 px-2 py-1 text-xs text-red-400">
                                <XCircle className="w-3.5 h-3.5 shrink-0" />
                                <span className="truncate flex-1">{f.filename}</span>
                                <span className="text-[10px]">{f.error}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
