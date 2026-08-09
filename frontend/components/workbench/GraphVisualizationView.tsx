'use client';

import React, { useState } from 'react';
import {
  Network,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Circle,
  Eye,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { AdeBadge } from '@/components/ui/AdeBadge';
import { useActiveHighlight } from '@/context/ActiveHighlightContext';

export interface GraphNode {
  id: string;
  type: 'equipment' | 'valve' | 'instrument' | 'pipe';
  tag: string;
  class: string;
  confidence: number;
  bbox?: { x: number; y: number; width: number; height: number; page?: number };
  attributes: Record<string, string>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  line_number?: string;
  pipe_spec?: string;
  status: 'valid' | 'warning';
}

export interface TopologyRule {
  id: string;
  rule: string;
  status: 'pass' | 'violation';
  details: string;
}

export interface SerializedOutput {
  dexpi_xml?: string;
  smart_pid_json?: string;
  graphml?: string;
}

export interface GraphVisualizationViewProps {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  topologyRules?: TopologyRule[];
  serializedOutput?: SerializedOutput;
  isLoading?: boolean;
}

export const GraphVisualizationView: React.FC<GraphVisualizationViewProps> = ({
  nodes = [],
  edges = [],
  topologyRules = [],
  serializedOutput,
  isLoading = false,
}) => {
  const [activeTab, setActiveTab] = useState<'graph' | 'dexpi' | 'smart_pid' | 'graphml'>('graph');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(nodes[0]?.id ?? null);
  const [showTopologyPanel, setShowTopologyPanel] = useState(true);

  const { setActiveFieldId, setActiveBBox } = useActiveHighlight();

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? nodes[0] ?? null;

  const handleSelectNode = (node: GraphNode) => {
    setSelectedNodeId(node.id);
    if (node.bbox) {
      setActiveFieldId(node.id);
      setActiveBBox(node.bbox);
    }
  };

  const hasGraphData =
    nodes.length > 0 ||
    Boolean(serializedOutput?.dexpi_xml) ||
    Boolean(serializedOutput?.smart_pid_json) ||
    Boolean(serializedOutput?.graphml);

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-3 bg-[var(--pane-bg)]">
        <div className="w-8 h-8 border-3 border-[var(--brand-primary)] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-muted">Processing topology graph output…</p>
      </div>
    );
  }

  if (!hasGraphData) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-3 bg-[var(--pane-bg)]">
        <div className="w-12 h-12 rounded-2xl bg-[var(--brand-primary-subtle)] text-[var(--brand-primary)] flex items-center justify-center">
          <Network className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h4 className="font-bold text-sm text-[var(--primary-text)]">No Graph Topology Data Available</h4>
          <p className="text-xs text-muted max-w-sm">
            This run produced no P&amp;ID graph topology or DEXPI XML data. Execute a P&amp;ID extraction run on a diagram to extract equipment nodes and piping relationships.
          </p>
        </div>
      </div>
    );
  }

  const dexpiContent =
    serializedOutput?.dexpi_xml || '<!-- No DEXPI XML data available for this run -->';
  const smartPidContent =
    serializedOutput?.smart_pid_json ||
    (nodes.length > 0
      ? JSON.stringify({ nodes, edges, topology_rules: topologyRules }, null, 2)
      : '{\n  "message": "No Smart P&ID JSON data available"\n}');
  const graphmlContent =
    serializedOutput?.graphml || '<!-- No GraphML data available for this run -->';

  const passedRulesCount = topologyRules.filter((r) => r.status === 'pass').length;

  return (
    <div className="h-full flex flex-col bg-[var(--pane-bg)] space-y-3">
      {/* Top Header & Tab Controls */}
      <div className="flex items-center justify-between border-b border-[var(--pane-border)] pb-2.5">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-[var(--brand-primary)]" />
          <h3 className="font-bold text-xs text-[var(--primary-text)]">P&amp;ID Topology Graph</h3>
          <AdeBadge variant="verified">
            {nodes.length} Nodes · {edges.length} Edges
          </AdeBadge>
        </div>

        {/* View Toggles */}
        <div className="flex items-center bg-black/10 dark:bg-white/10 p-0.5 rounded-lg text-[11px] font-medium">
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTab === 'graph' ? 'bg-[var(--brand-primary)] text-white font-bold' : 'text-muted'
            }`}
          >
            Graph View
          </button>
          <button
            onClick={() => setActiveTab('dexpi')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTab === 'dexpi' ? 'bg-[var(--brand-primary)] text-white font-bold' : 'text-muted'
            }`}
          >
            DEXPI XML
          </button>
          <button
            onClick={() => setActiveTab('smart_pid')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTab === 'smart_pid' ? 'bg-[var(--brand-primary)] text-white font-bold' : 'text-muted'
            }`}
          >
            Smart P&amp;ID JSON
          </button>
          <button
            onClick={() => setActiveTab('graphml')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTab === 'graphml' ? 'bg-[var(--brand-primary)] text-white font-bold' : 'text-muted'
            }`}
          >
            GraphML
          </button>
        </div>
      </div>

      {/* Main Tab Content Area */}
      {activeTab === 'graph' ? (
        <div className="flex-1 flex flex-col space-y-3 min-h-0">
          {/* Interactive Node-Link Graph Visualizer Canvas */}
          <div className="relative flex-1 rounded-xl border border-[var(--card-border)] bg-black/5 dark:bg-black/40 p-4 overflow-hidden flex items-center justify-center">
            {nodes.length === 0 ? (
              <div className="text-center text-xs text-muted">No graph nodes extracted</div>
            ) : (
              <div className="w-full h-full relative flex items-center justify-around px-8 flex-wrap gap-4 overflow-auto">
                {nodes.map((node) => {
                  const isSelected = selectedNode?.id === node.id;
                  return (
                    <div
                      key={node.id}
                      onClick={() => handleSelectNode(node)}
                      className={`relative p-3.5 rounded-xl border-2 cursor-pointer transition-all duration-200 shadow-md hover:scale-105 flex flex-col items-center space-y-1.5 ${
                        isSelected
                          ? 'border-[var(--brand-accent)] ring-4 ring-[var(--brand-accent)]/30 bg-[var(--brand-primary-subtle)] scale-105'
                          : 'border-[var(--card-border)] bg-[var(--card-bg)] hover:border-[var(--brand-primary)]'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        {node.type === 'equipment' && <Cpu className="w-4 h-4 text-[var(--brand-primary)]" />}
                        {node.type === 'valve' && <Network className="w-4 h-4 text-[var(--status-warning)]" />}
                        {node.type === 'instrument' && <Circle className="w-4 h-4 text-[var(--brand-accent)]" />}
                        <span className="font-mono text-xs font-bold text-[var(--primary-text)]">{node.tag || node.id}</span>
                      </div>

                      <span className="text-[10px] text-muted font-medium">{node.class}</span>

                      <AdeBadge variant={node.confidence > 0.9 ? 'verified' : 'medium'}>
                        {Math.round(node.confidence * 100)}% Conf
                      </AdeBadge>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Selected Node Inspector Panel */}
          {selectedNode && (
            <div className="p-3.5 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-2 text-xs animate-fadeIn">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-[var(--primary-text)]">{selectedNode.tag || selectedNode.id}</span>
                  <AdeBadge variant="info">{selectedNode.class}</AdeBadge>
                </div>
                {selectedNode.bbox && (
                  <button
                    onClick={() => handleSelectNode(selectedNode)}
                    className="flex items-center gap-1 text-[11px] text-[var(--brand-primary)] hover:underline font-semibold"
                  >
                    <Eye className="w-3.5 h-3.5" /> Highlight in Pane 3
                  </button>
                )}
              </div>

              {Object.keys(selectedNode.attributes || {}).length > 0 ? (
                <div className="grid grid-cols-3 gap-2 pt-1 border-t border-[var(--pane-border)] text-[11px]">
                  {Object.entries(selectedNode.attributes).map(([key, val]) => (
                    <div key={key} className="p-1.5 rounded bg-black/5 dark:bg-white/5 font-mono">
                      <span className="text-muted block text-[9px] uppercase">{key}</span>
                      <span className="font-bold text-[var(--primary-text)]">{String(val)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-muted italic pt-1 border-t border-[var(--pane-border)]">
                  No attributes extracted for this node.
                </p>
              )}
            </div>
          )}

          {/* Topology Rules Validation Collapsible Panel */}
          <div className="p-3 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-2 text-xs">
            <div
              onClick={() => setShowTopologyPanel(!showTopologyPanel)}
              className="flex items-center justify-between cursor-pointer select-none"
            >
              <div className="flex items-center gap-2 font-bold text-[var(--primary-text)]">
                <ShieldCheck className="w-4 h-4 text-[var(--status-success)]" />
                <span>Topology Rules Validation</span>
              </div>
              <AdeBadge variant={topologyRules.length > 0 ? 'verified' : 'info'}>
                {topologyRules.length > 0 ? `${passedRulesCount}/${topologyRules.length} Rules Passed` : '0 Rules Evaluated'}
              </AdeBadge>
            </div>

            {showTopologyPanel && (
              <div className="space-y-1.5 pt-1 border-t border-[var(--pane-border)]">
                {topologyRules.length === 0 ? (
                  <p className="text-[11px] text-muted italic p-1.5">No topology validation rules executed for this run.</p>
                ) : (
                  topologyRules.map((r) => (
                    <div key={r.id} className="flex items-center justify-between text-[11px] p-1.5 rounded bg-black/5 dark:bg-white/5">
                      <div className="flex items-center gap-2">
                        {r.status === 'pass' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-[var(--status-success)] shrink-0" />
                        ) : (
                          <AlertTriangle className="w-3.5 h-3.5 text-[var(--status-warning)] shrink-0" />
                        )}
                        <span className="font-medium text-[var(--primary-text)]">{r.rule}</span>
                      </div>
                      <span className="text-muted text-[10px] font-mono">{r.details}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Code View Tabs (DEXPI, Smart P&ID, GraphML) */
        <div className="flex-1 rounded-xl border border-[var(--card-border)] bg-black/10 dark:bg-black/50 p-3 overflow-auto font-mono text-xs text-[var(--primary-text)]">
          <pre className="p-2 whitespace-pre-wrap">
            {activeTab === 'dexpi' && dexpiContent}
            {activeTab === 'smart_pid' && smartPidContent}
            {activeTab === 'graphml' && graphmlContent}
          </pre>
        </div>
      )}
    </div>
  );
};
