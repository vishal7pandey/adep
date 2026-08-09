'use client';

import React, {
  useEffect,
  useState,
  useMemo,
  useCallback,
  useRef,
} from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine, Cell,
} from 'recharts';
import {
  BarChart3, TrendingUp, TrendingDown, Zap, DollarSign,
  CheckCircle2, XCircle, Download, RefreshCw,
  ChevronDown, AlertTriangle, Filter, Trophy, Activity,
  Clock, Target,
} from 'lucide-react';
import { fetchRecentRuns, ExtractionRun, fetchDefinitions, AgentDefinition, ApiError } from '@/lib/api';
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
  AnalyticsFilters,
} from '@/lib/analytics';

// ─────────────────────────────────────────────────────────
// Shared colour palette (matches design tokens)
// ─────────────────────────────────────────────────────────

const COLORS = {
  primary: '#0071CE',
  accent: '#00B5E2',
  success: '#4DB848',
  warning: '#F5BD1E',
  error: '#DC3545',
  purple: '#A27CC9',
  navy: '#00205C',
};

// ─────────────────────────────────────────────────────────
// Tooltip shared styles
// ─────────────────────────────────────────────────────────

const tooltipStyle = {
  backgroundColor: 'var(--card-bg)',
  border: '1px solid var(--card-border)',
  borderRadius: '8px',
  fontSize: '11px',
  color: 'var(--primary-text)',
};

// ─────────────────────────────────────────────────────────
// Stat Card
// ─────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

