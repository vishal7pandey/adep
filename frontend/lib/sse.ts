import { BBoxModel, ExtractedField } from './api';

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
  cycle: number;
  reason: string;
  required_action: string;
}

export interface SSECompleteEvent {
  type: 'complete';
  status: 'success' | 'failed' | 'cancelled' | 'max_iterations_reached';
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
  onComplete?: (event: SSECompleteEvent) => void;
  onError?: (error: Event) => void;
  onReconnecting?: (attempt: number, delayMs: number) => void;
  onReconnectFailed?: () => void;
}

export function connectToRunStream(
  runId: string,
  callbacks: SSEClientCallbacks
): () => void {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
  const url = `${API_BASE_URL}/runs/${runId}/stream`;

  let eventSource: EventSource | null = null;
  let isClosedManually = false;
  let retryCount = 0;
  let retryTimeout: NodeJS.Timeout | null = null;

  const connect = () => {
    if (isClosedManually) return;

    eventSource = new EventSource(url);

    eventSource.onopen = () => {
      retryCount = 0;
    };

    eventSource.onmessage = (e) => {
      try {
        const data: SSEEvent = JSON.parse(e.data);
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
          case 'complete':
            callbacks.onComplete?.(data);
            isClosedManually = true;
            eventSource?.close();
            break;
        }
      } catch (err) {
        console.error('[ADEP SSE Parse Error]', err);
      }
    };

    eventSource.onerror = (err) => {
      callbacks.onError?.(err);
      if (isClosedManually) return;

      eventSource?.close();

      if (retryCount < 4) {
        retryCount++;
        const backoffMs = Math.pow(2, retryCount) * 1000; // 2s, 4s, 8s, 16s
        callbacks.onReconnecting?.(retryCount, backoffMs);
        retryTimeout = setTimeout(() => {
          connect();
        }, backoffMs);
      } else {
        callbacks.onReconnectFailed?.();
      }
    };
  };

  connect();

  return () => {
    isClosedManually = true;
    if (retryTimeout) clearTimeout(retryTimeout);
    eventSource?.close();
  };
}
