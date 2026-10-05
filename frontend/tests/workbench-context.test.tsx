import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { WorkbenchProvider, useWorkbench } from '@/context/WorkbenchContext';

// Helper to render the hook with the provider
function renderWorkbenchHook() {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <WorkbenchProvider>{children}</WorkbenchProvider>
  );
  return renderHook(() => useWorkbench(), { wrapper });
}

describe('WorkbenchContext', () => {
  it('initializes with default state', () => {
    const { result } = renderWorkbenchHook();
    expect(result.current.phase).toBe('chat');
    expect(result.current.documentFileName).toBeNull();
    expect(result.current.documentUrl).toBeNull();
    expect(result.current.runId).toBeNull();
    expect(result.current.runStatus).toBe('idle');
  });

  it('should throw when used outside provider', () => {
    expect(() => renderHook(() => useWorkbench())).toThrow(
      'useWorkbench must be used within a WorkbenchProvider'
    );
  });

  it('setDocument sets file name, URL, and transitions to document phase', () => {
    const { result } = renderWorkbenchHook();
    act(() => {
      result.current.setDocument('invoice.pdf', 'doc-123');
    });
    expect(result.current.phase).toBe('document');
    expect(result.current.documentFileName).toBe('invoice.pdf');
    expect(result.current.documentUrl).toBe('doc-123');
  });

  it('setDocument defaults URL to null', () => {
    const { result } = renderWorkbenchHook();
    act(() => {
      result.current.setDocument('po.pdf');
    });
    expect(result.current.documentFileName).toBe('po.pdf');
    expect(result.current.documentUrl).toBeNull();
    expect(result.current.phase).toBe('document');
  });

  it('startRun sets run id, run status to running, and transitions to extraction', () => {
    const { result } = renderWorkbenchHook();
    act(() => {
      result.current.startRun('run-abc');
    });
    expect(result.current.phase).toBe('extraction');
    expect(result.current.runId).toBe('run-abc');
    expect(result.current.runStatus).toBe('running');
  });

  it('startRun generates an id when none provided', () => {
    const { result } = renderWorkbenchHook();
    // Mock crypto.randomUUID for deterministic id
    const uuid = vi.spyOn(crypto, 'randomUUID').mockReturnValue('a1b2c3d4-e5f6-7890-abcd-ef1234567890');
    act(() => {
      result.current.startRun();
    });
    expect(result.current.runId).toBe('run_a1b2c3d4e5f6');
    expect(result.current.runStatus).toBe('running');
    uuid.mockRestore();
  });

  it('completeRun sets run status to completed', () => {
    const { result } = renderWorkbenchHook();
    act(() => {
      result.current.startRun('run-1');
    });
    act(() => {
      result.current.completeRun();
    });
    expect(result.current.runStatus).toBe('completed');
  });

  it('reset clears all state and returns to chat phase', () => {
    const { result } = renderWorkbenchHook();
    // Set up some state
    act(() => {
      result.current.setDocument('invoice.pdf', 'doc-1');
    });
    act(() => {
      result.current.startRun('run-1');
    });
    act(() => {
      result.current.completeRun();
    });
    // Verify we're in non-default state
    expect(result.current.phase).toBe('extraction');
    expect(result.current.runStatus).toBe('completed');

    // Reset
    act(() => {
      result.current.reset();
    });
    expect(result.current.phase).toBe('chat');
    expect(result.current.documentFileName).toBeNull();
    expect(result.current.documentUrl).toBeNull();
    expect(result.current.runId).toBeNull();
    expect(result.current.runStatus).toBe('idle');
  });

  it('setRunStatus updates run status directly', () => {
    const { result } = renderWorkbenchHook();
    act(() => {
      result.current.setRunStatus('paused');
    });
    expect(result.current.runStatus).toBe('paused');
  });

  it('supports full lifecycle: chat → document → extraction → completed → chat', () => {
    const { result } = renderWorkbenchHook();

    // Initial
    expect(result.current.phase).toBe('chat');

    // Upload document
    act(() => result.current.setDocument('report.pdf', 'doc-99'));
    expect(result.current.phase).toBe('document');

    // Start extraction
    act(() => result.current.startRun('run-99'));
    expect(result.current.phase).toBe('extraction');
    expect(result.current.runStatus).toBe('running');

    // Running → Paused → Running
    act(() => result.current.setRunStatus('paused'));
    expect(result.current.runStatus).toBe('paused');
    act(() => result.current.setRunStatus('running'));

    // Complete
    act(() => result.current.completeRun());
    expect(result.current.runStatus).toBe('completed');

    // Reset to start again
    act(() => result.current.reset());
    expect(result.current.phase).toBe('chat');
    expect(result.current.documentFileName).toBeNull();
  });
});
