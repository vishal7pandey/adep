import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ApiError,
  fetchDefinitions,
  fetchSkills,
  fetchTemplates,
  pauseRun,
  resumeRun,
  stopRun,
  rollbackRun,
  compactRun,
  fetchRun,
  fetchRecentRuns,
  startExtractionRun,
} from '@/lib/api';

describe('API Client', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  // --- fetchDefinitions + dedupe logic (BLK-246: `def-pid-to-dexpi` removal) ---

  describe('fetchDefinitions', () => {
    it('fetches definitions and dedupes pnid/pid duplicate by name', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => [
          { id: 'def-pnid-to-dexpi', name: 'P&ID to DEXPI' },
          { id: 'def-pid-to-dexpi', name: 'P&ID to DEXPI' },
          { id: 'def-invoice', name: 'Invoice' },
        ],
      });

      const defs = await fetchDefinitions();
      // The pnid variant should be replaced by the pid variant (same name)
      expect(defs).toHaveLength(2);
      const pnid = defs.find((d) => d.id === 'def-pnid-to-dexpi');
      const pid = defs.find((d) => d.id === 'def-pid-to-dexpi');
      expect(pnid).toBeUndefined();
      expect(pid).toBeDefined();
    });

    it('keeps both if names differ even with the special ids', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => [
          { id: 'def-pnid-to-dexpi', name: 'PNID Definition' },
          { id: 'def-pid-to-dexpi', name: 'P&ID to DEXPI' },
        ],
      });

      const defs = await fetchDefinitions();
      expect(defs).toHaveLength(2);
    });

    it('dedupes same-name definitions keeping the first occurrence', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => [
          { id: 'def-1', name: 'Invoice' },
          { id: 'def-2', name: 'Invoice' },
        ],
      });

      const defs = await fetchDefinitions();
      expect(defs).toHaveLength(1);
      expect(defs[0].id).toBe('def-1');
    });

    it('throws ApiError on server error', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      });

      await expect(fetchDefinitions()).rejects.toThrow(ApiError);
    });

    it('throws ApiError on network failure', async () => {
      fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));
      await expect(fetchDefinitions()).rejects.toThrow(ApiError);
    });
  });

  // --- fetchSkills ---

  describe('fetchSkills', () => {
    it('fetches skills successfully', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => [{ id: 'skill-1', name: 'OCR' }],
      });

      const skills = await fetchSkills();
      expect(skills).toHaveLength(1);
      expect(skills[0].name).toBe('OCR');
    });

    it('throws ApiError when server is unreachable (mock, offline)', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'));
      await expect(fetchSkills()).rejects.toThrow(ApiError);
    });
  });

  // --- fetchTemplates ---

  describe('fetchTemplates', () => {
    it('fetches templates successfully', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => [{ id: 't-1', name: 'Invoice Template' }],
      });

      const templates = await fetchTemplates();
      expect(templates).toHaveLength(1);
    });

    it('throws ApiError on failure', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'));
      await expect(fetchTemplates()).rejects.toThrow(ApiError);
    });
  });

  // --- Run control actions (mock, deterministic — this is what BLK-246 requires) ---

  describe('run control actions', () => {
    it('pauseRun succeeds with 202', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 202,
        statusText: 'Accepted',
        json: async () => ({ run_id: 'run-1', paused: true, cycle: 2, message: 'paused' }),
      });

      const result = await pauseRun('run-1');
      expect(result.paused).toBe(true);
    });

    it('resumeRun succeeds', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 202,
        statusText: 'Accepted',
        json: async () => ({ run_id: 'run-1', resumed: true, cycle: 2, message: 'resumed' }),
      });

      const result = await resumeRun('run-1');
      expect(result.resumed).toBe(true);
    });

    it('stopRun succeeds', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 202,
        statusText: 'Accepted',
        json: async () => ({ run_id: 'run-1', stopped: true, cycle: 3, partial_result: [], message: 'stopped' }),
      });

      const result = await stopRun('run-1');
      expect(result.stopped).toBe(true);
    });

    it('rollbackRun posts to_cycle in body', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ run_id: 'run-1', rolled_back: true, from_cycle: 3, to_cycle: 2, attempted_preserved: true, message: 'rolled back' }),
      });

      const result = await rollbackRun('run-1', 2);
      expect(result.rolled_back).toBe(true);
      // Verify the request body contains to_cycle
      const [, init] = fetchMock.mock.calls[0];
      expect(JSON.parse((init as RequestInit).body as string)).toEqual({ to_cycle: 2 });
    });

    it('compactRun succeeds', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ status: 'compacted', compacted: true }),
      });

      const result = await compactRun('run-1');
      expect(result.compacted).toBe(true);
    });

    it('startExtractionRun handles rate limit (429)', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers({ 'Retry-After': '10' }),
        json: async () => ({}),
      });

      await expect(startExtractionRun('def-1', 'doc.pdf')).rejects.toThrow(
        'Server busy. Worker pool full. Retry in 10s'
      );
    });

    it('startExtractionRun succeeds with 202', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 202,
        statusText: 'Accepted',
        json: async () => ({ id: 'run-1', definition_id: 'def-1', status: 'running', current_cycle: 0, total_fields: 0, extracted_fields_count: 0, fields: [] }),
      });

      const run = await startExtractionRun('def-1', 'doc.pdf');
      expect(run.id).toBe('run-1');
      expect(run.status).toBe('running');
    });

    it('fetchRun returns run data', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ id: 'run-1', definition_id: 'def-1', status: 'completed', current_cycle: 1, total_fields: 1, extracted_fields_count: 1, fields: [] }),
      });

      const run = await fetchRun('run-1');
      expect(run.id).toBe('run-1');
      expect(run.status).toBe('completed');
    });

    it('fetchRecentRuns handles array response', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => [
          { id: 'run-1', definition_id: 'def-1', status: 'completed', current_cycle: 1, total_fields: 1, extracted_fields_count: 1, fields: [] },
          { id: 'run-2', definition_id: 'def-1', status: 'failed', current_cycle: 1, total_fields: 1, extracted_fields_count: 0, fields: [] },
        ],
      });

      const runs = await fetchRecentRuns(10);
      expect(runs).toHaveLength(2);
    });

    it('fetchRecentRuns handles items envelope response', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ items: [{ id: 'run-1', definition_id: 'def-1', status: 'running', current_cycle: 0, total_fields: 0, extracted_fields_count: 0, fields: [] }] }),
      });

      const runs = await fetchRecentRuns(10);
      expect(runs).toHaveLength(1);
    });
  });
});
