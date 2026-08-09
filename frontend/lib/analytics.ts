/**
 * BLK-119 / BLK-166: Run Analytics — Client-side metric computation
 *
 * All metrics are derived from the /runs history array (ExtractionRun[]).
 * No backend aggregation endpoints are needed for v1.
 * No mock/demo data — charts show empty/zero when backend has no data.
 */

import { ExtractionRun } from './api';

// -----------------------------------------------------------------------
// Shared types consumed by the analytics page components
// -----------------------------------------------------------------------

export interface SuccessRatePoint {
  date: string; // "YYYY-MM-DD"
  successRate: number; // 0-100
  runs: number;
}

export interface ConfidenceByField {
  field: string;
  avgConfidence: number; // 0-100
  sampleCount: number;
}

export interface CostTrendPoint {
  date: string;
  totalCostUsd: number;
  estimatedTokens: number;
  docCount: number;
}

export interface ProcessingTimePoint {
  bucketLabel: string; // e.g. "0-5s", "5-10s"
  count: number;
}

export interface FailureHeatmapCell {
  field: string;
  failureRate: number; // 0-100
  totalOccurrences: number;
}

export interface AgentLeaderboardRow {
  definitionId: string;
  name: string;
  totalRuns: number;
  successRate: number;     // 0-100
  avgConfidence: number;   // 0-100
  avgCostUsd: number;
  avgCycles: number;
}

export interface AnalyticsFilters {
  dateRange: { from: Date; to: Date };
  definitionIds: string[];   // [] = all
  documentTypes: string[];   // [] = all
}

// -----------------------------------------------------------------------
// Internal helper: derive analytics metadata from real ExtractionRun
// fields populated by the backend (BLK-165).
// -----------------------------------------------------------------------

interface RunAnalyticsMeta {
  created_at: string;          // YYYY-MM-DD or ISO timestamp
  processing_time_ms: number;  // computed from started_at/completed_at
  cost_usd: number;            // from total_cost_usd
  estimated_tokens: number;    // from total_tokens
  document_type: string;       // derived from document_url
  definition_name: string;     // definition_id (name resolved by caller)
}

function toDateStr(ts?: string): string {
  if (!ts) return new Date().toISOString().split('T')[0];
  return ts.split('T')[0];
}

function computeProcessingTimeMs(run: ExtractionRun): number {
  if (run.started_at && run.completed_at) {
    const start = new Date(run.started_at).getTime();
    const end = new Date(run.completed_at).getTime();
    const ms = end - start;
    return ms > 0 ? ms : 0;
  }
  return 0;
}

function getMeta(run: ExtractionRun): RunAnalyticsMeta {
  return {
    created_at: toDateStr(run.created_at),
    processing_time_ms: computeProcessingTimeMs(run),
    cost_usd: run.total_cost_usd ?? 0,
    estimated_tokens: run.total_tokens ?? 0,
    document_type: run.document_url?.split('/').pop()?.split('.')[0] ?? 'unknown',
    definition_name: run.definition_id,
  };
}

// -----------------------------------------------------------------------
// Filter
// -----------------------------------------------------------------------

export function applyFilters(runs: ExtractionRun[], filters: AnalyticsFilters): ExtractionRun[] {
  return runs.filter((run) => {
    const meta = getMeta(run);
    const runDate = new Date(meta.created_at);
    if (runDate < filters.dateRange.from || runDate > filters.dateRange.to) return false;
    if (filters.definitionIds.length > 0 && !filters.definitionIds.includes(run.definition_id)) return false;
    if (filters.documentTypes.length > 0 && !filters.documentTypes.includes(meta.document_type)) return false;
    return true;
  });
}

// -----------------------------------------------------------------------
// Metric computations
// -----------------------------------------------------------------------

