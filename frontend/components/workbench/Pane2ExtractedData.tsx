'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  AlertCircle, 
  MapPin, 
  Download, 
  FileText, 
  Code, 
  Edit2, 
  Check, 
  Search, 
  Layers, 
  Sparkles,
  RotateCcw,
  Copy,
  ClipboardList,
  ChevronDown
} from 'lucide-react';
import { useActiveHighlight } from '@/context/ActiveHighlightContext';
import { useWorkbench } from '@/context/WorkbenchContext';
import { ExtractedField, exportRunJSON, exportRunCSV, fetchRun } from '@/lib/api';
import { connectToRunStream } from '@/lib/sse';
import { AdeButton } from '@/components/ui/AdeButton';
import { AdeBadge } from '@/components/ui/AdeBadge';

import { FieldCardSkeleton } from '@/components/ui/SkeletonLoader';
import { ErrorState } from '@/components/ui/ErrorState';
import { GraphVisualizationView } from './GraphVisualizationView';

export const Pane2ExtractedData: React.FC = () => {
  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [runMeta, setRunMeta] = useState<{
    status?: string;
    error?: string;
    definitionId?: string;
    taskType?: string;
    serializedOutput?: any;
  } | null>(null);
  const [viewMode, setViewMode] = useState<'cards' | 'json' | 'graph'>('cards');
  const [editingFieldId, setEditingFieldId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [jsonText, setJsonText] = useState<string>('[]');
  const [fetchError, setFetchError] = useState<{ message: string; status?: number } | null>(null);

  const { activeFieldId, setActiveBBox, setActivePage, setActiveFieldId, setHoveredFieldId, setHeatmapFields, setTotalPages } =
    useActiveHighlight();
  const { phase, runStatus, runId } = useWorkbench();

  const [showExportMenu, setShowExportMenu] = useState(false);
  const [copyNotification, setCopyNotification] = useState<string | null>(null);

  const fieldRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    setFetchError(null);
    if (phase === 'extraction' && runId) {
      // Fetch initial run fields from API
      fetchRun(runId)
        .then((run) => {
          setRunMeta({
            status: run.status,
            error: run.error,
            definitionId: run.definition_id,
            taskType: run.task_type,
            serializedOutput: run.serialized_output,
          });
          if (run && run.fields) {
            setFields(run.fields);
            setJsonText(JSON.stringify(run.fields, null, 2));
            // BLK-250: Set total pages from max field page (fallback when document metadata unavailable)
            const maxPage = run.fields.reduce((mx, f) => Math.max(mx, f.page || 1), 1);
            setTotalPages(maxPage);
          }
        })
        .catch((err) => {
          setFetchError({
            message: err instanceof Error ? err.message : 'Failed to fetch extraction run fields',
            status: (err as any)?.status || 0,
          });
        });

      // Subscribe to real-time SSE field_update events
      const cleanup = connectToRunStream(runId, {
        onFieldUpdate: (evt) => {
          if (evt.field) {
            setFields((prev) => {
              const existingIdx = prev.findIndex((f) => f.id === evt.field.id || f.name === evt.field.name);
              let updated: ExtractedField[];
              if (existingIdx >= 0) {
                updated = [...prev];
                updated[existingIdx] = evt.field;
              } else {
                updated = [...prev, evt.field];
              }
              setJsonText(JSON.stringify(updated, null, 2));
              return updated;
            });
          }
        },
      });

      return () => cleanup();
    } else {
      setFields([]);
      setRunMeta(null);
      setJsonText('[]');
    }
  }, [phase, runId]);

  // BLK-115: Push fields to heatmap context whenever fields change
  useEffect(() => {
    setHeatmapFields(
      fields
        .filter((f) => f.bbox)
        .map((f) => ({
          id: f.id,
          name: f.name,
          confidence: f.confidence,
          page: f.page || 1,
          bbox: f.bbox!,
        }))
    );
  }, [fields, setHeatmapFields]);

  const handleFieldClick = (field: ExtractedField) => {
    setActiveFieldId(field.id);
    if (field.bbox) {
      setActiveBBox(field.bbox, field.page || 1);
      setActivePage(field.page || 1);
    } else {
      setActiveBBox(null);
    }
  };

  const handleStartEdit = (field: ExtractedField, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingFieldId(field.id);
    setEditValue(field.value !== null ? String(field.value) : '');
  };

  const [exportNotice, setExportNotice] = useState<string | null>(null);

  const handleSaveEdit = (fieldId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    // BLK-253: Do not fabricate 'verified' status or confidence=1.0 on manual edit.
    // Preserve original status and confidence; only update the value.
    setFields((prev) =>
      prev.map((f) =>
        f.id === fieldId ? { ...f, value: editValue } : f
      )
    );
    setEditingFieldId(null);
  };

  const handleExportJSON = async () => {
    setShowExportMenu(false);
    setExportNotice(null);
    // Try real API first, fall back to client-side export
    if (runId) {
      try {
        const blob = await exportRunJSON(runId);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `extraction_${runId}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        return;
      } catch (err) {
        setExportNotice(`Backend API export failed (${err instanceof Error ? err.message : 'error'}); downloaded client-side JSON export.`);
      }
    }
    // Client-side fallback (partial/failed runs still exportable)
    try {
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(fields, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', 'extracted_data.json');
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (fallbackErr) {
      setExportNotice(`Export failed: ${fallbackErr instanceof Error ? fallbackErr.message : 'unknown error'}`);
    }
  };

  const handleExportCSV = async () => {
    setShowExportMenu(false);
    setExportNotice(null);
    // Try real API first, fall back to client-side export
    if (runId) {
      try {
        const blob = await exportRunCSV(runId);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `extraction_${runId}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        return;
      } catch (err) {
        setExportNotice(`Backend API export failed (${err instanceof Error ? err.message : 'error'}); downloaded client-side CSV export.`);
      }
    }
    // Client-side fallback (partial/failed runs still exportable)
    try {
      const headers = ['field_name', 'value', 'confidence', 'status', 'page'];
      const rows = fields.map((f) => [
        f.name,
        `"${f.value !== null ? String(f.value).replace(/"/g, '""') : ''}"`,
        f.confidence,
        f.status,
        f.page || 1,
      ]);
      const csvContent = [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
      const dataStr = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent);
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', 'extracted_data.csv');
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (fallbackErr) {
      setExportNotice(`Export failed: ${fallbackErr instanceof Error ? fallbackErr.message : 'unknown error'}`);
    }
  };


  // BLK-133: Copy single field value to clipboard
  const handleCopyField = (field: ExtractedField, e: React.MouseEvent) => {
    e.stopPropagation();
    const text = field.value !== null ? String(field.value) : '';
    navigator.clipboard.writeText(text).then(() => {
      setCopyNotification(field.name);
      setTimeout(() => setCopyNotification(null), 1500);
    }).catch(() => {
      setExportNotice('Failed to copy to clipboard.');
    });
  };

  // BLK-133: Copy all field values as tab-separated text (for spreadsheet paste)
  const handleCopyAllTSV = () => {
    setShowExportMenu(false);
    const headers = 'field_name\tvalue\tconfidence\tstatus';
    const rows = fields.map((f) =>
      `${f.name}\t${f.value !== null ? String(f.value) : ''}\t${Math.round(f.confidence * 100)}%\t${f.status}`
    );
    const tsvContent = [headers, ...rows].join('\n');
    navigator.clipboard.writeText(tsvContent).then(() => {
      setCopyNotification('all fields');
      setTimeout(() => setCopyNotification(null), 1500);
    }).catch(() => {
      setExportNotice('Failed to copy to clipboard.');
    });
  };

  const verifiedCount = fields.filter((f) => f.status === 'verified').length;
  const isGraphTask = runMeta?.taskType === 'graph_extraction';

  return (
    <div className="h-full flex flex-col border-r border-[var(--pane-border)] bg-[var(--pane-bg)] overflow-hidden">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 bg-[var(--pane-bg)] border-b border-[var(--pane-border)] shadow-2xs">
        {exportNotice && (
          <div className="px-4 py-2 bg-[var(--status-warning-subtle)] border-b border-[var(--status-warning)] text-[11px] text-[var(--status-warning)] flex items-center justify-between font-medium">
            <span>⚠️ {exportNotice}</span>
            <button onClick={() => setExportNotice(null)} className="font-bold underline ml-2">Dismiss</button>
          </div>
        )}
        <div className="px-4 py-2.5 flex items-center justify-between bg-black/5 dark:bg-white/5">

          <div className="flex items-center gap-2">
            <h2 className="font-bold text-xs text-[var(--primary-text)]">Extracted Data</h2>
            <AdeBadge variant="verified">{verifiedCount}/{fields.length || 6} Verified</AdeBadge>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center bg-black/10 dark:bg-white/10 p-0.5 rounded text-[11px] font-medium">
              <button
                onClick={() => setViewMode('cards')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  viewMode === 'cards' ? 'bg-[var(--brand-primary)] text-white font-semibold' : 'text-muted'
                }`}
              >
                Cards View
              </button>
              {isGraphTask && (
                <button
                  onClick={() => setViewMode('graph')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    viewMode === 'graph' ? 'bg-[var(--brand-primary)] text-white font-semibold' : 'text-muted'
                  }`}
                >
                  P&amp;ID Graph View
                </button>
              )}
              <button
                onClick={() => setViewMode('json')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  viewMode === 'json' ? 'bg-[var(--brand-primary)] text-white font-semibold' : 'text-muted'
                }`}
              >
                JSON View
              </button>
            </div>

            {/* BLK-133: Export Dropdown */}
            <div className="relative">
              <AdeButton variant="secondary" size="sm" onClick={() => setShowExportMenu(!showExportMenu)}>
                <Download className="w-3.5 h-3.5" />
                <span>Export</span>
                <ChevronDown className="w-3 h-3" />
              </AdeButton>

              {showExportMenu && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-[var(--pane-bg)] border border-[var(--pane-border)] rounded-lg shadow-xl py-1 z-30 text-xs">
                  <button
                    onClick={handleExportJSON}
                    className="w-full text-left px-3 py-2 hover:bg-[var(--brand-primary)] hover:text-white flex items-center gap-2"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download JSON
                  </button>
                  <button
                    onClick={handleExportCSV}
                    className="w-full text-left px-3 py-2 hover:bg-[var(--brand-primary)] hover:text-white flex items-center gap-2"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    Download CSV
                  </button>
                  <div className="border-t border-[var(--pane-border)] my-1" />
                  <button
                    onClick={handleCopyAllTSV}
                    className="w-full text-left px-3 py-2 hover:bg-[var(--brand-primary)] hover:text-white flex items-center gap-2"
                  >
                    <ClipboardList className="w-3.5 h-3.5" />
                    Copy All (Spreadsheet)
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* BLK-133: Copy notification toast */}
      {copyNotification && (
        <div className="px-4 py-1.5 bg-[var(--status-success-subtle)] border-b border-[var(--status-success)] text-xs text-[var(--status-success)] font-semibold flex items-center gap-1.5 animate-fadeIn">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Copied {copyNotification} to clipboard</span>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 p-4 overflow-y-auto">
        {fetchError ? (
          <ErrorState
            message={fetchError.message}
            status={fetchError.status}
            onRetry={() => {
              setFetchError(null);
              if (runId) {
                fetchRun(runId)
                  .then((r) => {
                    setRunMeta({ status: r.status, error: r.error, definitionId: r.definition_id });
                    if (r.fields) setFields(r.fields);
                  })
                  .catch((err) => {
                    setFetchError({
                      message: err instanceof Error ? err.message : 'Failed to fetch extraction run fields',
                      status: (err as any)?.status || 0,
                    });
                  });
              }
            }}
          />
        ) : runMeta?.status === 'failed' ? (
          <ErrorState
            message={runMeta.error || 'This extraction run failed before producing output fields.'}
            status={500}
            onRetry={() => {
              setFetchError(null);
              if (runId) {
                fetchRun(runId)
                  .then((r) => {
                    setRunMeta({ status: r.status, error: r.error, definitionId: r.definition_id });
                    if (r.fields) {
                      setFields(r.fields);
                      setJsonText(JSON.stringify(r.fields, null, 2));
                    }
                  })
                  .catch((err) => {
                    setFetchError({
                      message: err instanceof Error ? err.message : 'Failed to fetch extraction run fields',
                      status: (err as any)?.status || 0,
                    });
                  });
              }
            }}
          />
        ) : fields.length === 0 ? (
          isGraphTask ? (
            <div className="h-full flex flex-col gap-3">
              <div className="px-3 py-2 rounded-lg border border-[var(--pane-border)] bg-black/5 dark:bg-white/5 text-[11px] text-muted">
                This run uses graph extraction. View outputs in P&amp;ID Graph View, DEXPI XML, Smart P&amp;ID JSON, or GraphML.
              </div>
              <div className="flex-1 min-h-0">
                <GraphVisualizationView
                  nodes={runMeta?.serializedOutput?.nodes}
                  edges={runMeta?.serializedOutput?.edges}
                  topologyRules={runMeta?.serializedOutput?.topology_rules}
                  serializedOutput={runMeta?.serializedOutput}
                  isLoading={runStatus === 'running'}
                />
              </div>
            </div>
          ) :
          runStatus === 'running' ? (
            <div className="space-y-3">
              <FieldCardSkeleton />
              <FieldCardSkeleton />
              <FieldCardSkeleton />
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-2 text-muted p-6">
                <FileText className="w-10 h-10 mx-auto opacity-30 text-[var(--brand-primary)]" />
                <p className="text-xs font-semibold text-[var(--primary-text)]">No Extracted Data Yet</p>
                <p className="text-[11px] max-w-xs">Start an extraction run in Pane 1 to populate structured fields.</p>
              </div>
            </div>
          )
        ) : viewMode === 'graph' ? (
          <GraphVisualizationView
            nodes={runMeta?.serializedOutput?.nodes}
            edges={runMeta?.serializedOutput?.edges}
            topologyRules={runMeta?.serializedOutput?.topology_rules}
            serializedOutput={runMeta?.serializedOutput}
            isLoading={runStatus === 'running'}
          />
        ) : viewMode === 'cards' ? (
          <div className="space-y-3">
            {fields.map((field) => {
              const isSelected = activeFieldId === field.id;
              const isEditing = editingFieldId === field.id;

              let badgeVariant: 'verified' | 'medium' | 'failed' = 'verified';
              if (field.confidence < 0.6 || field.status === 'failed') badgeVariant = 'failed';
              else if (field.confidence < 0.8 || field.status === 'low_confidence') badgeVariant = 'medium';

              return (
                <div
                  key={field.id}
                  ref={(el) => {
                    fieldRefs.current[field.id] = el;
                  }}
                  onClick={() => handleFieldClick(field)}
                  onMouseEnter={() => setHoveredFieldId(field.id)}
                  onMouseLeave={() => setHoveredFieldId(null)}
                  className={`p-3.5 rounded-lg border transition-all cursor-pointer shadow-2xs space-y-2 ${
                    isSelected
                      ? 'border-[var(--brand-accent)] ring-2 ring-[var(--brand-accent)]/40 bg-[var(--brand-primary-subtle)]'
                      : 'border-[var(--card-border)] bg-[var(--card-bg)] hover:border-[var(--brand-primary)]/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-muted uppercase tracking-wider">
                      {field.name}
                    </span>

                    <div className="flex items-center gap-2">
                      <AdeBadge variant={badgeVariant}>
                        {field.status === 'failed' ? 'Failed' : `${Math.round(field.confidence * 100)}% Confidence`}
                      </AdeBadge>

                      <button
                        onClick={(e) => handleCopyField(field, e)}
                        className="p-1 text-muted hover:text-[var(--status-success)] rounded"
                        title="Copy Value"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={(e) => handleStartEdit(field, e)}
                        className="p-1 text-muted hover:text-[var(--brand-primary)] rounded"
                        title="Edit Field Value"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {isEditing ? (
                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="flex-1 p-1.5 rounded border border-[var(--brand-primary)] bg-[var(--pane-bg)] text-xs focus:outline-none"
                      />
                      <button
                        onClick={(e) => handleSaveEdit(field.id, e)}
                        className="p-1.5 bg-[var(--status-success)] text-white rounded hover:bg-green-700"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded bg-black/5 dark:bg-black/30 border border-black/5 dark:border-white/5 font-mono text-xs font-medium text-[var(--primary-text)]">
                      {field.value !== null ? String(field.value) : <span className="text-red-500 italic">Not Found / Null</span>}
                    </div>
                  )}

                  {field.bbox && (
                    <div className="pt-1 flex justify-end">
                      <button
                        onClick={() => handleFieldClick(field)}
                        className="flex items-center gap-1 text-[11px] font-medium text-[var(--brand-primary)] hover:underline"
                      >
                        <MapPin className="w-3 h-3 text-[var(--brand-accent)]" />
                        <span>Show source (Page {field.page || 1})</span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="h-full flex flex-col space-y-2">
            <div className="text-[11px] text-muted font-mono italic">JSON View (Read-Only)</div>
            <textarea
              value={jsonText}
              readOnly
              className="flex-1 w-full p-4 font-mono text-xs bg-black/10 dark:bg-black/40 border border-[var(--pane-border)] rounded-lg focus:outline-none cursor-default"
            />
          </div>
        )}
      </div>
    </div>
  );
};
