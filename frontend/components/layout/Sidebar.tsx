'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { 
  Sparkles, 
  Database, 
  Sun, 
  Moon, 
  ChevronLeft, 
  ChevronRight,
  Layers,
  ShieldCheck,
  Plus,
  MoreVertical,
  CheckCircle2,
  Clock,
  FileText,
  Trash2,
  Copy,
  Edit2,
  ChevronDown,
  BarChart3,
  Key
} from 'lucide-react';

import { useTheme } from '@/context/ThemeContext';
import { useWorkbench } from '@/context/WorkbenchContext';
import { ExtractionRun, fetchRecentRuns, deleteRun, duplicateRun, renameRun } from '@/lib/api';

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [sessions, setSessions] = useState<ExtractionRun[]>([]);
  const [showAllSessions, setShowAllSessions] = useState(false);
  const [openMenuRunId, setOpenMenuRunId] = useState<string | null>(null);

  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeRunId = searchParams.get('run');

  const { theme, toggleTheme } = useTheme();
  const { reset, setDocument, startRun, setRunStatus } = useWorkbench();

  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    fetchRecentRuns(10)
      .then(setSessions)
      .catch((err) => {
        setSessions([]);
        setSessionError(err instanceof Error ? err.message : 'Backend server offline');
      });
  }, []);

  useEffect(() => {
    function handleClickOutside() {
      if (openMenuRunId !== null) {
        setOpenMenuRunId(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [openMenuRunId]);

  const handleNewSession = () => {
    reset();
    router.push('/');
  };

  const handleSelectSession = (id: string) => {
    const session = sessions.find((s) => s.id === id);
    if (session) {
      const docUrl = session.document_url || '';
      const docName = docUrl.includes('\\') ? docUrl.split('\\').pop() || docUrl : docUrl;
      setDocument(docName || 'document', docUrl || null);
      startRun(id);
      if (session.status) setRunStatus(session.status);
      else setRunStatus('stopped');
    }
    router.push(`/?run=${id}`);
  };


  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenuRunId(null);
    await deleteRun(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeRunId === id) {
      reset();
      router.push('/');
    }
  };

  const handleDuplicateSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenuRunId(null);
    const duplicated = await duplicateRun(id);
    setSessions((prev) => [duplicated, ...prev]);
  };

  const handleRenameSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenuRunId(null);
    const newName = prompt('Enter new session name:');
    if (newName) {
      await renameRun(id, newName);
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, document_url: newName } : s))
      );
    }
  };

  const visibleSessions = showAllSessions ? sessions : sessions.slice(0, 3);

  return (
    <aside
      className={`relative transition-all duration-300 ease-in-out flex flex-col z-20 shadow-lg ${
        collapsed ? 'w-16' : 'w-64'
      }`}
      style={{
        backgroundColor: 'var(--sidebar-bg)',
        color: 'var(--sidebar-text)',
      }}
    >
      {/* Header / Brand */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-white/10 shrink-0">
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--brand-primary)] flex items-center justify-center font-bold text-white shadow-xs">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-sm leading-tight text-white tracking-tight">ADEP Workbench</h1>
              <p className="text-[10px] text-[var(--brand-accent)] font-medium">Local Agentic Extraction</p>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 mx-auto rounded-lg bg-[var(--brand-primary)] flex items-center justify-center font-bold text-white">
            <ShieldCheck className="w-5 h-5" />
          </div>
        )}
      </div>

      {/* Main Sidebar Navigation Area */}
      <div className="flex-1 py-3 px-2 space-y-4 overflow-y-auto">
        {/* New Session Button */}
        <button
          onClick={handleNewSession}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white font-semibold text-xs transition-colors shadow-2xs ${
            collapsed ? 'justify-center px-0' : ''
          }`}
          title="New Extraction Session"
        >
          <Plus className="w-4 h-4" />
          {!collapsed && <span>New Session</span>}
        </button>

        {/* Recent Sessions List */}
        {!collapsed && (
          <div className="space-y-1">
            <div className="flex items-center justify-between px-2 text-[10px] font-bold text-white/60 uppercase tracking-wider">
              <span>Recent Sessions</span>
              {sessions.length > 3 && (
                <button
                  onClick={() => setShowAllSessions(!showAllSessions)}
                  className="hover:text-white flex items-center gap-0.5 text-[9px]"
                >
                  {showAllSessions ? 'Less' : `More (${sessions.length - 3})`}
                  <ChevronDown className={`w-3 h-3 transition-transform ${showAllSessions ? 'rotate-180' : ''}`} />
                </button>
              )}
            </div>

            <div className="space-y-0.5 pt-1">
              {sessionError ? (
                <div className="px-2 py-1.5 text-[10px] text-red-300/80 italic leading-tight">
                  {sessionError.includes('401')
                    ? 'Auth error: Set API Key in Settings'
                    : 'Backend server offline (port 8000)'}
                </div>
              ) : visibleSessions.length === 0 ? (
                <div className="px-2 py-1.5 text-[11px] text-white/40 italic">
                  No recent sessions yet
                </div>
              ) : (
                visibleSessions.map((s) => {
                const isSelected = activeRunId === s.id;
                const progressPct = Math.round((s.extracted_fields_count / (s.total_fields || 6)) * 100);

                return (
                  <div
                    key={s.id}
                    onClick={() => handleSelectSession(s.id)}
                    className={`group relative flex items-center justify-between px-2.5 py-2 rounded-md text-xs cursor-pointer transition-all ${
                      isSelected
                        ? 'border-l-3 border-[var(--brand-primary)] bg-[var(--brand-primary-muted)] text-white font-semibold'
                        : 'text-white/80 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      {s.status === 'completed' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-[var(--status-success)] shrink-0" />
                      ) : s.status === 'running' ? (
                        <Clock className="w-3.5 h-3.5 text-[var(--status-warning)] shrink-0 animate-spin" />
                      ) : (
                        <FileText className="w-3.5 h-3.5 text-[var(--brand-accent)] shrink-0" />
                      )}
                      <div className="overflow-hidden">
                        <div className="text-[11px] font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                          {s.document_url || s.id}
                        </div>
                        <div className="text-[9px] text-white/50">{progressPct}% extracted</div>
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuRunId(openMenuRunId === s.id ? null : s.id);
                      }}
                      className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-white/20 transition-opacity"
                    >
                      <MoreVertical className="w-3.5 h-3.5" />
                    </button>

                    {openMenuRunId === s.id && (
                      <div className="absolute right-1 top-8 bg-[var(--pane-bg)] border border-[var(--pane-border)] rounded-lg shadow-xl py-1 z-30 text-xs w-32 text-[var(--primary-text)]">
                        <button
                          onClick={(e) => handleRenameSession(s.id, e)}
                          className="w-full text-left px-3 py-1.5 hover:bg-[var(--brand-primary)] hover:text-white flex items-center gap-1.5"
                        >
                          <Edit2 className="w-3 h-3" /> Rename
                        </button>
                        <button
                          onClick={(e) => handleDuplicateSession(s.id, e)}
                          className="w-full text-left px-3 py-1.5 hover:bg-[var(--brand-primary)] hover:text-white flex items-center gap-1.5"
                        >
                          <Copy className="w-3 h-3" /> Duplicate
                        </button>
                        <button
                          onClick={(e) => handleDeleteSession(s.id, e)}
                          className="w-full text-left px-3 py-1.5 hover:bg-red-600 hover:text-white text-red-400 flex items-center gap-1.5"
                        >
                          <Trash2 className="w-3 h-3" /> Delete
                        </button>
                      </div>
                    )}
                  </div>
                );
              }))}
            </div>
          </div>
        )}

        <div className="border-t border-white/10 my-2" />

        {/* Library Section (Standardized "Choose Agent" Label) */}
        <div className="space-y-1">
          {!collapsed && (
            <div className="px-2 text-[10px] font-bold text-white/60 uppercase tracking-wider mb-1">
              Library
            </div>
          )}

          {[
            { href: '/definitions', label: 'Agent Definitions', icon: Layers },
            { href: '/skills', label: 'Skills', icon: Sparkles },
            { href: '/templates', label: 'Templates', icon: Database },
            { href: '/analytics', label: 'Analytics', icon: BarChart3 },
            { href: '/settings', label: 'API Keys & Auth', icon: Key },
          ].map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 text-xs transition-all rounded-r-md ${
                  isActive
                    ? 'border-l-3 border-[var(--brand-primary)] bg-[var(--brand-primary-muted)] text-white font-semibold'
                    : 'text-white/80 hover:bg-white/10 hover:text-white font-medium'
                } ${collapsed ? 'justify-center px-0 border-l-0 rounded-md' : ''}`}
                title={collapsed ? item.label : undefined}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[var(--brand-accent)]' : 'text-white/70'}`} />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Footer Controls */}
      <div className="p-3 border-t border-white/10 space-y-1 shrink-0">
        <button
          onClick={toggleTheme}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-white/10 text-white/90 ${
            collapsed ? 'justify-center px-0' : ''
          }`}
          title="Toggle Theme"
        >
          {theme === 'light' ? (
            <>
              <Moon className="w-4 h-4 text-[var(--status-warning)]" />
              {!collapsed && <span>Dark Mode</span>}
            </>
          ) : (
            <>
              <Sun className="w-4 h-4 text-[var(--status-warning)]" />
              {!collapsed && <span>Light Mode</span>}
            </>
          )}
        </button>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors"
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
};