function StatCard({ label, value, sub, icon: Icon, trend, color = COLORS.primary }: StatCardProps) {
  return (
    <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-4 flex items-start gap-3 shadow-xs hover:shadow-sm transition-shadow">
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}18` }}
      >
        <Icon className="w-4.5 h-4.5" style={{ color }} />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] font-semibold text-muted uppercase tracking-wide">{label}</div>
        <div className="text-xl font-bold text-[var(--primary-text)] mt-0.5 leading-none">{value}</div>
        {sub && (
          <div className="flex items-center gap-1 mt-1 text-[10px] text-muted">
            {trend === 'up' && <TrendingUp className="w-3 h-3 text-[var(--status-success)]" />}
            {trend === 'down' && <TrendingDown className="w-3 h-3 text-[var(--status-error)]" />}
            <span>{sub}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Chart Card wrapper
// ─────────────────────────────────────────────────────────

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  icon?: React.ElementType;
  className?: string;
}

function ChartCard({ title, subtitle, children, icon: Icon, className = '' }: ChartCardProps) {
  return (
    <div className={`bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl shadow-xs overflow-hidden ${className}`}>
      <div className="px-5 py-3.5 border-b border-[var(--card-border)] flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-[var(--brand-primary)]" />}
        <div>
          <div className="text-sm font-semibold text-[var(--primary-text)]">{title}</div>
          {subtitle && <div className="text-[10px] text-muted">{subtitle}</div>}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Date range preset helper
// ─────────────────────────────────────────────────────────

type DatePreset = '7d' | '14d' | '30d' | '60d' | '90d';

function datePresetRange(preset: DatePreset): { from: Date; to: Date } {
  const to = new Date();
  const from = new Date();
  const days = preset === '7d' ? 7 : preset === '14d' ? 14 : preset === '30d' ? 30 : preset === '60d' ? 60 : 90;
  from.setDate(from.getDate() - days);
  return { from, to };
}

// ─────────────────────────────────────────────────────────
// Confidence heatmap colour helper
// ─────────────────────────────────────────────────────────

function failureRateColor(rate: number): string {
  if (rate >= 50) return COLORS.error;
  if (rate >= 25) return COLORS.warning;
  return COLORS.success;
}

// ─────────────────────────────────────────────────────────
// Main Analytics Page
// ─────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [allRuns, setAllRuns] = useState<ExtractionRun[]>([]);
  const [definitions, setDefinitions] = useState<AgentDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [datePreset, setDatePreset] = useState<DatePreset>('30d');
  const [selectedDefIds, setSelectedDefIds] = useState<string[]>([]);
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([]);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  const filterPanelRef = useRef<HTMLDivElement>(null);

  const filters: AnalyticsFilters = useMemo(
    () => ({
      dateRange: datePresetRange(datePreset),
      definitionIds: selectedDefIds,
      documentTypes: selectedDocTypes,
    }),
    [datePreset, selectedDefIds, selectedDocTypes],
  );

  const filteredRuns = useMemo(() => applyFilters(allRuns, filters), [allRuns, filters]);

  // Computed metrics
  const summary = useMemo(() => computeSummary(filteredRuns), [filteredRuns]);
  const successRateData = useMemo(() => computeSuccessRate(filteredRuns), [filteredRuns]);
  const confidenceByField = useMemo(() => computeConfidenceByField(filteredRuns), [filteredRuns]);
  const costTrend = useMemo(() => computeCostTrend(filteredRuns), [filteredRuns]);
  const processingHistogram = useMemo(() => computeProcessingTimeHistogram(filteredRuns), [filteredRuns]);
  const failureHeatmap = useMemo(() => computeFailureHeatmap(filteredRuns), [filteredRuns]);
  const agentLeaderboard = useMemo(() => {
    const nameMap: Record<string, string> = {};
    definitions.forEach((d) => { nameMap[d.id] = d.name; });
    return computeAgentLeaderboard(filteredRuns, nameMap);
  }, [filteredRuns, definitions]);

  const uniqueDefIds = useMemo(() => getUniqueDefinitionIds(allRuns), [allRuns]);
  const uniqueDocTypes = useMemo(() => getUniqueDocTypes(allRuns), [allRuns]);

  // Load data — uses `.then()` chaining so setState runs in async
  // callbacks, not synchronously in the effect body (matches the
  // pattern used by other pages and satisfies react-hooks rules).
  // `loading` is initialised to `true` so the spinner shows on first render.
  const applyResult = useCallback(
    (runs: ExtractionRun[], defs: AgentDefinition[], err: string | null) => {
      setAllRuns(runs);
      setDefinitions(defs);
      if (err) setError(err);
      setLoading(false);
    },
    [],
  );

  const fetchAnalytics = useCallback((): Promise<void> => {
    return Promise.all([
      fetchRecentRuns(200),
      fetchDefinitions().catch(() => [] as AgentDefinition[]),
    ])
      .then(([runs, defs]) => {
        applyResult(runs, defs, null);
      })
      .catch((err) => {
        const msg = err instanceof ApiError
          ? `API Error ${err.status}: ${err.message}`
          : 'Backend unreachable — unable to load analytics.';
        applyResult([], [], msg);
      });
  }, [applyResult]);

  useEffect(() => { fetchAnalytics(); }, [fetchAnalytics]);

  // Refresh handler — explicitly resets loading/error before re-fetching.
  const handleRefresh = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Close filter panel on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (filterPanelRef.current && !filterPanelRef.current.contains(e.target as Node)) {
        setShowFilterPanel(false);
      }
    }
    if (showFilterPanel) document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [showFilterPanel]);

  // CSV export
  const handleExportCsv = () => {
    const csv = exportToCsv(filteredRuns);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `adep-analytics-${datePreset}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // PDF export (print)
  const handleExportPdf = () => window.print();

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 bg-[var(--app-bg)]">
        <div className="w-8 h-8 border-3 border-[var(--brand-primary)] border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-muted">Loading analytics…</p>
      </div>
    );
  }

  // Empty state: no runs and no error — show a friendly prompt.
  if (allRuns.length === 0 && !error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] px-6 text-center">
        <BarChart3 className="w-12 h-12 text-[var(--brand-primary)] opacity-40" />
        <div>
          <h2 className="text-sm font-semibold text-[var(--primary-text)]">No runs yet</h2>
          <p className="text-xs text-muted mt-1">
            Run an extraction to see analytics.
          </p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--card-border)] bg-[var(--card-bg)] text-[11px] font-medium text-muted hover:text-[var(--primary-text)] transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>
    );
  }

  const DATE_PRESETS: { label: string; value: DatePreset }[] = [
    { label: '7 days', value: '7d' },
    { label: '14 days', value: '14d' },
    { label: '30 days', value: '30d' },
    { label: '60 days', value: '60d' },
    { label: '90 days', value: '90d' },
  ];

  const defIdToName: Record<string, string> = {};
  definitions.forEach((d) => { defIdToName[d.id] = d.name; });

  return (
    <div className="flex-1 overflow-y-auto bg-[var(--app-bg)] print:bg-white">
      {/* ── Page Header ─────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-[var(--app-bg)]/90 backdrop-blur border-b border-[var(--pane-border)] print:hidden">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <BarChart3 className="w-5 h-5 text-[var(--brand-primary)]" />
            <div>
              <h1 className="text-sm font-bold text-[var(--primary-text)]">Run Analytics</h1>
              <p className="text-[10px] text-muted">{filteredRuns.length} runs · {datePreset} window</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Date preset pills */}
            <div className="flex items-center gap-1 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-0.5">
              {DATE_PRESETS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setDatePreset(p.value)}
                  className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                    datePreset === p.value
                      ? 'bg-[var(--brand-primary)] text-white shadow-sm'
                      : 'text-muted hover:text-[var(--primary-text)]'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Filter button */}
            <div className="relative" ref={filterPanelRef}>
              <button
                onClick={() => setShowFilterPanel((v) => !v)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[11px] font-medium transition-all ${
                  selectedDefIds.length > 0 || selectedDocTypes.length > 0
                    ? 'bg-[var(--brand-primary-subtle)] border-[var(--brand-primary)] text-[var(--brand-primary)]'
                    : 'bg-[var(--card-bg)] border-[var(--card-border)] text-muted hover:text-[var(--primary-text)]'
                }`}
              >
                <Filter className="w-3.5 h-3.5" />
                Filters
                {(selectedDefIds.length + selectedDocTypes.length) > 0 && (
                  <span className="ml-0.5 w-4 h-4 rounded-full bg-[var(--brand-primary)] text-white text-[9px] flex items-center justify-center">
                    {selectedDefIds.length + selectedDocTypes.length}
                  </span>
                )}
                <ChevronDown className="w-3 h-3" />
              </button>

              {showFilterPanel && (
                <div className="absolute right-0 top-full mt-1.5 w-72 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl shadow-lg z-30 p-3 space-y-3 animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--primary-text)]">Filters</span>
                    <button
                      onClick={() => { setSelectedDefIds([]); setSelectedDocTypes([]); }}
                      className="text-[10px] text-[var(--brand-primary)] hover:underline"
                    >
                      Clear all
                    </button>
                  </div>

                  {/* Agent filter */}
                  <div>
                    <div className="text-[10px] font-bold text-muted uppercase tracking-wide mb-1.5">Agent Definition</div>
                    <div className="space-y-1">
                      {uniqueDefIds.map((id) => (
                        <label key={id} className="flex items-center gap-2 cursor-pointer group">
                          <input
                            type="checkbox"
                            className="rounded accent-[var(--brand-primary)]"
                            checked={selectedDefIds.includes(id)}
                            onChange={(e) =>
                              setSelectedDefIds((prev) =>
                                e.target.checked ? [...prev, id] : prev.filter((x) => x !== id),
                              )
                            }
                          />
                          <span className="text-xs text-[var(--primary-text)] group-hover:text-[var(--brand-primary)] truncate">
                            {defIdToName[id] ?? id}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Document type filter */}
                  <div>
                    <div className="text-[10px] font-bold text-muted uppercase tracking-wide mb-1.5">Document Type</div>
                    <div className="space-y-1">
                      {uniqueDocTypes.map((dt) => (
                        <label key={dt} className="flex items-center gap-2 cursor-pointer group">
                          <input
                            type="checkbox"
                            className="rounded accent-[var(--brand-primary)]"
                            checked={selectedDocTypes.includes(dt)}
                            onChange={(e) =>
                              setSelectedDocTypes((prev) =>
                                e.target.checked ? [...prev, dt] : prev.filter((x) => x !== dt),
                              )
                            }
                          />
                          <span className="text-xs text-[var(--primary-text)] group-hover:text-[var(--brand-primary)]">
                            {dt}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Export */}
            <div className="flex items-center gap-1">
              <button
                onClick={handleExportCsv}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--card-border)] bg-[var(--card-bg)] text-[11px] font-medium text-muted hover:text-[var(--primary-text)] transition-all"
              >
                <Download className="w-3.5 h-3.5" /> CSV
              </button>
              <button
                onClick={handleExportPdf}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--card-border)] bg-[var(--card-bg)] text-[11px] font-medium text-muted hover:text-[var(--primary-text)] transition-all"
              >
                <Download className="w-3.5 h-3.5" /> PDF
              </button>
              <button
                onClick={handleRefresh}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--card-border)] bg-[var(--card-bg)] text-[11px] font-medium text-muted hover:text-[var(--primary-text)] transition-all"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Error Banner ─────────────────────────────── */}
      {error && (
        <div className="max-w-[1400px] mx-auto px-6 pt-4 print:hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-[var(--status-warning-subtle)] border border-[var(--status-warning)]/40 rounded-lg text-xs text-[var(--status-warning)] font-medium">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            {error}
          </div>
        </div>
      )}

      <div className="max-w-[1400px] mx-auto px-6 py-5 space-y-6">

        {/* ── KPI Stat Cards ─────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          <StatCard label="Total Runs" value={summary.totalRuns} icon={Activity} color={COLORS.primary} />
          <StatCard label="Completed" value={summary.completedRuns} icon={CheckCircle2} color={COLORS.success} />
          <StatCard label="Failed / Stopped" value={summary.failedRuns} icon={XCircle} color={COLORS.error} />
          <StatCard
            label="Success Rate"
            value={`${summary.successRate}%`}
            icon={Target}
            color={summary.successRate >= 80 ? COLORS.success : summary.successRate >= 60 ? COLORS.warning : COLORS.error}
            trend={summary.successRate >= 80 ? 'up' : 'down'}
            sub="of all runs in window"
          />
          <StatCard
            label="Avg Confidence"
            value={`${summary.avgConfidence}%`}
            icon={Zap}
            color={COLORS.accent}
            sub="across all fields"
          />
          <StatCard
            label="Total Cost"
            value={`$${summary.totalCostUsd.toFixed(3)}`}
            icon={DollarSign}
            color={COLORS.purple}
            sub={`$${filteredRuns.length > 0 ? (summary.totalCostUsd / filteredRuns.length).toFixed(4) : '0'} avg/run`}
          />
          <StatCard
            label="Avg Cycles/Run"
            value={summary.avgCyclesPerRun}
            icon={Clock}
            color={COLORS.navy}
            sub="reasoning iterations"
          />
        </div>

        {/* ── Row 1: Success Rate + Cost Trend ────────── */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <ChartCard
            title="Extraction Success Rate"
            subtitle="% of completed runs per day"
            icon={TrendingUp}
          >
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={successRateData} margin={{ top: 4, right: 16, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit="%" />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v) => [`${Number(v)}%`, 'Success Rate']}
                />
                <ReferenceLine y={80} stroke={COLORS.success} strokeDasharray="4 2" opacity={0.5} />
                <Line
                  type="monotone"
                  dataKey="successRate"
                  stroke={COLORS.primary}
                  strokeWidth={2}
                  dot={{ fill: COLORS.primary, r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard
            title="Cost per Day"
            subtitle="USD spent on extraction runs"
            icon={DollarSign}
          >
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={costTrend} margin={{ top: 4, right: 16, left: -4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v.toFixed(2)}`} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v, name) => [
                    name === 'totalCostUsd' ? `$${Number(v).toFixed(4)}` : Number(v).toLocaleString(),
                    name === 'totalCostUsd' ? 'Cost (USD)' : 'Tokens',
                  ]}
                />
                <Legend iconSize={8} wrapperStyle={{ fontSize: 10 }} />
                <Line
                  type="monotone"
                  dataKey="totalCostUsd"
                  name="Cost (USD)"
                  stroke={COLORS.purple}
                  strokeWidth={2}
                  dot={{ fill: COLORS.purple, r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* ── Row 2: Confidence by Field + Histogram ─── */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <ChartCard
            title="Avg Confidence per Field"
            subtitle="Across all completed runs (lower = higher extraction risk)"
            icon={Target}
          >
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={confidenceByField} layout="vertical" margin={{ top: 0, right: 20, left: 60, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="field" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={70} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v) => [`${Number(v)}%`, 'Avg Confidence']}
                />
                <ReferenceLine x={85} stroke={COLORS.success} strokeDasharray="4 2" opacity={0.5} />
                <Bar dataKey="avgConfidence" radius={[0, 4, 4, 0]}
                  fill={COLORS.accent}
                  // Dynamic per-bar color based on confidence
                  label={false}
                >
                  {confidenceByField.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={
                        entry.avgConfidence >= 85 ? COLORS.success
                          : entry.avgConfidence >= 60 ? COLORS.accent
                          : COLORS.error
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard
            title="Processing Time Distribution"
            subtitle="Number of runs per processing duration bucket"
            icon={Clock}
          >
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={processingHistogram} margin={{ top: 4, right: 16, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" />
                <XAxis dataKey="bucketLabel" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => [Number(v), 'Runs']} />
                <Bar dataKey="count" name="Runs" fill={COLORS.primary} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* ── Row 3: Failure Heatmap + Agent Leaderboard */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

          {/* Failure Heatmap */}
          <ChartCard
            title="Field Failure Heatmap"
            subtitle="Which fields fail most across all runs"
            icon={AlertTriangle}
          >
            <div className="space-y-1.5">
              {failureHeatmap.slice(0, 10).map((cell) => (
                <div key={cell.field} className="flex items-center gap-3">
                  <div className="w-28 text-[11px] font-mono text-muted truncate shrink-0">{cell.field}</div>
                  <div className="flex-1 h-5 bg-[var(--surface-raised)] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${cell.failureRate}%`,
                        backgroundColor: failureRateColor(cell.failureRate),
                        opacity: 0.8,
                      }}
                    />
                  </div>
                  <div
                    className="w-10 text-right text-[11px] font-bold shrink-0"
                    style={{ color: failureRateColor(cell.failureRate) }}
                  >
                    {cell.failureRate}%
                  </div>
                  <div className="text-[10px] text-muted shrink-0">({cell.totalOccurrences})</div>
                </div>
              ))}
            </div>
            {failureHeatmap.length === 0 && (
              <p className="text-xs text-muted text-center py-4">No field data in selected range.</p>
            )}
          </ChartCard>

          {/* Agent Leaderboard */}
          <ChartCard
            title="Agent Leaderboard"
            subtitle="Performance comparison across agent definitions"
            icon={Trophy}
          >
            {agentLeaderboard.length === 0 ? (
              <p className="text-xs text-muted text-center py-4">No agents in selected range.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-[var(--card-border)]">
                      <th className="text-left pb-2 text-muted font-semibold text-[10px] uppercase tracking-wide">#</th>
                      <th className="text-left pb-2 text-muted font-semibold text-[10px] uppercase tracking-wide">Agent</th>
                      <th className="text-right pb-2 text-muted font-semibold text-[10px] uppercase tracking-wide">Runs</th>
                      <th className="text-right pb-2 text-muted font-semibold text-[10px] uppercase tracking-wide">Success</th>
                      <th className="text-right pb-2 text-muted font-semibold text-[10px] uppercase tracking-wide">Conf.</th>
                      <th className="text-right pb-2 text-muted font-semibold text-[10px] uppercase tracking-wide">Avg $</th>
                      <th className="text-right pb-2 text-muted font-semibold text-[10px] uppercase tracking-wide">Cycles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agentLeaderboard.map((row, idx) => (
                      <tr
                        key={row.definitionId}
                        className="border-b border-[var(--card-border)] last:border-0 hover:bg-[var(--hover-bg)] transition-colors"
                      >
                        <td className="py-2 pr-2 font-bold text-muted">
                          {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : idx + 1}
                        </td>
                        <td className="py-2 pr-3">
                          <div className="font-semibold text-[var(--primary-text)] truncate max-w-[120px]">{row.name}</div>
                          <div className="text-[9px] font-mono text-muted truncate">{row.definitionId}</div>
                        </td>
                        <td className="py-2 text-right font-mono">{row.totalRuns}</td>
                        <td className="py-2 text-right">
                          <span
                            className="font-bold"
                            style={{ color: row.successRate >= 80 ? COLORS.success : row.successRate >= 60 ? COLORS.warning : COLORS.error }}
                          >
                            {row.successRate}%
                          </span>
                        </td>
                        <td className="py-2 text-right font-mono text-muted">{row.avgConfidence}%</td>
                        <td className="py-2 text-right font-mono text-muted">${row.avgCostUsd}</td>
                        <td className="py-2 text-right font-mono text-muted">{row.avgCycles}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </ChartCard>
        </div>

        {/* ── Footer note ─────────────────────────────── */}
        <div className="text-center text-[10px] text-muted pb-4 print:hidden">
          Analytics computed client-side from run history · {filteredRuns.length} of {allRuns.length} total runs shown
        </div>
      </div>
    </div>
  );
}
