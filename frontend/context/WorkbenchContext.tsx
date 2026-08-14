'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

export type RunStatusType =
  | 'idle'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'max_iterations_reached'
  | 'stopped';

interface WorkbenchContextType {
  phase: WorkbenchPhase;
  documentFileName: string | null;
  documentUrl: string | null;
  runId: string | null;
  runStatus: RunStatusType;
  setDocument: (fileName: string, url?: string | null) => void;
  startRun: (runId?: string) => void;
  completeRun: () => void;
  reset: () => void;
  setRunStatus: (status: RunStatusType) => void;
}

const WorkbenchContext = createContext<WorkbenchContextType | undefined>(undefined);

export const WorkbenchProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [phase, setPhase] = useState<WorkbenchPhase>('chat');
  const [documentFileName, setDocumentFileName] = useState<string | null>(null);
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatusType>('idle');

  const setDocument = (fileName: string, url: string | null = null) => {
    setDocumentFileName(fileName);
    setDocumentUrl(url);
    setPhase('document');
  };

  const startRun = (id?: string) => {
    const effectiveId = id || `run_${crypto.randomUUID().replace(/-/g, '').substring(0, 12)}`;
    setRunId(effectiveId);
    setRunStatus('running');
    setPhase('extraction');
  };


  const completeRun = () => {
    setRunStatus('completed');
  };

  const reset = () => {
    setPhase('chat');
    setDocumentFileName(null);
    setDocumentUrl(null);
    setRunId(null);
    setRunStatus('idle');
  };

  return (
    <WorkbenchContext.Provider
      value={{
        phase,
        documentFileName,
        documentUrl,
        runId,
        runStatus,
        setDocument,
        startRun,
        completeRun,
        reset,
        setRunStatus,
      }}
    >
      {children}
    </WorkbenchContext.Provider>
  );
};

export const useWorkbench = (): WorkbenchContextType => {
  const context = useContext(WorkbenchContext);
  if (!context) {
    throw new Error('useWorkbench must be used within a WorkbenchProvider');
  }
  return context;
};