/** Group by date and compute success rate per day. */
export function computeSuccessRate(runs: ExtractionRun[]): SuccessRatePoint[] {
  const byDate: Record<string, { success: number; total: number }> = {};
  for (const run of runs) {
    const { created_at } = getMeta(run);
    if (!byDate[created_at]) byDate[created_at] = { success: 0, total: 0 };
    byDate[created_at].total++;
    if (run.status === 'completed') byDate[created_at].success++;
  }
  return Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, { success, total }]) => ({
      date,
      successRate: total > 0 ? Math.round((success / total) * 100) : 0,
      runs: total,
    }));
}

/** Average confidence per field name across all completed runs. */
export function computeConfidenceByField(runs: ExtractionRun[]): ConfidenceByField[] {
  const byField: Record<string, { sum: number; count: number }> = {};
  for (const run of runs.filter((r) => r.status === 'completed')) {
    for (const field of run.fields ?? []) {
      if (!byField[field.name]) byField[field.name] = { sum: 0, count: 0 };
      byField[field.name].sum += field.confidence;
      byField[field.name].count++;
    }
  }
  return Object.entries(byField)
    .map(([field, { sum, count }]) => ({
      field,
      avgConfidence: Math.round((sum / count) * 100),
      sampleCount: count,
    }))
    .sort((a, b) => a.avgConfidence - b.avgConfidence);
}

/** Cost per day with token breakdown. Filters runs with no cost data. */
export function computeCostTrend(runs: ExtractionRun[]): CostTrendPoint[] {
  const byDate: Record<string, { costSum: number; tokens: number; docs: number }> = {};
  for (const run of runs) {
    if (!run.total_cost_usd && !run.total_tokens) continue;
    const meta = getMeta(run);
    if (!byDate[meta.created_at]) byDate[meta.created_at] = { costSum: 0, tokens: 0, docs: 0 };
    byDate[meta.created_at].costSum += meta.cost_usd;
    byDate[meta.created_at].tokens += meta.estimated_tokens;
    byDate[meta.created_at].docs++;
  }
  return Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, { costSum, tokens, docs }]) => ({
      date,
      totalCostUsd: parseFloat(costSum.toFixed(4)),
      estimatedTokens: tokens,
      docCount: docs,
    }));
}

/** Processing time distribution in time buckets.
 * Computed from completed_at - started_at. Filters runs missing either timestamp. */
export function computeProcessingTimeHistogram(runs: ExtractionRun[]): ProcessingTimePoint[] {
  const buckets: Record<string, number> = {
    '0-5s': 0,
    '5-10s': 0,
    '10-20s': 0,
    '20-30s': 0,
    '30-45s': 0,
    '45-60s': 0,
    '>60s': 0,
  };
  for (const run of runs) {
    if (!run.started_at || !run.completed_at) continue;
    const { processing_time_ms } = getMeta(run);
    if (processing_time_ms <= 0) continue;
    const sec = processing_time_ms / 1000;
    if (sec < 5) buckets['0-5s']++;
    else if (sec < 10) buckets['5-10s']++;
    else if (sec < 20) buckets['10-20s']++;
    else if (sec < 30) buckets['20-30s']++;
    else if (sec < 45) buckets['30-45s']++;
    else if (sec < 60) buckets['45-60s']++;
    else buckets['>60s']++;
  }
  return Object.entries(buckets).map(([bucketLabel, count]) => ({ bucketLabel, count }));
}

/** Which fields fail most? Returns failure rate per field. */
export function computeFailureHeatmap(runs: ExtractionRun[]): FailureHeatmapCell[] {
  const byField: Record<string, { failed: number; total: number }> = {};
  for (const run of runs) {
    for (const field of run.fields ?? []) {
      if (!byField[field.name]) byField[field.name] = { failed: 0, total: 0 };
      byField[field.name].total++;
      if (field.status === 'failed' || field.status === 'low_confidence') byField[field.name].failed++;
    }
  }
  return Object.entries(byField)
    .map(([field, { failed, total }]) => ({
      field,
      failureRate: total > 0 ? Math.round((failed / total) * 100) : 0,
      totalOccurrences: total,
    }))
    .sort((a, b) => b.failureRate - a.failureRate);
}

