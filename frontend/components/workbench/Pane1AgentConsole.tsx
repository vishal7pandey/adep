'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Terminal, 
  Play, 
  Pause, 
  Square, 
  RotateCcw, 
  Undo2, 
  Minimize2, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Wrench, 
  BrainCircuit, 
  Image as ImageIcon, 
  Upload, 
  Layers, 
  ChevronDown, 
  ChevronUp, 
  FileSearch,
  AlertTriangle,
  Coins,
  ShieldAlert,
  Check,
  X
} from 'lucide-react';
import {
  AgentDefinition,
  fetchDefinitions,
  fetchDocument,
  startExtractionRun,
  stopRun,
  pauseRun,
  resumeRun,
  rollbackRun,
  compactRun,
  approveRun,
  rejectRun,
  uploadDocument,
  suggestAgent,
  AgentSuggestionResult,
} from '@/lib/api';
import { connectToRunStream, SSEThoughtEvent, SSEToolCallEvent, SSEToolResultEvent } from '@/lib/sse';
import { AdeButton } from '@/components/ui/AdeButton';
import { AdeBadge } from '@/components/ui/AdeBadge';
import { useWorkbench, RunStatusType } from '@/context/WorkbenchContext';

export interface ConsoleTraceCycle {
  cycleNumber: number;
  thought?: SSEThoughtEvent;
  toolCall?: SSEToolCallEvent;
  toolResult?: SSEToolResultEvent;
}

function dedupeDefinitions(defs: AgentDefinition[]): AgentDefinition[] {
  const byName = new Map<string, AgentDefinition>();

  for (const def of defs) {
    const key = def.name.trim().toLowerCase();
    const existing = byName.get(key);
    if (!existing) {
      byName.set(key, def);
      continue;
    }

    const keepCurrent =
      existing.id === 'def-pnid-to-dexpi' && def.id === 'def-pid-to-dexpi';
    if (keepCurrent) {
      byName.set(key, def);
    }
  }

  return Array.from(byName.values());
}

