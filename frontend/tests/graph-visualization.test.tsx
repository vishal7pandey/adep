import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock ActiveHighlightContext
vi.mock('@/context/ActiveHighlightContext', () => ({
  useActiveHighlight: () => ({
    activeBBox: null,
    activeBBoxPage: null,
    activePage: 1,
    totalPages: 1,
    setActiveFieldId: vi.fn(),
    setActiveBBox: vi.fn(),
    setTotalPages: vi.fn(),
  }),
}));

// Mock LttsBadge to simplify assertions
vi.mock('@/components/ui/LttsBadge', () => ({
  LttsBadge: ({ children }: { children: React.ReactNode }) => (
    <span data-testid="ltts-badge">{children}</span>
  ),
}));

import { GraphVisualizationView, GraphNode, GraphEdge, SerializedOutput } from '@/components/workbench/GraphVisualizationView';

function makeNodes(): GraphNode[] {
  return [
    {
      id: 'n1',
      type: 'equipment',
      tag: 'P-101',
      class: 'Pump',
      confidence: 0.95,
      attributes: { capacity: '100 gpm' },
    },
  ];
}

function makeEdges(): GraphEdge[] {
  return [
    { id: 'e1', source: 'n1', target: 'n2', status: 'valid' },
  ];
}

describe('GraphVisualizationView [BLK-249]', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Smart P&ID JSON tab', () => {
    it('shows real smart_pid_json when provided', () => {
      const serializedOutput: SerializedOutput = {
        smart_pid_json: '{"nodes": [{"id": "P-101", "type": "pump"}]}',
      };

      render(
        <GraphVisualizationView
          nodes={makeNodes()}
          edges={makeEdges()}
          serializedOutput={serializedOutput}
        />
      );

      // Switch to Smart P&ID tab
      fireEvent.click(screen.getByText('Smart P&ID JSON'));

      expect(screen.getByText(/"nodes"/)).toBeInTheDocument();
      expect(screen.getByText(/P-101/)).toBeInTheDocument();
    });

    it('does not fabricate mock JSON when smart_pid_json is missing [BLK-249]', () => {
      const serializedOutput: SerializedOutput = {
        dexpi_xml: '<dexpi>some data</dexpi>',
      };

      render(
        <GraphVisualizationView
          nodes={makeNodes()}
          edges={makeEdges()}
          serializedOutput={serializedOutput}
        />
      );

      // Switch to Smart P&ID tab
      fireEvent.click(screen.getByText('Smart P&ID JSON'));

      // Should show empty-state message, not fabricated JSON
      expect(screen.getByText(/No Smart P&ID JSON data returned by backend/)).toBeInTheDocument();
      // Should NOT show fabricated JSON with "message" key
      expect(screen.queryByText(/"message"/)).not.toBeInTheDocument();
    });

    it('shows empty-state placeholder when smart_pid_json is empty string', () => {
      const serializedOutput: SerializedOutput = {
        smart_pid_json: '',
        dexpi_xml: '<dexpi>data</dexpi>',
      };

      render(
        <GraphVisualizationView
          nodes={makeNodes()}
          edges={makeEdges()}
          serializedOutput={serializedOutput}
        />
      );

      fireEvent.click(screen.getByText('Smart P&ID JSON'));

      expect(screen.getByText(/No Smart P&ID JSON data returned by backend/)).toBeInTheDocument();
    });

    it('shows empty-state when serializedOutput is entirely undefined', () => {
      render(
        <GraphVisualizationView
          nodes={makeNodes()}
          edges={makeEdges()}
        />
      );

      fireEvent.click(screen.getByText('Smart P&ID JSON'));

      expect(screen.getByText(/No Smart P&ID JSON data returned by backend/)).toBeInTheDocument();
    });
  });

  describe('DEXPI XML tab', () => {
    it('shows real DEXPI XML when provided', () => {
      const serializedOutput: SerializedOutput = {
        dexpi_xml: '<dexpi><equipment>P-101</equipment></dexpi>',
      };

      render(
        <GraphVisualizationView
          nodes={makeNodes()}
          edges={makeEdges()}
          serializedOutput={serializedOutput}
        />
      );

      fireEvent.click(screen.getByText('DEXPI XML'));

      expect(screen.getByText(/P-101/)).toBeInTheDocument();
    });

    it('shows fallback comment when DEXPI XML is missing', () => {
      const serializedOutput: SerializedOutput = {
        smart_pid_json: '{"data": true}',
      };

      render(
        <GraphVisualizationView
          nodes={makeNodes()}
          edges={makeEdges()}
          serializedOutput={serializedOutput}
        />
      );

      fireEvent.click(screen.getByText('DEXPI XML'));

      expect(screen.getByText(/No DEXPI XML data returned by backend/)).toBeInTheDocument();
    });
  });

  describe('empty state when no graph data at all', () => {
    it('shows no-data message when no nodes and no serialized output', () => {
      render(<GraphVisualizationView />);

      expect(screen.getByText('No Graph Topology Data Available')).toBeInTheDocument();
    });
  });
});
