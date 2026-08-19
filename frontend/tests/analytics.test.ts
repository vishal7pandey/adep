import { describe, it, expect } from 'vitest';
import {
  applyFilters,
  computeSuccessRate,
  computeConfidenceByField,
  computeCostTrend,
  computeProcessingTimeHistogram,
  computeFailureHeatmap,
  computeAgentLeaderboard,
  computeSummary,
  getUniqueDefinitionIds,
  getUniqueDocTypes,
  exportToCsv,
} from '@/lib/analytics';
import { ExtractionRun } from '@/lib/api';

function makeRun(overrides: Partial<ExtractionRun> = {}): ExtractionRun {
  return {
    id: 'run-1',
    definition_id: 'def-1',
    document_url: '/docs/invoice.pdf',
    status: 'completed',
    current_cycle: 3,
    total_fields: 2,
    extracted_fields_count: 2,
    fields: [],
    created_at: '2026-08-01T10:00:00+05:30',
    ...overrides,
  };
}

describe('applyFilters', () => {
  const runs = [
    makeRun({ id: 'r1', definition_id: 'def-1', document_url: '/docs/invoice.pdf', created_at: '2026-08-01T00:00:00Z' }),
    makeRun({ id: 'r2', definition_id: 'def-2', document_url: '/docs/po.pdf', created_at: '2026-08-15T00:00:00Z' }),
    makeRun({ id: 'r3', definition_id: 'def-1', document_url: '/docs/po.pdf', created_at: '2026-07-01T00:00:00Z' }),
  ];

  it('filters by date range inclusive', () => {
    const result = applyFilters(runs, {
      dateRange: { from: new Date('2026-08-01T00:00:00Z'), to: new Date('2026-08-31T23:59:59Z') },
      definitionIds: [],
      documentTypes: [],
    });
    expect(result.map((r) => r.id)).toEqual(['r1', 'r2']);
  });

  it('filters by definition ids', () => {
    const result = applyFilters(runs, {
      dateRange: { from: new Date('2026-01-01'), to: new Date('2026-12-31') },
      definitionIds: ['def-2'],
      documentTypes: [],
    });
    expect(result.map((r) => r.id)).toEqual(['r2']);
  });

  it('filters by document type derived from URL', () => {
    const result = applyFilters(runs, {
      dateRange: { from: new Date('2026-01-01'), to: new Date('2026-12-31') },
      definitionIds: [],
      documentTypes: ['po'],
    });
    expect(result.map((r) => r.id)).toEqual(['r2', 'r3']);
  });

  it('returns all runs when filters are empty', () => {
    const result = applyFilters(runs, {
      dateRange: { from: new Date('2026-01-01'), to: new Date('2026-12-31') },
      definitionIds: [],
      documentTypes: [],
    });
    expect(result).toHaveLength(3);
  });

  it('includes runs on the boundary day (from date) [BLK-247]', () => {
    const boundaryRuns = [
      makeRun({ id: 'b1', created_at: '2026-08-01T00:00:00Z' }),
      makeRun({ id: 'b2', created_at: '2026-08-01T23:59:59Z' }),
      makeRun({ id: 'b3', created_at: '2026-08-15T12:00:00Z' }),
    ];
    const result = applyFilters(boundaryRuns, {
      dateRange: { from: new Date('2026-08-01'), to: new Date('2026-08-31') },
      definitionIds: [],
      documentTypes: [],
    });
    expect(result.map((r) => r.id)).toEqual(['b1', 'b2', 'b3']);
  });

  it('includes runs on the boundary day (to date) [BLK-247]', () => {
    const boundaryRuns = [
      makeRun({ id: 'b1', created_at: '2026-08-31T00:00:00Z' }),
      makeRun({ id: 'b2', created_at: '2026-08-31T23:59:59Z' }),
      makeRun({ id: 'b3', created_at: '2026-09-01T00:00:00Z' }),
    ];
    const result = applyFilters(boundaryRuns, {
      dateRange: { from: new Date('2026-08-01'), to: new Date('2026-08-31') },
      definitionIds: [],
      documentTypes: [],
    });
    expect(result.map((r) => r.id)).toEqual(['b1', 'b2']);
  });

  it('includes runs when from and to are the same day [BLK-247]', () => {
    const sameDayRuns = [
      makeRun({ id: 's1', created_at: '2026-08-15T00:00:00Z' }),
      makeRun({ id: 's2', created_at: '2026-08-15T12:00:00Z' }),
      makeRun({ id: 's3', created_at: '2026-08-16T00:00:00Z' }),
    ];
    const result = applyFilters(sameDayRuns, {
      dateRange: { from: new Date('2026-08-15'), to: new Date('2026-08-15') },
      definitionIds: [],
      documentTypes: [],
    });
    expect(result.map((r) => r.id)).toEqual(['s1', 's2']);
  });
});

