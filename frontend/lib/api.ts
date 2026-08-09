export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export interface BBoxModel {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ExtractedField {
  id: string;
  name: string;
  value: string | number | boolean | null;
  confidence: number;
  bbox?: BBoxModel | null;
  page?: number;
  status: 'verified' | 'low_confidence' | 'failed' | 'extracted';
}

export interface ProbeStep {
  id?: string;
  rationale: string;
  action: string;
}

export interface InvariantSpec {
  id?: string;
  fieldName: string;
  type: string;
  params: string;
}

export interface FailureActionSpec {
  id?: string;
  condition: string;
  action: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  semantic_checks_enabled?: boolean;
  semantic_prompt?: string;
  tools?: string[];
  system_prompt?: string;
  probe_order?: ProbeStep[];
  invariants?: InvariantSpec[];
  failure_actions?: FailureActionSpec[];
}

export interface FieldSchema {
  name: string;
  type: string;
  description: string;
  required: boolean;
  confidence_threshold?: number;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  fields: FieldSchema[];
}

export interface AgentDefinition {
  id: string;
  name: string;
  skill_id: string;
  template_id: string;
  task_type?: string;
  skill_ref?: string;
  template_ref?: string;
  system_prompt?: string;
  max_iterations?: number;
}

export interface GraphNodeData {
  id: string;
  type: 'equipment' | 'valve' | 'instrument' | 'pipe';
  tag: string;
  class: string;
  confidence: number;
  bbox?: { x: number; y: number; width: number; height: number; page?: number };
  attributes: Record<string, string>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  line_number?: string;
  pipe_spec?: string;
  status: 'valid' | 'warning';
}

export interface TopologyRuleData {
  id: string;
  rule: string;
  status: 'pass' | 'violation';
  details: string;
}

export interface SerializedGraphOutput {
  dexpi_xml?: string;
  smart_pid_json?: string;
  graphml?: string;
  nodes?: GraphNodeData[];
  edges?: GraphEdgeData[];
  topology_rules?: TopologyRuleData[];
}

export interface ExtractionRun {
  id: string;
  definition_id: string;
  document_url: string;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'stopped';
  current_cycle: number;
  total_fields: number;
  extracted_fields_count: number;
  fields: ExtractedField[];
  task_type?: string;
  serialized_output?: SerializedGraphOutput;
  // New from BLK-165 (populated by backend, optional until deployed):
  total_cost_usd?: number;
  total_tokens?: number;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface UploadDocumentResponse {
  document_id: string;
  original_filename: string;
  format: string;
  total_pages: number;
  page_dimensions: Array<{ width: number; height: number }>;
  page_paths: string[];
  thumbnail: string;
  created_at: string;
}

export interface DocumentMetadata {
  document_id: string;
  original_filename: string;
  format: string;
  total_pages: number;
  page_dimensions: Array<{ width: number; height: number }>;
  page_paths: string[];
  thumbnail: string;
  created_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const headers = { ...getAuthHeaders(), ...init.headers };
  return fetch(url, { ...init, headers });
}

/**
 * Wraps unknown catch errors into ApiError with status 0 (network error).
 * All API functions use this pattern: succeed with real data or throw.
 * No fabricated data. No silent fallbacks.
 */
/**
 * BLK-135: Security & Key Storage Note:
 * Reads API Key from sessionStorage for current browser tab context.
 * Note: Neither sessionStorage nor localStorage is fully immune to XSS;
 * httpOnly cookies are the long-term production target when backend session layer lands.
 */
export function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const apiKey = sessionStorage.getItem('adep_api_key');
  return apiKey ? { Authorization: `Bearer ${apiKey}` } : {};
}

export interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at?: string;
  status: 'active' | 'revoked';
}

export interface AgentPrediction {
  document_type: string;
  confidence: number;
  reasoning: string;
  suggested_definition_id: string;
}

export interface AgentSuggestionResult {
  predictions: AgentPrediction[];
  page_count: number;
  is_multi_type: boolean;
}

export async function suggestAgent(documentId: string): Promise<AgentSuggestionResult> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/documents/${documentId}/suggest-agent`, {
      method: 'POST',
    });
    if (!res.ok) {
      throw new ApiError(`Failed to classify document`, res.status);
    }
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

function rethrowAsApiError(err: unknown): never {
  if (err instanceof ApiError) throw err;
  throw new ApiError(
    `Network error: ${err instanceof Error ? err.message : 'Unknown error'}`,
    0,
  );
}

// --- Definitions ---

export async function fetchDefinitions(): Promise<AgentDefinition[]> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/definitions`);
    if (!res.ok) throw new ApiError(`Failed to fetch definitions: ${res.statusText}`, res.status);
    const defs: AgentDefinition[] = await res.json();
    const byName = new Map<string, AgentDefinition>();
    for (const def of defs) {
      const key = def.name.trim().toLowerCase();
      const existing = byName.get(key);
      if (!existing) {
        byName.set(key, def);
        continue;
      }
      if (existing.id === 'def-pnid-to-dexpi' && def.id === 'def-pid-to-dexpi') {
        byName.set(key, def);
      }
    }
    return Array.from(byName.values());
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function fetchDefinition(id: string): Promise<AgentDefinition | null> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/definitions/${id}`);
    if (res.status === 404) return null;
    if (!res.ok) throw new ApiError(`Failed to fetch definition: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function createDefinition(data: Omit<AgentDefinition, 'id'>): Promise<AgentDefinition> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/definitions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...data,
        skill_ref: data.skill_id || data.skill_ref,
        template_ref: data.template_id || data.template_ref,
      }),
    });
    if (!res.ok) throw new ApiError(`Failed to create definition: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function updateDefinition(
  id: string,
  data: Partial<AgentDefinition>
): Promise<AgentDefinition> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/definitions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new ApiError(`Failed to update definition: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function deleteDefinition(id: string): Promise<void> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/definitions/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok && res.status !== 204) throw new ApiError(`Failed to delete definition: ${res.statusText}`, res.status);
  } catch (err) {
    rethrowAsApiError(err);
  }
}

