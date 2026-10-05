import { BBoxModel, ExtractedField, getAuthHeaders, RunStatus } from './api';

export interface SSEThoughtEvent {
  type: 'thought';
  cycle: number;
  text: string;
  timestamp: string;
}

export interface SSEToolCallEvent {
  type: 'tool_call';
  cycle: number;
  tool: string;
  args: Record<string, unknown>;
  timestamp: string;
}

export interface SSEToolResultEvent {
  type: 'tool_result';
  cycle: number;
  tool: string;
  result: Record<string, unknown>;
  crop_thumbnail?: string | null;
  timestamp: string;
}

export interface SSEProgressEvent {
  type: 'progress';
  completed_fields: number;
  total_fields: number;
  failing_fields: number;
}

export interface SSEFieldUpdateEvent {
  type: 'field_update';
  field: ExtractedField;
}

export interface SSECompactionEvent {
  type: 'compaction';
  entries_compacted: number;
  summary_length: number;
  timestamp: string;
}

export interface SSEPausedEvent {
  type: 'paused';
  cycle: number;
}

export interface SSEResumedEvent {
  type: 'resumed';
  cycle: number;
}

export interface SSEStoppedEvent {
  type: 'stopped';
  cycle: number;
  partial_result: ExtractedField[] | null;
}

export interface SSERolledBackEvent {
  type: 'rolled_back';
  from_cycle: number;
  to_cycle: number;
}

export interface SSETrajectoryWarningEvent {
  type: 'trajectory_warning';
  cycle: number;
  message: string;
}

export interface SSETrajectoryCriticalEvent {
  type: 'trajectory_critical';
  cycle: number;
  message: string;
}

export interface SSEGateTriggeredEvent {
  type: 'gate_triggered';
  field: string;
  risk_tier: string;
  confidence: number;
  reason: string;
  cycle: number;
  required_action: string;
}

export interface SSEStatusChangeEvent {
  type: 'status_change';
  status: RunStatus;
  cycle: number;
  previous_status?: string | null;
}

export interface SSECompleteEvent {
  type: 'complete';
  status: RunStatus;
  summary?: string;
  run_id?: string;
}

export type SSEEvent =
  | SSEThoughtEvent
  | SSEToolCallEvent
  | SSEToolResultEvent
  | SSEProgressEvent
  | SSEFieldUpdateEvent
  | SSECompactionEvent
  | SSEPausedEvent
  | SSEResumedEvent
  | SSEStoppedEvent
  | SSERolledBackEvent
  | SSETrajectoryWarningEvent
  | SSETrajectoryCriticalEvent
  | SSEGateTriggeredEvent
  | SSEStatusChangeEvent
  | SSECompleteEvent;

export interface SSEClientCallbacks {
  onThought?: (event: SSEThoughtEvent) => void;
  onToolCall?: (event: SSEToolCallEvent) => void;
  onToolResult?: (event: SSEToolResultEvent) => void;
  onProgress?: (event: SSEProgressEvent) => void;
  onFieldUpdate?: (event: SSEFieldUpdateEvent) => void;
  onCompaction?: (event: SSECompactionEvent) => void;
  onPaused?: (event: SSEPausedEvent) => void;
  onResumed?: (event: SSEResumedEvent) => void;
  onStopped?: (event: SSEStoppedEvent) => void;
  onRolledBack?: (event: SSERolledBackEvent) => void;
  onTrajectoryWarning?: (event: SSETrajectoryWarningEvent) => void;
  onTrajectoryCritical?: (event: SSETrajectoryCriticalEvent) => void;
  onGateTriggered?: (event: SSEGateTriggeredEvent) => void;
  onStatusChange?: (event: SSEStatusChangeEvent) => void;
  onComplete?: (event: SSECompleteEvent) => void;
  onError?: (error: Event) => void;
  onReconnecting?: (attempt: number, delayMs: number) => void;
  onReconnectFailed?: () => void;
}

function dispatchSSEEvent(data: SSEEvent, callbacks: SSEClientCallbacks) {
  switch (data.type) {
    case 'thought':
      callbacks.onThought?.(data);
      break;
    case 'tool_call':
      callbacks.onToolCall?.(data);
      break;
    case 'tool_result':
      callbacks.onToolResult?.(data);
      break;
    case 'progress':
      callbacks.onProgress?.(data);
      break;
    case 'field_update':
      callbacks.onFieldUpdate?.(data);
      break;
    case 'compaction':
      callbacks.onCompaction?.(data);
      break;
    case 'paused':
      callbacks.onPaused?.(data);
      break;
    case 'resumed':
      callbacks.onResumed?.(data);
      break;
    case 'stopped':
      callbacks.onStopped?.(data);
      break;
    case 'rolled_back':
      callbacks.onRolledBack?.(data);
      break;
    case 'trajectory_warning':
      callbacks.onTrajectoryWarning?.(data);
      break;
    case 'trajectory_critical':
      callbacks.onTrajectoryCritical?.(data);
      break;
    case 'gate_triggered':
      callbacks.onGateTriggered?.(data);
      break;
    case 'status_change':
      callbacks.onStatusChange?.(data);
      break;
    case 'complete':
      callbacks.onComplete?.(data);
      break;
  }
}

export function connectToRunStream(
  runId: string,
  callbacks: SSEClientCallbacks
): () => void {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
  const url = `${API_BASE_URL}/runs/${runId}/stream`;

  let isClosedManually = false;
  let retryCount = 0;
  let retryTimeout: NodeJS.Timeout | null = null;
  let currentController: AbortController | null = null;

  const connect = async () => {
    if (isClosedManually) return;

    currentController = new AbortController();
    const headers = { ...getAuthHeaders(), Accept: 'text/event-stream' };

    try {
      const response = await fetch(url, {
        headers,
        signal: currentController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body received for SSE stream');
      }

      retryCount = 0;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (!isClosedManually) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';

        for (const block of blocks) {
          const lines = block.split('\n');
          const dataLine = lines.find((l) => l.startsWith('data: '));
          if (!dataLine) continue;
          const jsonStr = dataLine.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const data: SSEEvent = JSON.parse(jsonStr);
            dispatchSSEEvent(data, callbacks);
            if (data.type === 'complete') {
              isClosedManually = true;
              currentController.abort();
            }
          } catch (err) {
            console.error('[ADEP SSE Parse Error]', err);
          }
        }
      }
    } catch (err: unknown) {
      if (isClosedManually || (err instanceof Error && err.name === 'AbortError')) {
        return;
      }
      callbacks.onError?.(err as Event);

      if (retryCount < 4) {
        retryCount++;
        const backoffMs = Math.pow(2, retryCount) * 1000;
        callbacks.onReconnecting?.(retryCount, backoffMs);
        retryTimeout = setTimeout(() => {
          connect();
        }, backoffMs);
      } else {
        callbacks.onReconnectFailed?.();
      }
    }
  };

  connect();

  return () => {
    isClosedManually = true;
    if (retryTimeout) clearTimeout(retryTimeout);
    if (currentController) currentController.abort();
  };
}