describe('computeSuccessRate', () => {
  it('groups by date and computes success rate', () => {
    const runs = [
      makeRun({ id: 'r1', status: 'completed', created_at: '2026-08-01T00:00:00Z' }),
      makeRun({ id: 'r2', status: 'completed', created_at: '2026-08-01T01:00:00Z' }),
      makeRun({ id: 'r3', status: 'failed', created_at: '2026-08-01T02:00:00Z' }),
      makeRun({ id: 'r4', status: 'completed', created_at: '2026-08-02T00:00:00Z' }),
    ];
    const result = computeSuccessRate(runs);
    expect(result).toEqual([
      { date: '2026-08-01', successRate: 67, runs: 3 },
      { date: '2026-08-02', successRate: 100, runs: 1 },
    ]);
  });

  it('returns empty array for no runs', () => {
    expect(computeSuccessRate([])).toEqual([]);
  });

  it('returns 0 success rate when no completions', () => {
    const runs = [makeRun({ status: 'failed' }), makeRun({ status: 'cancelled' })];
    const result = computeSuccessRate(runs);
    expect(result[0].successRate).toBe(0);
  });
});

describe('computeConfidenceByField', () => {
  it('averages confidence per field across completed runs only', () => {
    const runs = [
      makeRun({
        status: 'completed',
        fields: [
          { id: 'f1', name: 'invoice_number', value: 'INV-1', confidence: 0.9, status: 'verified' },
          { id: 'f2', name: 'amount', value: 100, confidence: 0.8, status: 'extracted' },
        ],
      }),
      makeRun({
        status: 'completed',
        fields: [
          { id: 'f3', name: 'invoice_number', value: 'INV-2', confidence: 0.7, status: 'verified' },
        ],
      }),
      makeRun({
        status: 'failed',
        fields: [
          { id: 'f4', name: 'invoice_number', value: null, confidence: 0.1, status: 'failed' },
        ],
      }),
    ];
    const result = computeConfidenceByField(runs);
    const invoiceField = result.find((r) => r.field === 'invoice_number');
    const amountField = result.find((r) => r.field === 'amount');

    expect(invoiceField).toEqual({ field: 'invoice_number', avgConfidence: 80, sampleCount: 2 });
    expect(amountField).toEqual({ field: 'amount', avgConfidence: 80, sampleCount: 1 });
  });

  it('sorts by ascending confidence', () => {
    const runs = [
      makeRun({
        status: 'completed',
        fields: [
          { id: 'f1', name: 'low', value: 'a', confidence: 0.5, status: 'extracted' },
          { id: 'f2', name: 'high', value: 'b', confidence: 0.9, status: 'extracted' },
        ],
      }),
    ];
    const result = computeConfidenceByField(runs);
    expect(result[0].field).toBe('low');
    expect(result[1].field).toBe('high');
  });
});

describe('computeCostTrend', () => {
  it('groups cost by date, skipping runs with no cost data', () => {
    const runs = [
      makeRun({ id: 'r1', total_cost_usd: 0.5, total_tokens: 5000, created_at: '2026-08-01T00:00:00Z' }),
      makeRun({ id: 'r2', total_cost_usd: 0.25, total_tokens: 2500, created_at: '2026-08-01T01:00:00Z' }),
      makeRun({ id: 'r3', total_cost_usd: 0, total_tokens: 0, created_at: '2026-08-02T00:00:00Z' }),
    ];
    const result = computeCostTrend(runs);
    expect(result).toEqual([
      { date: '2026-08-01', totalCostUsd: 0.75, estimatedTokens: 7500, docCount: 2 },
    ]);
  });
});

describe('computeProcessingTimeHistogram', () => {
  it('buckets runs by processing time', () => {
    const runs = [
      makeRun({ started_at: '2026-08-01T00:00:00Z', completed_at: '2026-08-01T00:00:02Z' }), // 2s
      makeRun({ started_at: '2026-08-01T00:00:00Z', completed_at: '2026-08-01T00:00:07Z' }), // 7s
      makeRun({ started_at: '2026-08-01T00:00:00Z', completed_at: '2026-08-01T00:00:40Z' }), // 40s
      makeRun({}), // missing timestamps - skipped
    ];
    const result = computeProcessingTimeHistogram(runs);
    const byBucket = Object.fromEntries(result.map((r) => [r.bucketLabel, r.count]));
    expect(byBucket['0-5s']).toBe(1);
    expect(byBucket['5-10s']).toBe(1);
    expect(byBucket['30-45s']).toBe(1);
    expect(byBucket['>60s']).toBe(0);
  });

  it('handles zero processing time (invalid)', () => {
    const runs = [
      makeRun({ started_at: '2026-08-01T00:00:00Z', completed_at: '2026-08-01T00:00:00Z' }),
    ];
    const result = computeProcessingTimeHistogram(runs);
    const total = result.reduce((sum, r) => sum + r.count, 0);
    expect(total).toBe(0);
  });
});

