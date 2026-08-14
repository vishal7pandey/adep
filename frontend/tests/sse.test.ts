import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Test double for EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  closed = false;
  private static _lastInstance: MockEventSource | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
    MockEventSource._lastInstance = this;
  }

  static get lastInstance(): MockEventSource | null {
    return MockEventSource._lastInstance;
  }

  static clearInstances() {
    MockEventSource.instances = [];
    MockEventSource._lastInstance = null;
  }

  close() {
    this.closed = true;
  }

  // Test helpers
  emitOpen() {
    this.onopen?.();
  }

  emitMessage(data: string) {
    this.onmessage?.({ data });
  }

  emitError(err: unknown = new Error('connection error')) {
    this.onerror?.(err);
  }
}

// Mock the sse module so it picks up MockEventSource at module-load time
vi.mock('@/lib/sse', () => {
  const actual = require('@/lib/sse');
  return {
    ...actual,
  };
});

describe('connectToRunStream', () => {
  let originalEventSource: typeof EventSource;
  let timers: ReturnType<typeof vi.useFakeTimers>;

  beforeEach(() => {
    originalEventSource = globalThis.EventSource;
    MockEventSource.clearInstances();
    (globalThis as any).EventSource = MockEventSource;
    vi.useFakeTimers();
  });

  afterEach(() => {
    (globalThis as any).EventSource = originalEventSource;
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('connects to the run stream URL', () => {
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-123', {});
    expect(MockEventSource.lastInstance?.url).toBe('http://localhost:8000/api/v1/runs/run-123/stream');
    cleanup();
  });

  it('dispatches complete event and closes the connection', () => {
    const onComplete = vi.fn();
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-123', { onComplete });

    const es = MockEventSource.lastInstance!;
    es.emitMessage(JSON.stringify({ type: 'complete', status: 'success', run_id: 'run-123' }));

    expect(onComplete).toHaveBeenCalledWith({
      type: 'complete',
      status: 'success',
      run_id: 'run-123',
    });
    expect(es.closed).toBe(true);
    cleanup();
  });

  it('parses thought, tool_call, and progress events', () => {
    const onThought = vi.fn();
    const onToolCall = vi.fn();
    const onProgress = vi.fn();
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-1', { onThought, onToolCall, onProgress });

    const es = MockEventSource.lastInstance!;
    es.emitMessage(JSON.stringify({ type: 'thought', cycle: 1, text: 'Thinking...', timestamp: '2026-08-09T10:00:00Z' }));
    es.emitMessage(JSON.stringify({ type: 'tool_call', cycle: 1, tool: 'read_pdf', args: { page: 1 }, timestamp: '2026-08-09T10:00:01Z' }));
    es.emitMessage(JSON.stringify({ type: 'progress', completed_fields: 2, total_fields: 5, failing_fields: 0 }));

    expect(onThought).toHaveBeenCalledWith({ type: 'thought', cycle: 1, text: 'Thinking...', timestamp: '2026-08-09T10:00:00Z' });
    expect(onToolCall).toHaveBeenCalledWith({ type: 'tool_call', cycle: 1, tool: 'read_pdf', args: { page: 1 }, timestamp: '2026-08-09T10:00:01Z' });
    expect(onProgress).toHaveBeenCalledWith({ type: 'progress', completed_fields: 2, total_fields: 5, failing_fields: 0 });
    cleanup();
  });

  it('handles malformed JSON with console.error and does not crash', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-1', {});

    const es = MockEventSource.lastInstance!;
    expect(() => es.emitMessage('{invalid json')).not.toThrow();
    expect(consoleError).toHaveBeenCalled();
    cleanup();
  });

  it('ignores unknown event types', () => {
    const complete = vi.fn();
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-1', { onComplete: complete });

    const es = MockEventSource.lastInstance!;
    es.emitMessage(JSON.stringify({ type: 'unknown_event', some: 'data' }));

    expect(complete).not.toHaveBeenCalled();
    cleanup();
  });

  it('retries with exponential backoff capped at 4 attempts', () => {
    const onReconnecting = vi.fn();
    const onReconnectFailed = vi.fn();
    const onError = vi.fn();
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-1', { onReconnecting, onReconnectFailed, onError });

    // First error: retry 1, delay 2s
    MockEventSource.lastInstance!.emitError();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onReconnecting).toHaveBeenCalledWith(1, 2000);

    // Advance timers to trigger reconnection
    vi.advanceTimersByTime(2000);
    MockEventSource.lastInstance!.emitError();
    expect(onReconnecting).toHaveBeenCalledWith(2, 4000);

    vi.advanceTimersByTime(4000);
    MockEventSource.lastInstance!.emitError();
    expect(onReconnecting).toHaveBeenCalledWith(3, 8000);

    vi.advanceTimersByTime(8000);
    MockEventSource.lastInstance!.emitError();
    expect(onReconnecting).toHaveBeenCalledWith(4, 16000);

    // 5th error: capped, reconnect failed
    vi.advanceTimersByTime(16000);
    MockEventSource.lastInstance!.emitError();
    expect(onReconnectFailed).toHaveBeenCalledTimes(1);
    expect(onReconnecting).toHaveBeenCalledTimes(4);

    cleanup();
  });

  it('resets retry count on successful reconnect (open)', () => {
    const onReconnecting = vi.fn();
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-1', { onReconnecting });

    // Fail once then succeed
    MockEventSource.lastInstance!.emitError();
    vi.advanceTimersByTime(2000);
    expect(onReconnecting).toHaveBeenCalledTimes(1);

    MockEventSource.lastInstance!.emitOpen();
    MockEventSource.lastInstance!.emitError();
    vi.advanceTimersByTime(2000);
    expect(onReconnecting).toHaveBeenCalledTimes(2);
    expect(onReconnecting).toHaveBeenLastCalledWith(1, 2000); // reset to attempt 1

    cleanup();
  });

  it('manual cleanup closes connection, clears timeout, and prevents further reconnects', () => {
    const onReconnecting = vi.fn();
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-1', { onReconnecting });

    // Trigger an error that would schedule a reconnect
    MockEventSource.lastInstance!.emitError();
    expect(onReconnecting).toHaveBeenCalledTimes(1);

    // Clean up — should close and prevent future reconnects
    cleanup();
    vi.advanceTimersByTime(5000);

    // No new connection should have been made after cleanup
    expect(onReconnecting).toHaveBeenCalledTimes(1);
  });

  it('does not reconnect after complete event', () => {
    const onComplete = vi.fn();
    const onReconnecting = vi.fn();
    const { connectToRunStream } = require('@/lib/sse');
    const cleanup = connectToRunStream('run-1', { onComplete, onReconnecting });

    const es = MockEventSource.lastInstance!;
    es.emitMessage(JSON.stringify({ type: 'complete', status: 'success' }));
    // Now simulate an error — should not reconnect since isClosedManually was set
    es.emitError();

    vi.advanceTimersByTime(5000);
    expect(onReconnecting).not.toHaveBeenCalled();
    cleanup();
  });
});