// --- Skills ---

export async function fetchSkills(): Promise<Skill[]> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/skills`);
    if (!res.ok) throw new ApiError(`Failed to fetch skills: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function createSkill(data: Omit<Skill, 'id'>): Promise<Skill> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/skills`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new ApiError(`Failed to create skill: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function updateSkill(
  id: string,
  data: Partial<Skill>
): Promise<Skill> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/skills/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new ApiError(`Failed to update skill: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function deleteSkill(id: string): Promise<void> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/skills/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok && res.status !== 204) throw new ApiError(`Failed to delete skill: ${res.statusText}`, res.status);
  } catch (err) {
    rethrowAsApiError(err);
  }
}

// --- Templates ---

export async function fetchTemplates(): Promise<Template[]> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/templates`);
    if (!res.ok) throw new ApiError(`Failed to fetch templates: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function createTemplate(data: Omit<Template, 'id'>): Promise<Template> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new ApiError(`Failed to create template: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

// --- AI Template Composer (BLK-067) ---

/** Response shape from POST /templates/generate */
export interface GeneratedTemplate {
  name: string;
  fields: FieldSchema[];
}

/**
 * Generate a template schema from a natural language description.
 * Calls the backend AI Template Composer (BLK-070).
 */
export async function generateTemplate(description: string): Promise<GeneratedTemplate> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/templates/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    });
    if (!res.ok) throw new ApiError(`Failed to generate template: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

// --- Extraction Runs ---

export async function startExtractionRun(definitionId: string, documentUrl: string): Promise<ExtractionRun> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ definition_id: definitionId, document_url: documentUrl }),
    });
    if (res.status === 429) {
      const retryAfter = res.headers.get('Retry-After') || '5';
      throw new ApiError(`Server busy. Worker pool full. Retry in ${retryAfter}s`, 429);
    }
    if (!res.ok && res.status !== 202) throw new ApiError(`Failed to start extraction run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

// --- Run Control ---

export async function compactRun(runId: string): Promise<{ status: string; compacted: boolean }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/compact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new ApiError(`Failed to compact run context: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function pauseRun(runId: string): Promise<{ run_id: string; paused: boolean; cycle: number; message: string }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/pause`, { method: 'POST' });
    if (!res.ok && res.status !== 202) throw new ApiError(`Failed to pause run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function resumeRun(runId: string): Promise<{ run_id: string; resumed: boolean; cycle: number; message: string }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/resume`, { method: 'POST' });
    if (!res.ok && res.status !== 202) throw new ApiError(`Failed to resume run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function stopRun(runId: string): Promise<{ run_id: string; stopped: boolean; cycle: number; partial_result: ExtractedField[]; message: string }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/stop`, { method: 'POST' });
    if (!res.ok && res.status !== 202) throw new ApiError(`Failed to stop run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function approveRun(runId: string): Promise<{ run_id: string; approved: boolean; message: string }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/approve`, { method: 'POST' });
    if (!res.ok && res.status !== 202) throw new ApiError(`Failed to approve run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function rejectRun(runId: string, reason?: string): Promise<{ run_id: string; rejected: boolean; message: string }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason || 'User rejected high-risk tool execution' }),
    });
    if (!res.ok && res.status !== 202) throw new ApiError(`Failed to reject run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function rollbackRun(runId: string, toCycle: number): Promise<{ run_id: string; rolled_back: boolean; from_cycle: number; to_cycle: number; attempted_preserved: boolean; message: string }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to_cycle: toCycle }),
    });
    if (!res.ok) throw new ApiError(`Failed to rollback run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

// --- Run Management ---

export async function fetchRecentRuns(limit: number = 20): Promise<ExtractionRun[]> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs?limit=${limit}`);
    if (!res.ok) throw new ApiError(`Failed to fetch recent runs: ${res.statusText}`, res.status);
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function fetchRun(runId: string): Promise<ExtractionRun> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}`);
    if (!res.ok) throw new ApiError(`Failed to fetch run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function uploadDocument(file: File): Promise<UploadDocumentResponse> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiFetch(`${API_BASE_URL}/documents`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new ApiError(`Failed to upload document: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function fetchDocument(documentId: string): Promise<DocumentMetadata> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/documents/${encodeURIComponent(documentId)}`);
    if (!res.ok) throw new ApiError(`Failed to fetch document: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function deleteRun(runId: string): Promise<{ deleted: boolean }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}`, { method: 'DELETE' });
    if (!res.ok) throw new ApiError(`Failed to delete run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function renameRun(runId: string, newName: string): Promise<{ id: string; name: string }> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName }),
    });
    if (!res.ok) throw new ApiError(`Failed to rename run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function duplicateRun(runId: string): Promise<ExtractionRun> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/duplicate`, { method: 'POST' });
    if (!res.ok) throw new ApiError(`Failed to duplicate run: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

// --- Export Endpoints (BLK-133) ---

export async function exportRunJSON(runId: string): Promise<Blob> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/export/json`);
    if (!res.ok) throw new ApiError(`Failed to export run as JSON: ${res.statusText}`, res.status);
    return await res.blob();
  } catch (err) {
    rethrowAsApiError(err);
  }
}

export async function exportRunCSV(runId: string): Promise<Blob> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/runs/${runId}/export/csv`);
    if (!res.ok) throw new ApiError(`Failed to export run as CSV: ${res.statusText}`, res.status);
    return await res.blob();
  } catch (err) {
    rethrowAsApiError(err);
  }
}