describe('computeFailureHeatmap', () => {
  it('computes failure rate per field, sorted desc', () => {
    const runs = [
      makeRun({
        fields: [
          { id: 'f1', name: 'a', value: null, confidence: 0, status: 'failed' },
          { id: 'f2', name: 'a', value: 'x', confidence: 0.9, status: 'verified' },
          { id: 'f3', name: 'b', value: 'y', confidence: 0.8, status: 'extracted' },
          { id: 'f4', name: 'b', value: null, confidence: 0.2, status: 'low_confidence' },
        ],
      }),
    ];
    const result = computeFailureHeatmap(runs);
    expect(result[0]).toEqual({ field: 'a', failureRate: 50, totalOccurrences: 2 });
    expect(result[1]).toEqual({ field: 'b', failureRate: 50, totalOccurrences: 2 });
  });
});

describe('computeAgentLeaderboard', () => {
  it('aggregates per definition and sorts by success rate', () => {
    const runs = [
      makeRun({
        id: 'r1', definition_id: 'def-1', status: 'completed', current_cycle: 2,
        total_cost_usd: 0.1, fields: [{ id: 'f1', name: 'x', value: 'a', confidence: 0.9, status: 'verified' }],
      }),
      makeRun({
        id: 'r2', definition_id: 'def-1', status: 'failed', current_cycle: 1,
        total_cost_usd: 0.05, fields: [],
      }),
      makeRun({
        id: 'r3', definition_id: 'def-2', status: 'completed', current_cycle: 3,
        total_cost_usd: 0.2, fields: [{ id: 'f2', name: 'x', value: 'b', confidence: 0.8, status: 'verified' }],
      }),
    ];
    const result = computeAgentLeaderboard(runs, { 'def-1': 'Def One', 'def-2': 'Def Two' });
    expect(result).toHaveLength(2);
    expect(result[0].definitionId).toBe('def-2'); // 100% success
    expect(result[0].name).toBe('Def Two');
    expect(result[0].successRate).toBe(100);
    expect(result[0].avgConfidence).toBe(80);
    expect(result[0].avgCostUsd).toBe(0.2);
    expect(result[0].avgCycles).toBe(3);
    expect(result[1].definitionId).toBe('def-1');
    expect(result[1].successRate).toBe(50);
    expect(result[1].avgConfidence).toBe(90);
    expect(result[1].avgCostUsd).toBe(0.075);
  });
});

describe('computeSummary', () => {
  it('computes KPI summary', () => {
    const runs = [
      makeRun({ status: 'completed', current_cycle: 2, total_cost_usd: 0.5, fields: [{ id: 'f1', name: 'x', value: 'a', confidence: 1, status: 'verified' }] }),
      makeRun({ status: 'failed', current_cycle: 1, total_cost_usd: 0.25, fields: [] }),
      makeRun({ status: 'cancelled', current_cycle: 3, total_cost_usd: 0.1, fields: [] }),
    ];
    const result = computeSummary(runs);
    expect(result.totalRuns).toBe(3);
    expect(result.successRate).toBe(33);
    expect(result.avgConfidence).toBe(100);
    expect(result.totalCostUsd).toBe(0.85);
    expect(result.avgCyclesPerRun).toBe(2);
    expect(result.completedRuns).toBe(1);
    expect(result.failedRuns).toBe(2);
  });

  it('handles empty runs', () => {
    const result = computeSummary([]);
    expect(result.totalRuns).toBe(0);
    expect(result.successRate).toBe(0);
    expect(result.avgConfidence).toBe(0);
    expect(result.totalCostUsd).toBe(0);
    expect(result.avgCyclesPerRun).toBe(0);
  });
});

describe('getUniqueDefinitionIds', () => {
  it('returns unique definition ids', () => {
    const runs = [
      makeRun({ definition_id: 'def-1' }),
      makeRun({ definition_id: 'def-2' }),
      makeRun({ definition_id: 'def-1' }),
    ];
    expect(getUniqueDefinitionIds(runs)).toEqual(['def-1', 'def-2']);
  });
});

describe('getUniqueDocTypes', () => {
  it('returns unique document types from URLs', () => {
    const runs = [
      makeRun({ document_url: '/docs/invoice.pdf' }),
      makeRun({ document_url: '/docs/po.pdf' }),
      makeRun({ document_url: '/docs/invoice.pdf' }),
      makeRun({ document_url: '/unknown/file' }),
    ];
    const docTypes = getUniqueDocTypes(runs);
    expect(docTypes).toContain('invoice');
    expect(docTypes).toContain('po');
    expect(docTypes).toContain('file');
  });
});

describe('exportToCsv', () => {
  it('exports CSV with header and rows', () => {
    const runs = [makeRun({ id: 'r1', total_cost_usd: 0.5, total_tokens: 100, current_cycle: 2 })];
    const csv = exportToCsv(runs);
    const lines = csv.split('\n');
    expect(lines[0]).toBe('run_id,definition_id,status,created_at,processing_time_ms,cost_usd,estimated_tokens,total_fields,extracted_fields,current_cycle');
    expect(lines[1]).toContain('r1');
    expect(lines[1]).toContain('0.5');
    expect(lines[1]).toContain('2');
  });
});