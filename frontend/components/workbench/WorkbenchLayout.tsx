'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Pane1AgentConsole } from './Pane1AgentConsole';
import { Pane2ExtractedData } from './Pane2ExtractedData';
import { Pane3DocumentViewer } from './Pane3DocumentViewer';
import { RunComparisonView } from './RunComparisonView';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { useWorkbench } from '@/context/WorkbenchContext';

export const WorkbenchLayout: React.FC = () => {
  const { phase } = useWorkbench();
  const searchParams = useSearchParams();
  const router = useRouter();

  const isCompareView = searchParams.get('view') === 'compare';

  if (isCompareView) {
    return (
      <div className="h-full w-full bg-[var(--pane-bg)] overflow-hidden">
        <ErrorBoundary paneName="Run Comparison View">
          <RunComparisonView onClose={() => router.push('/')} />
        </ErrorBoundary>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-[var(--pane-bg)] transition-all duration-300 ease-in-out overflow-hidden">
      {/* Phase 1: Chat Phase (Pane 1 only, Full Width) */}
      {phase === 'chat' && (
        <div className="h-full w-full max-w-4xl mx-auto p-4 transition-all duration-300">
          <ErrorBoundary paneName="Agent Console (Pane 1)">
            <Pane1AgentConsole />
          </ErrorBoundary>
        </div>
      )}

      {/* Phase 2: Document Phase (Pane 1 + Pane 3, 2-Column Split) */}
      {phase === 'document' && (
        <div className="grid grid-cols-2 h-full w-full transition-all duration-300">
          <div className="h-full overflow-hidden">
            <ErrorBoundary paneName="Agent Console (Pane 1)">
              <Pane1AgentConsole />
            </ErrorBoundary>
          </div>
          <div className="h-full overflow-hidden border-l border-[var(--pane-border)]">
            <ErrorBoundary paneName="Document Viewer (Pane 3)">
              <Pane3DocumentViewer />
            </ErrorBoundary>
          </div>
        </div>
      )}

      {/* Phase 3: Extraction Phase (Pane 1 + Pane 3 + Pane 2 per Spec Order) */}
      {phase === 'extraction' && (
        <div className="grid grid-cols-3 h-full w-full transition-all duration-300">
          <div className="h-full overflow-hidden">
            <ErrorBoundary paneName="Agent Console (Pane 1)">
              <Pane1AgentConsole />
            </ErrorBoundary>
          </div>
          <div className="h-full overflow-hidden border-l border-[var(--pane-border)]">
            <ErrorBoundary paneName="Document Viewer (Pane 3)">
              <Pane3DocumentViewer />
            </ErrorBoundary>
          </div>
          <div className="h-full overflow-hidden border-l border-[var(--pane-border)]">
            <ErrorBoundary paneName="Extracted Data (Pane 2)">
              <Pane2ExtractedData />
            </ErrorBoundary>
          </div>
        </div>
      )}
    </div>
  );
};