/** Agent leaderboard across all definitions. */
export function computeAgentLeaderboard(
  runs: ExtractionRun[],
  nameMap: Record<string, string> = {},
): AgentLeaderboardRow[] {
  const byDef: Record<
    string,
    { success: number; total: number; confSum: number; confCount: number; costSum: number; cyclesSum: number }
  > = {};

  for (const run of runs) {
    const meta = getMeta(run);
    if (!byDef[run.definition_id]) {
      byDef[run.definition_id] = { success: 0, total: 0, confSum: 0, confCount: 0, costSum: 0, cyclesSum: 0 };
    }
    const entry = byDef[run.definition_id];
    entry.total++;
    if (run.status === 'completed') entry.success++;
    for (const f of run.fields ?? []) {
      entry.confSum += f.confidence;
      entry.confCount++;
    }
    entry.costSum += meta.cost_usd;
    entry.cyclesSum += run.current_cycle ?? 0;
  }

  return Object.entries(byDef)
    .map(([defId, e]) => ({
      definitionId: defId,
      name: nameMap[defId] ?? defId,
      totalRuns: e.total,
      successRate: e.total > 0 ? Math.round((e.success / e.total) * 100) : 0,
      avgConfidence: e.confCount > 0 ? Math.round((e.confSum / e.confCount) * 100) : 0,
      avgCostUsd: e.total > 0 ? parseFloat((e.costSum / e.total).toFixed(4)) : 0,
      avgCycles: e.total > 0 ? parseFloat((e.cyclesSum / e.total).toFixed(1)) : 0,
    }))
    .sort((a, b) => b.successRate - a.successRate);
}

/** Summary KPIs for the stat cards */
export interface AnalyticsSummary {
  totalRuns: number;
  successRate: number;
  avgConfidence: number;
  totalCostUsd: number;
  avgCyclesPerRun: number;
  completedRuns: number;
  failedRuns: number;
}

export function computeSummary(runs: ExtractionRun[]): AnalyticsSummary {
  const completed = runs.filter((r) => r.status === 'completed').length;
  const failed = runs.filter((r) => r.status === 'failed' || r.status === 'stopped').length;
  let confSum = 0, confCount = 0, costSum = 0, cyclesSum = 0;
  for (const run of runs) {
    const meta = getMeta(run);
    costSum += meta.cost_usd;
    cyclesSum += run.current_cycle ?? 0;
    for (const f of run.fields ?? []) {
      confSum += f.confidence;
      confCount++;
    }
  }
  return {
    totalRuns: runs.length,
    successRate: runs.length > 0 ? Math.round((completed / runs.length) * 100) : 0,
    avgConfidence: confCount > 0 ? Math.round((confSum / confCount) * 100) : 0,
    totalCostUsd: parseFloat(costSum.toFixed(4)),
    avgCyclesPerRun: runs.length > 0 ? parseFloat((cyclesSum / runs.length).toFixed(1)) : 0,
    completedRuns: completed,
    failedRuns: failed,
  };
}

/** Unique definition IDs present in the run set */
export function getUniqueDefinitionIds(runs: ExtractionRun[]): string[] {
  return [...new Set(runs.map((r) => r.definition_id))];
}

/** Unique document types present in the run set */
export function getUniqueDocTypes(runs: ExtractionRun[]): string[] {
  return [...new Set(runs.map((r) => getMeta(r).document_type))];
}

/** Export analytics data to CSV string */
export function exportToCsv(runs: ExtractionRun[]): string {
  const header = 'run_id,definition_id,status,created_at,processing_time_ms,cost_usd,estimated_tokens,total_fields,extracted_fields,current_cycle';
  const rows = runs.map((run) => {
    const meta = getMeta(run);
    return [
      run.id,
      run.definition_id,
      run.status,
      meta.created_at,
      meta.processing_time_ms,
      meta.cost_usd,
      meta.estimated_tokens,
      run.total_fields,
      run.extracted_fields_count,
      run.current_cycle,
    ].join(',');
  });
  return [header, ...rows].join('\n');
}
