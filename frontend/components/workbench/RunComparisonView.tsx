'use client';

import React, { useState, useEffect } from 'react';
import { GitCompare, ArrowRight, TrendingUp, TrendingDown, Minus, CheckCircle2, AlertTriangle, FileText, X, RefreshCw } from 'lucide-react';
import { ExtractionRun, ExtractedField, fetchRecentRuns, fetchRun } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface RunComparisonViewProps {
  onClose?: () => void;
}

export const RunComparisonView: React.FC<RunComparisonViewProps> = ({ onClose }) => {
  const [runs, setRuns] = useState<ExtractionRun[]>([]);
  const [runAId, setRunAId] = useState<string>('');
  const [runBId, setRunBId] = useState<string>('');

  const [runA, setRunA] = useState<ExtractionRun | null>(null);
  const [runB, setRunB] = useState<ExtractionRun | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRecentRuns(10)
      .then((res) => {
        const items = Array.isArray(res) ? res : (res as { items?: ExtractionRun[] }).items || [];
        setRuns(items);
        if (items.length >= 2) {
          setRunAId(items[0].id);
          setRunBId(items[1].id);
        } else if (items.length === 1) {
          setRunAId(items[0].id);
        }
      })
      .catch((err) => {
        setRuns([]);
        setError(err instanceof Error ? err.message : 'Failed to fetch extraction runs for comparison');
      });
  }, []);

  useEffect(() => {
    if (runAId) {
      fetchRun(runAId)
        .then(setRunA)
        .catch((err) => {
          setRunA(null);
          setError(`Failed to fetch baseline run (${runAId}): ${err instanceof Error ? err.message : 'Unknown error'}`);
        });
    }
  }, [runAId]);

  useEffect(() => {
    if (runBId) {
      fetchRun(runBId)
        .then(setRunB)
        .catch((err) => {
          setRunB(null);
          setError(`Failed to fetch comparison run (${runBId}): ${err instanceof Error ? err.message : 'Unknown error'}`);
        });
    }
  }, [runBId]);

  // Compute field comparison map
  const fieldsA = runA?.fields || [];
  const fieldsB = runB?.fields || [];

  const allFieldNames = Array.from(
    new Set([...fieldsA.map((f) => f.name), ...fieldsB.map((f) => f.name)])
  );

  const diffRows = allFieldNames.map((name) => {
    const fA = fieldsA.find((f) => f.name === name);
    const fB = fieldsB.find((f) => f.name === name);

    const confA = fA ? fA.confidence : 0;
    const confB = fB ? fB.confidence : 0;
    const delta = confB - confA;

    let status: 'improved' | 'regressed' | 'unchanged' | 'new' | 'removed' = 'unchanged';
    if (!fA && fB) status = 'new';
    else if (fA && !fB) status = 'removed';
    else if (delta > 0.05) status = 'improved';
    else if (delta < -0.05) status = 'regressed';

    return { name, fA, fB, confA, confB, delta, status };
  });

  const improvedCount = diffRows.filter((r) => r.status === 'improved' || r.status === 'new').length;
  const regressedCount = diffRows.filter((r) => r.status === 'regressed' || r.status === 'removed').length;
  const avgDelta =
    diffRows.length > 0
      ? diffRows.reduce((acc, r) => acc + r.delta, 0) / diffRows.length
      : 0;

  return (
    <div className="h-full flex flex-col bg-[var(--pane-bg)] overflow-hidden p-6 space-y-4">
      {/* Top Header & Selectors */}
      <div className="flex items-center justify-between border-b border-[var(--pane-border)] pb-4">
        <div className="flex items-center gap-2">
          <GitCompare className="w-5 h-5 text-[var(--brand-primary)]" />
          <div>
            <h1 className="text-lg font-bold text-[var(--primary-text)]">Side-by-Side Run Comparison</h1>
            <p className="text-xs text-muted">Field-by-field confidence delta and value diff analysis</p>
          </div>
        </div>

        {onClose && (
          <Button variant="tertiary" size="sm" onClick={onClose}>
            <X className="w-4 h-4" /> Close Comparison
          </Button>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-[var(--status-error-subtle)] border border-[var(--status-error)]/40 text-xs text-[var(--status-error)] font-medium">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            className="font-bold underline ml-2 shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Selectors Panel */}
      <div className="grid grid-cols-2 gap-4 p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] text-xs">
        <div>
          <label className="block font-semibold text-muted mb-1">Baseline Run (Run A)</label>
          <select
            value={runAId}
            onChange={(e) => setRunAId(e.target.value)}
            className="w-full p-2 rounded-lg border border-[var(--pane-border)] bg-[var(--pane-bg)] font-mono text-xs focus:outline-none focus:border-[var(--brand-primary)]"
          >
            <option value="">Select Baseline Run...</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id} ({r.document_url || '—'})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block font-semibold text-muted mb-1">Comparison Run (Run B)</label>
          <select
            value={runBId}
            onChange={(e) => setRunBId(e.target.value)}
            className="w-full p-2 rounded-lg border border-[var(--pane-border)] bg-[var(--pane-bg)] font-mono text-xs focus:outline-none focus:border-[var(--brand-primary)]"
          >
            <option value="">Select Comparison Run...</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id} ({r.document_url || '—'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary KPI Stats Panel */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase">Fields Compared</span>
          <div className="text-lg font-bold text-[var(--primary-text)] font-mono">{diffRows.length}</div>
        </div>

        <div className="p-3.5 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase">Avg Confidence Delta</span>
          <div className={`text-lg font-bold font-mono ${avgDelta >= 0 ? 'text-[var(--status-success)]' : 'text-[var(--status-error)]'}`}>
            {avgDelta >= 0 ? `+${(avgDelta * 100).toFixed(1)}%` : `${(avgDelta * 100).toFixed(1)}%`}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase">Improvements / New</span>
          <div className="text-lg font-bold text-[var(--status-success)] font-mono flex items-center gap-1">
            <TrendingUp className="w-4 h-4" /> {improvedCount}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase">Regressions / Lost</span>
          <div className="text-lg font-bold text-[var(--status-error)] font-mono flex items-center gap-1">
            <TrendingDown className="w-4 h-4" /> {regressedCount}
          </div>
        </div>
      </div>

      {/* Field-by-Field Diff Comparison Table */}
      <div className="flex-1 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] overflow-hidden flex flex-col">
        <div className="px-4 py-3 bg-black/5 dark:bg-white/5 border-b border-[var(--pane-border)] grid grid-cols-12 text-xs font-bold text-muted uppercase tracking-wider">
          <div className="col-span-3">Field Name</div>
          <div className="col-span-4">Run A Value (Baseline)</div>
          <div className="col-span-4">Run B Value (Comparison)</div>
          <div className="col-span-1 text-right">Delta</div>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-[var(--pane-border)] text-xs">
          {diffRows.map((row) => (
            <div
              key={row.name}
              className={`grid grid-cols-12 items-center px-4 py-2.5 transition-colors ${
                row.status === 'improved'
                  ? 'bg-green-500/10 dark:bg-green-950/20'
                  : row.status === 'regressed'
                  ? 'bg-red-500/10 dark:bg-red-950/20'
                  : row.status === 'new'
                  ? 'bg-blue-500/10 dark:bg-blue-950/20'
                  : 'hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              <div className="col-span-3 font-mono font-semibold text-[var(--primary-text)]">
                {row.name}
              </div>

              <div className="col-span-4 flex items-center gap-2 font-mono">
                <span className="truncate">{row.fA?.value !== undefined ? String(row.fA.value) : <em className="text-muted">null</em>}</span>
                {row.fA && (
                  <Badge variant={row.fA.confidence > 0.8 ? 'verified' : 'medium'}>
                    {Math.round(row.fA.confidence * 100)}%
                  </Badge>
                )}
              </div>

              <div className="col-span-4 flex items-center gap-2 font-mono">
                <span className="truncate">{row.fB?.value !== undefined ? String(row.fB.value) : <em className="text-muted">null</em>}</span>
                {row.fB && (
                  <Badge variant={row.fB.confidence > 0.8 ? 'verified' : 'medium'}>
                    {Math.round(row.fB.confidence * 100)}%
                  </Badge>
                )}
              </div>

              <div className="col-span-1 text-right font-mono font-bold">
                {row.status === 'improved' && <span className="text-[var(--status-success)]">+{Math.round(row.delta * 100)}%</span>}
                {row.status === 'regressed' && <span className="text-[var(--status-error)]">{Math.round(row.delta * 100)}%</span>}
                {row.status === 'new' && <Badge variant="info">New</Badge>}
                {row.status === 'removed' && <Badge variant="failed">Lost</Badge>}
                {row.status === 'unchanged' && <span className="text-muted">0%</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