export const Pane1AgentConsole: React.FC = () => {
  const [cycles, setCycles] = useState<ConsoleTraceCycle[]>([]);
  const [runState, setRunState] = useState<RunStatusType>('idle');

  const [isCompacting, setIsCompacting] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [completedFieldsCount, setCompletedFieldsCount] = useState(0);
  const [totalFields, setTotalFields] = useState(6);
  const [runningTokens, setRunningTokens] = useState(0);
  const [runningCost, setRunningCost] = useState(0);
  const [definitions, setDefinitions] = useState<AgentDefinition[]>([]);
  const [selectedDefId, setSelectedDefId] = useState<string>('');
  const [hasManualDefinitionSelection, setHasManualDefinitionSelection] = useState(false);
  const [collapsedCycles, setCollapsedCycles] = useState<Record<number, boolean>>({});
  const [gateInfo, setGateInfo] = useState<{ reason: string; required_action: string; cycle: number } | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [disclosureLevel, setDisclosureLevel] = useState<1 | 2 | 3>(2);
  const [showRollbackDropdown, setShowRollbackDropdown] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isClassifying, setIsClassifying] = useState(false);
  const [suggestionResult, setSuggestionResult] = useState<AgentSuggestionResult | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const { phase, runStatus, documentFileName, documentUrl, runId, setDocument, startRun, completeRun } = useWorkbench();

  const [defError, setDefError] = useState<string | null>(null);

  useEffect(() => {
    fetchDefinitions().then((defs) => {
      const uniqueDefs = dedupeDefinitions(defs);
      setDefinitions(uniqueDefs);
      if (uniqueDefs.length > 0) setSelectedDefId(uniqueDefs[0].id);
    }).catch((err) => {
      setDefinitions([]);
      const msg = err instanceof Error ? err.message : 'Backend server offline';
      setDefError(msg);
      setNotification(`Agent fetch warning: ${msg}. Check backend server or API Key.`);
    });
  }, []);

  const handlePauseResume = useCallback(async () => {
    if (!activeRunId) return;
    if (runState === 'running') {
      setRunState('paused');
      await pauseRun(activeRunId);
      setNotification('Run execution paused at cycle boundary');
    } else if (runState === 'paused') {
      setRunState('running');
      await resumeRun(activeRunId);
      setNotification('Run execution resumed');
    }
    setTimeout(() => setNotification(null), 3000);
  }, [activeRunId, runState]);

  // BLK-117: Keyboard shortcuts listener for Space (Pause/Resume) and 1/2/3 (Disclosure Levels)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.code === 'Space' && (runState === 'running' || runState === 'paused')) {
        e.preventDefault();
        handlePauseResume();
      } else if (e.key === '1') {
        e.preventDefault();
        setDisclosureLevel(1);
      } else if (e.key === '2') {
        e.preventDefault();
        setDisclosureLevel(2);
      } else if (e.key === '3') {
        e.preventDefault();
        setDisclosureLevel(3);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [runState, handlePauseResume]);

  // Sync internal state with WorkbenchContext
  useEffect(() => {
    if (phase === 'chat') {
      setCycles([]);
      setRunState('idle');
      setActiveRunId(null);
      setCompletedFieldsCount(0);
      setRunningTokens(0);
      setRunningCost(0);
      setUploadedFileName(null);
      setCollapsedCycles({});
    } else if (phase === 'document') {
      setUploadedFileName(documentFileName);
      setRunState('idle');
    } else if (phase === 'extraction') {
      setUploadedFileName(documentFileName || null);
      setActiveRunId(runId);
      if (runStatus === 'completed') setRunState('completed');
      else if (runStatus === 'paused') setRunState('paused');
      else if (runStatus === 'stopped') setRunState('stopped');
      else if (runStatus === 'running') setRunState('running');
      else setRunState('idle');
    }
  }, [phase, runStatus, documentFileName, runId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [cycles]);

  const toggleCycleCollapse = (cycleNum: number) => {
    setCollapsedCycles((prev) => ({ ...prev, [cycleNum]: !prev[cycleNum] }));
  };

  const handleStop = async () => {
    if (!activeRunId) return;
    setRunState('stopped');
    await stopRun(activeRunId);
    setNotification('Run halted by user — partial results preserved');
    setTimeout(() => setNotification(null), 4000);
  };

  const handleRollback = async (toCycle: number) => {
    if (!activeRunId) return;
    setShowRollbackDropdown(false);
    await rollbackRun(activeRunId, toCycle);
    setCycles((prev) => prev.filter((c) => c.cycleNumber <= toCycle));
    setNotification(`Rolled back context to cycle ${toCycle}`);
    setTimeout(() => setNotification(null), 4000);
  };

  const handleCompact = async () => {
    if (!activeRunId) return;
    setIsCompacting(true);
    await compactRun(activeRunId);

    setTimeout(() => {
      setIsCompacting(false);
      setNotification('Context compacted: 15 trace entries → 420 char summary');
      setTimeout(() => setNotification(null), 4000);
    }, 1200);
  };

  const [isUploading, setIsUploading] = useState(false);
  const streamCleanupRef = useRef<(() => void) | null>(null);

  // BLK-245: Cleanup active SSE stream on component unmount
  useEffect(() => {
    return () => {
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
        streamCleanupRef.current = null;
      }
    };
  }, []);


  const handleApproveGate = async () => {
    if (!activeRunId) return;
    try {
      await approveRun(activeRunId);
      setGateInfo(null);
      setRunState('running');
      setNotification('HITL Gate approved — agent resuming execution');
    } catch (err) {
      setNotification(`Approval failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleRejectGate = async () => {
    if (!activeRunId) return;
    try {
      await rejectRun(activeRunId, 'User rejected execution');
      setGateInfo(null);
      setRunState('stopped');
      setNotification('HITL Gate rejected — run halted by user');
    } catch (err) {
      setNotification(`Rejection failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleStartRun = async (definitionOverride?: string | React.MouseEvent) => {
    const effectiveDefinitionId = typeof definitionOverride === 'string' ? definitionOverride : selectedDefId;
    if ((!uploadedFileName && !documentFileName) || !effectiveDefinitionId) return;
    setCycles([]);
    setRunState('running');
    setCompletedFieldsCount(0);
    setNotification(null);
    setGateInfo(null);
    setRunningTokens(0);
    setRunningCost(0);

    const docUrl = documentUrl || uploadedFileName || documentFileName || '';
    let resolvedDocumentPath = docUrl;

    const isLikelyDocumentId =
      !!docUrl
      && /^[a-zA-Z0-9_-]+$/.test(docUrl)
      && !docUrl.includes('.')
      && !docUrl.includes('\\')
      && !docUrl.includes('/');

    if (isLikelyDocumentId) {
      try {
        const meta = await fetchDocument(docUrl);
        resolvedDocumentPath = meta.page_paths[0] || docUrl;
      } catch {
        resolvedDocumentPath = docUrl;
      }
    }

    try {
      const run = await startExtractionRun(effectiveDefinitionId, resolvedDocumentPath);
      const newRunId = run.id;
      setActiveRunId(newRunId);
      startRun(newRunId);

      if (streamCleanupRef.current) {
        streamCleanupRef.current();
      }

      const cleanup = connectToRunStream(newRunId, {
        onThought: (evt) => {
          setCycles((prev) => {
            const existing = prev.find((c) => c.cycleNumber === evt.cycle);
            if (existing) {
              return prev.map((c) => (c.cycleNumber === evt.cycle ? { ...c, thought: evt } : c));
            }
            return [...prev, { cycleNumber: evt.cycle, thought: evt }];
          });
        },
        onToolCall: (evt) => {
          setCycles((prev) => {
            const existing = prev.find((c) => c.cycleNumber === evt.cycle);
            if (existing) {
              return prev.map((c) => (c.cycleNumber === evt.cycle ? { ...c, toolCall: evt } : c));
            }
            return [...prev, { cycleNumber: evt.cycle, toolCall: evt }];
          });
        },
        onToolResult: (evt) => {
          setCycles((prev) => {
            const existing = prev.find((c) => c.cycleNumber === evt.cycle);
            if (existing) {
              return prev.map((c) => (c.cycleNumber === evt.cycle ? { ...c, toolResult: evt } : c));
            }
            return [...prev, { cycleNumber: evt.cycle, toolResult: evt }];
          });
        },
        onProgress: (evt) => {
          setCompletedFieldsCount(evt.completed_fields);
          setTotalFields(evt.total_fields);
        },
        onGateTriggered: (evt) => {
          setRunState('paused');
          setGateInfo({ reason: evt.reason, required_action: evt.required_action, cycle: evt.cycle });
          setNotification(`HITL Gate Triggered (Cycle ${evt.cycle}): ${evt.reason}`);
        },
        onTrajectoryWarning: (evt) => {
          setNotification(`⚠️ Trajectory Warning (Cycle ${evt.cycle}): ${evt.message}`);
        },
        onTrajectoryCritical: (evt) => {
          setNotification(`🚨 Trajectory Critical Alert (Cycle ${evt.cycle}): ${evt.message}`);
        },
        onComplete: (evt) => {
          if (evt.status === 'success' || evt.status === 'completed') {
            setRunState('completed');
            setRunStatus('completed');
          } else if (evt.status === 'max_iterations_reached') {
            setRunState('max_iterations_reached');
            setRunStatus('max_iterations_reached');
            setNotification('Extraction halted: Maximum iterations limit reached.');
          } else if (evt.status === 'cancelled') {
            setRunState('cancelled');
            setRunStatus('cancelled');
            setNotification('Extraction cancelled by user.');
          } else if (evt.status === 'failed') {
            setRunState('failed');
            setRunStatus('failed');
            setNotification(evt.summary || 'Extraction failed during execution.');
          } else {
            setRunState('stopped');
            setRunStatus('stopped');
            setNotification(evt.summary || `Run ended with status: ${evt.status}`);
          }
        },

        onStopped: () => {
          setRunState('stopped');
        },
        onPaused: () => {
          setRunState('paused');
        },
        onResumed: () => {
          setRunState('running');
        },
        onReconnecting: (attempt, delayMs) => {
          setNotification(`Connection lost. Reconnecting (attempt #${attempt}, retrying in ${delayMs / 1000}s)...`);
        },
        onReconnectFailed: () => {
          setNotification('Connection lost. Please check backend server and click Retry.');
          setRunState('stopped');
        },
      });

      streamCleanupRef.current = cleanup;
    } catch (err) {
      setNotification(`Failed to start extraction: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setRunState('idle');
    }
  };

  const processUploadedFile = async (file: File) => {
    setUploadedFileName(file.name);
    setIsUploading(true);
    setIsClassifying(true);
    try {
      const res = await uploadDocument(file);
      const docId = res.document_id;
      setDocument(res.original_filename || file.name, docId);

      try {
        const suggestion = await suggestAgent(docId);
        setSuggestionResult(suggestion);
        if (!hasManualDefinitionSelection && suggestion.predictions.length > 0) {
          const top = suggestion.predictions[0];
          if (top.confidence >= 0.75 && top.suggested_definition_id) {
            setSelectedDefId(top.suggested_definition_id);
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Classification service unavailable';
        setNotification(`Classification notice: ${msg}. Agent definition selection preserved.`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setNotification(`Upload failed: ${msg}`);
    } finally {
      setIsUploading(false);
      setIsClassifying(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await processUploadedFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      await processUploadedFile(files[0]);
    }
  };

  const progressPercentage = totalFields > 0 ? Math.round((completedFieldsCount / totalFields) * 100) : 0;

  return (
    <div className="h-full flex flex-col border-r border-[var(--pane-border)] bg-[var(--pane-bg)] overflow-hidden">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 bg-[var(--pane-bg)] border-b border-[var(--pane-border)] shadow-2xs">
        {/* Row 1: Identity, Status & Token Display */}
        <div className="px-4 py-2.5 flex items-center justify-between bg-black/5 dark:bg-white/5 border-b border-[var(--pane-border)]">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-[var(--brand-primary)] text-white flex items-center justify-center">
              <FileSearch className="w-3.5 h-3.5" />
            </div>
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-xs leading-tight">Extraction Agent Definition</h2>
              {runState === 'running' && <AdeBadge variant="info">Running</AdeBadge>}
              {runState === 'paused' && <AdeBadge variant="medium">Paused</AdeBadge>}
              {runState === 'completed' && <AdeBadge variant="verified">Completed</AdeBadge>}
              {runState === 'failed' && <AdeBadge variant="failed">Failed</AdeBadge>}
              {runState === 'cancelled' && <AdeBadge variant="neutral">Cancelled</AdeBadge>}
              {runState === 'max_iterations_reached' && <AdeBadge variant="medium">Max Iterations Reached</AdeBadge>}
              {runState === 'stopped' && <AdeBadge variant="neutral">Stopped</AdeBadge>}
              {runState === 'idle' && <AdeBadge variant="neutral">Idle</AdeBadge>}

            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-muted flex items-center gap-1">
              <Coins className="w-3.5 h-3.5 text-[var(--status-warning)]" />
              <span>{runningTokens.toLocaleString()} tokens</span>
            </span>
            <span className="text-muted font-bold">${runningCost.toFixed(4)}</span>

            <div className="flex items-center bg-black/10 dark:bg-white/10 p-0.5 rounded text-[11px] font-medium ml-2">
              <button
                onClick={() => setDisclosureLevel(1)}
                className={`px-2 py-0.5 rounded transition-colors ${disclosureLevel === 1 ? 'bg-[var(--brand-primary)] text-white' : 'text-muted'}`}
              >
                Summary
              </button>
              <button
                onClick={() => setDisclosureLevel(2)}
                className={`px-2 py-0.5 rounded transition-colors ${disclosureLevel === 2 ? 'bg-[var(--brand-primary)] text-white' : 'text-muted'}`}
              >
                Detailed
              </button>
              <button
                onClick={() => setDisclosureLevel(3)}
                className={`px-2 py-0.5 rounded transition-colors ${disclosureLevel === 3 ? 'bg-[var(--brand-primary)] text-white' : 'text-muted'}`}
              >
                Expert
              </button>
            </div>
          </div>
        </div>

        {/* Row 2: Control Toolbar */}
        <div className="px-4 py-2 flex items-center justify-between bg-black/5 dark:bg-white/5 border-b border-[var(--pane-border)]">
          <div className="flex items-center gap-1.5">
            {runState === 'idle' && (
              <AdeButton variant="primary" size="sm" onClick={() => { void handleStartRun(); }} disabled={!uploadedFileName && !documentFileName}>
                <Play className="w-3.5 h-3.5" /> Start Run
              </AdeButton>
            )}

            {runState === 'running' && (
              <AdeButton variant="primary" size="sm" onClick={handlePauseResume}>
                <Pause className="w-3.5 h-3.5" /> Pause
              </AdeButton>
            )}

            {runState === 'paused' && (
              <AdeButton variant="primary" size="sm" onClick={handlePauseResume}>
                <Play className="w-3.5 h-3.5" /> Resume
              </AdeButton>
            )}

            {(runState === 'running' || runState === 'paused') && (
              <AdeButton variant="destructive" size="sm" onClick={handleStop}>
                <Square className="w-3.5 h-3.5 fill-current" /> Stop
              </AdeButton>
            )}

            {runState === 'completed' && (
              <AdeButton variant="primary" size="sm" onClick={() => { void handleStartRun(); }}>
                <RotateCcw className="w-3.5 h-3.5" /> Re-run
              </AdeButton>
            )}

            {cycles.length > 0 && (
              <div className="relative">
                <AdeButton variant="tertiary" size="sm" onClick={() => setShowRollbackDropdown(!showRollbackDropdown)}>
                  <Undo2 className="w-3.5 h-3.5 text-[var(--brand-primary)]" /> Rollback
                </AdeButton>

                {showRollbackDropdown && (
                  <div className="absolute top-full left-0 mt-1 w-40 bg-[var(--pane-bg)] border border-[var(--pane-border)] rounded-lg shadow-xl py-1 z-30 text-xs">
                    <div className="px-3 py-1 font-semibold text-muted border-b border-[var(--pane-border)] text-[10px]">
                      Select Rewind Cycle
                    </div>
                    {cycles.map((c) => (
                      <button
                        key={c.cycleNumber}
                        onClick={() => handleRollback(c.cycleNumber)}
                        className="w-full text-left px-3 py-1.5 hover:bg-[var(--brand-primary)] hover:text-white flex items-center justify-between"
                      >
                        <span>Cycle #{c.cycleNumber}</span>
                        <span className="text-[10px] opacity-70">{c.thought?.timestamp}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            <AdeButton variant="tertiary" size="sm" onClick={handleCompact} disabled={cycles.length < 3 || isCompacting}>
              <Minimize2 className="w-3.5 h-3.5" /> {isCompacting ? 'Compacting…' : 'Compact Memory'}
            </AdeButton>
          </div>

          {/* Agent Definition Selector */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-muted shrink-0 flex items-center gap-1">
              <Layers className="w-3.5 h-3.5 text-[var(--brand-primary)]" />
              Agent Definition:
            </span>
            <select
              value={selectedDefId}
              onChange={(e) => {
                setSelectedDefId(e.target.value);
                setHasManualDefinitionSelection(true);
              }}
              disabled={runState === 'running'}
              className="min-w-[180px] max-w-[240px] px-2.5 py-1 rounded-md border border-[var(--pane-border)] bg-[var(--pane-bg)] text-xs font-semibold text-[var(--primary-text)] focus:outline-none focus:border-[var(--brand-primary)]"
            >
              {definitions.length === 0 ? (
                <option value="">No definitions available</option>
              ) : (
                definitions.map((def) => (
                  <option key={def.id} value={def.id}>
                    {def.name}
                  </option>
                ))
              )}
            </select>

            {(uploadedFileName || documentFileName) && (
              <label className="flex items-center gap-1 px-2 py-1 rounded border border-dashed border-[var(--brand-primary)] text-[var(--brand-primary)] hover:bg-[var(--brand-primary-subtle)] cursor-pointer text-[11px] font-medium transition-colors">
                <Upload className="w-3 h-3" />
                <span>Change</span>
                <input type="file" onChange={handleFileUpload} accept=".pdf,.png,.jpg,.jpeg,.tiff" className="hidden" />
              </label>
            )}
          </div>
        </div>

        {/* Row 3: Live Extraction Progress Bar */}
        {(runState === 'running' || runState === 'completed' || completedFieldsCount > 0) && (
          <div className="px-4 py-2 bg-black/5 dark:bg-white/5 border-b border-[var(--pane-border)] flex items-center gap-3">
            <div className="flex-1 flex items-center justify-between text-xs">
              <span className="font-semibold text-muted">Fields Grounded</span>
              <span className="font-mono font-bold text-[var(--primary-text)]">
                {completedFieldsCount} / {totalFields} ({progressPercentage}%)
              </span>
            </div>

            <div className="w-32 bg-black/10 dark:bg-white/10 h-2 rounded-full overflow-hidden">
              <div
                className="bg-[var(--status-success)] h-full transition-all duration-500 ease-out"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Notification Toast */}
      {notification && (
        <div className="px-4 py-2 bg-[var(--brand-primary-muted)] border-b border-[var(--brand-primary)] text-xs text-[var(--brand-primary)] font-medium flex items-center gap-1.5 animate-fadeIn">
          <Sparkles className="w-3.5 h-3.5 text-[var(--brand-primary)] shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Trace Log Content */}
      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-3">
        {cycles.length === 0 ? (
          <div className="h-full flex flex-col gap-4">
            {/* BLK-131: Upload-First Flow State 1 — No document uploaded yet */}
            {!uploadedFileName && !documentFileName && (
              <div
                ref={dropZoneRef}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`flex-1 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-6 text-center space-y-3 transition-all duration-200 ${
                  isDragOver
                    ? 'border-[var(--brand-accent)] bg-[var(--brand-accent-subtle)] scale-[1.01] shadow-lg'
                    : 'border-[var(--pane-border)] hover:border-[var(--brand-primary)]/50'
                }`}
              >
                <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                  isDragOver
                    ? 'bg-[var(--brand-accent-subtle)] text-[var(--brand-accent)] animate-pulse scale-110'
                    : 'bg-[var(--brand-primary-subtle)] text-[var(--brand-primary)]'
                }`}>
                  {isDragOver ? <Upload className="w-7 h-7" /> : <BrainCircuit className="w-7 h-7" />}
                </div>
                <div>
                  <h3 className="font-bold text-sm text-[var(--primary-text)]">
                    {isDragOver ? 'Drop your document here' : 'Upload a Document to Begin'}
                  </h3>
                  <p className="text-xs max-w-xs mt-1 text-muted">
                    {isDragOver
                      ? 'Release to upload PDF, PNG, JPG, or TIFF'
                      : 'Upload your document first. ADEP will classify its structure and suggest the best matching extraction agent definition automatically.'}
                  </p>
                </div>
                {!isDragOver && (
                  <label className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--brand-primary)] text-white text-xs font-semibold cursor-pointer hover:bg-[var(--brand-primary-hover)] transition-colors shadow-2xs">
                    <Upload className="w-3.5 h-3.5" />
                    <span>Choose File</span>
                    <input type="file" onChange={handleFileUpload} accept=".pdf,.png,.jpg,.jpeg,.tiff" className="hidden" />
                  </label>
                )}
              </div>
            )}

            {/* BLK-131: Classification Loading State */}
            {isClassifying && (
              <div className="p-6 rounded-xl border border-[var(--brand-primary)] bg-[var(--brand-primary-subtle)] text-center space-y-3 animate-pulse">
                <Sparkles className="w-8 h-8 mx-auto text-[var(--brand-primary)] animate-spin" />
                <h3 className="font-bold text-sm text-[var(--primary-text)]">Classifying Document Structure...</h3>
                <p className="text-xs text-muted">Analyzing document layout, headers, and matching optimal extraction agent definition.</p>
              </div>
            )}

            {/* BLK-131: Agent Suggestion Recommendation Card */}
            {(uploadedFileName || documentFileName) && !isClassifying && suggestionResult && (
              <div className="p-4 rounded-xl border border-[var(--brand-primary)] bg-[var(--card-bg)] space-y-3.5 shadow-md animate-fadeIn">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[var(--brand-primary)]" />
                    <span className="font-bold text-xs text-[var(--primary-text)]">
                      This looks like an {suggestionResult.predictions[0]?.document_type.toUpperCase() || 'DOCUMENT'}
                    </span>
                  </div>
                  <AdeBadge variant="verified">
                    {Math.round((suggestionResult.predictions[0]?.confidence || 0.92) * 100)}% Confident
                  </AdeBadge>
                </div>

                <p className="text-xs text-muted leading-relaxed">
                  {suggestionResult.predictions[0]?.reasoning || 'Detected document structure and matching extraction schema.'}
                </p>

                {/* Multi-Type Document Limitation Notice */}
                {suggestionResult.is_multi_type && (
                  <div className="p-2.5 rounded-lg border border-[var(--status-warning)] bg-[var(--status-warning-subtle)] text-xs text-[var(--primary-text)] space-y-1">
                    <div className="font-bold text-[var(--status-warning)] flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Multi-Type Document Detected</span>
                    </div>
                    <p className="text-[11px] text-muted">
                      This file contains multiple document types. The agent definition will process the entire file using the primary suggested agent definition.
                    </p>
                  </div>
                )}

                {/* Agent Selection & Run CTAs */}
                <div className="pt-2 border-t border-[var(--pane-border)] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted">Suggested Agent Definition:</span>
                    <strong className="text-xs text-[var(--brand-primary)]">
                      {definitions.find((d) => d.id === selectedDefId)?.name || 'Standard Invoice Extractor'}
                    </strong>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <AdeButton variant="primary" size="sm" onClick={() => { void handleStartRun(); }} className="flex-1">
                      <Play className="w-3.5 h-3.5" /> Start Run with Suggested Agent Definition
                    </AdeButton>
                    <AdeButton
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelectedDefId('auto');
                        handleStartRun('auto');
                      }}
                    >
                      <Sparkles className="w-3.5 h-3.5" /> Let ADEP Auto-Route
                    </AdeButton>
                  </div>
                </div>

                {/* Alternative Predictions List */}
                {suggestionResult.predictions.length > 1 && (
                  <div className="pt-2 border-t border-[var(--pane-border)] space-y-1 text-[11px]">
                    <span className="font-semibold text-muted">Other Possibilities:</span>
                    <div className="flex items-center gap-2 pt-0.5">
                      {suggestionResult.predictions.slice(1).map((p) => (
                        <button
                          key={p.document_type}
                          onClick={() => setSelectedDefId(p.suggested_definition_id)}
                          className="px-2 py-1 rounded border border-[var(--pane-border)] hover:border-[var(--brand-primary)] bg-black/5 dark:bg-white/5 font-mono"
                        >
                          {p.document_type} ({Math.round(p.confidence * 100)}%)
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          cycles.map((cycle) => {
            const isCollapsed = collapsedCycles[cycle.cycleNumber];

            return (
              <div
                key={cycle.cycleNumber}
                className="rounded-lg border border-[var(--card-border)] bg-[var(--card-bg)] p-3 shadow-xs text-xs space-y-2.5 transition-all hover:border-[var(--brand-primary)]/50"
              >
                <div
                  onClick={() => toggleCycleCollapse(cycle.cycleNumber)}
                  className="flex items-center justify-between text-[11px] font-semibold text-[var(--secondary-text)] border-b border-black/5 dark:border-white/5 pb-1 cursor-pointer select-none"
                >
                  <span className="flex items-center gap-1.5">
                    {isCollapsed ? <ChevronDown className="w-3.5 h-3.5 text-muted" /> : <ChevronUp className="w-3.5 h-3.5 text-muted" />}
                    <span>Cycle #{cycle.cycleNumber}</span>
                  </span>
                  <div className="flex items-center gap-1">
                    {cycle.thought && <AdeBadge variant="info">Thought</AdeBadge>}
                    {cycle.toolCall && <AdeBadge variant="tool">{cycle.toolCall.tool}</AdeBadge>}
                    {cycle.toolResult && <AdeBadge variant="verified">Observation</AdeBadge>}
                  </div>
                </div>

                {!isCollapsed && (
                  <div className="space-y-2 pt-1">
                    {cycle.thought && (
                      <div className="p-2 rounded bg-black/5 dark:bg-white/5 font-mono text-[11px] text-[var(--primary-text)] border-l-2 border-[var(--brand-accent)]">
                        {cycle.thought.text}
                      </div>
                    )}

                    {disclosureLevel >= 2 && cycle.toolCall && (
                      <div className="p-2 rounded bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5 space-y-1.5">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-muted flex items-center gap-1">
                            <Wrench className="w-3 h-3 text-[var(--brand-primary)]" /> Action Invocation:
                          </span>
                          <AdeBadge variant="tool">{cycle.toolCall.tool}</AdeBadge>
                        </div>
                        <div className="flex items-center gap-2">
                          <AdeBadge variant="neutral">
                            args
                          </AdeBadge>
                          <span className="text-[11px] font-mono text-muted overflow-hidden text-ellipsis whitespace-nowrap max-w-[200px]">
                            {JSON.stringify(cycle.toolCall.args)}
                          </span>
                        </div>

                        {/* Interactive HITL Gate Approval Card */}
                        {(gateInfo || ['azure_vlm', 'vlm_escalation', 'db_write', 'external_api'].includes(cycle.toolCall.tool)) && (
                          <div className="p-3 rounded-xl border border-[var(--brand-primary)] bg-[var(--brand-primary-subtle)] space-y-2 animate-fadeIn shadow-sm">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5 text-[var(--brand-primary)] font-bold text-xs">
                                <ShieldAlert className="w-4 h-4" />
                                <span>Human-in-the-Loop Safety Gate</span>
                              </div>
                              <AdeBadge variant="info">Paused for Approval</AdeBadge>
                            </div>
                            <p className="text-xs text-[var(--primary-text)] font-medium">
                              {gateInfo?.reason || `Tool "${cycle.toolCall.tool}" is flagged for high-impact visual or external operation.`}
                            </p>
                            {gateInfo?.required_action && (
                              <p className="text-[11px] font-mono text-muted">Action Required: {gateInfo.required_action}</p>
                            )}
                            <div className="flex items-center gap-2 pt-1">
                              <AdeButton variant="primary" size="sm" onClick={handleApproveGate}>
                                <Check className="w-3.5 h-3.5" /> Approve Action
                              </AdeButton>
                              <AdeButton variant="secondary" size="sm" onClick={handleRejectGate}>
                                <X className="w-3.5 h-3.5" /> Reject Action
                              </AdeButton>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {disclosureLevel >= 2 && cycle.toolResult && (
                      <div className="p-2 rounded bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5">
                        <div className="flex items-center justify-between mb-1 text-[11px] text-[var(--status-success)] font-medium">
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Observation
                          </span>
                        </div>
                        <pre className="font-mono text-[10px] text-muted overflow-x-auto p-1 bg-black/10 dark:bg-black/30 rounded">
                          {JSON.stringify(cycle.toolResult.result, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
