import React, { ReactNode, useState, useEffect } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock the API and SSE modules before importing components
vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    fetchRun: vi.fn(),
    exportRunJSON: vi.fn(),
    exportRunCSV: vi.fn(),
  };
});

vi.mock('@/lib/sse', () => ({
  connectToRunStream: vi.fn(() => () => {}),
}));

// Mock GraphVisualizationView to avoid heavy deps
vi.mock('@/components/workbench/GraphVisualizationView', () => ({
  GraphVisualizationView: () => <div data-testid="graph-view">Graph View</div>,
}));

import { Pane2ExtractedData } from '@/components/workbench/Pane2ExtractedData';
import { Pane3DocumentViewer } from '@/components/workbench/Pane3DocumentViewer';
import { WorkbenchProvider, useWorkbench } from '@/context/WorkbenchContext';
import { ActiveHighlightProvider } from '@/context/ActiveHighlightContext';
import { fetchRun, ExtractedField, ExtractionRun } from '@/lib/api';

function AllProviders({ children }: { children: ReactNode }) {
  return (
    <WorkbenchProvider>
      <ActiveHighlightProvider>{children}</ActiveHighlightProvider>
    </WorkbenchProvider>
  );
}

// Helper: uses a ref to trigger context setters once on mount
// without wrapping in act() (which causes React 19 issues in effects)
function ExtractionSetup({ children }: { children: ReactNode }) {
  const { setDocument, startRun } = useWorkbench();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setDocument('invoice.pdf', 'doc-1');
    startRun('run-1');
    setReady(true);
  }, [setDocument, startRun]);
  if (!ready) return null;
  return <>{children}</>;
}

function makeField(overrides: Partial<ExtractedField> = {}): ExtractedField {
  return {
    id: 'f1',
    name: 'invoice_number',
    value: 'INV-001',
    confidence: 0.95,
    status: 'verified',
    ...overrides,
  };
}

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
    ...overrides,
  };
}

// Render Panes in extraction phase
function renderInExtraction() {
  return render(
    <AllProviders>
      <ExtractionSetup>
        <Pane2ExtractedData />
        <Pane3DocumentViewer />
      </ExtractionSetup>
    </AllProviders>
  );
}

beforeEach(() => {
  vi.mocked(fetchRun).mockReset();
  // Default: fetchRun resolves a completed run with no fields
  vi.mocked(fetchRun).mockResolvedValue(makeRun({}));
  // URL.createObjectURL is not available in jsdom
  Object.defineProperty(URL, 'createObjectURL', {
    writable: true,
    value: vi.fn(() => 'blob:mock'),
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    writable: true,
    value: vi.fn(),
  });
  Object.defineProperty(HTMLAnchorElement.prototype, 'click', {
    writable: true,
    value: vi.fn(),
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('Pane2ExtractedData', () => {
  it('renders the header', () => {
    renderInExtraction();
    expect(screen.getByText('Extracted Data')).toBeInTheDocument();
  });

  it('fetches and renders fields from a completed run (happy path)', async () => {
    const fields = [
      makeField({ id: 'f1', name: 'invoice_number', value: 'INV-001', confidence: 0.95, status: 'verified' }),
      makeField({ id: 'f2', name: 'amount', value: 250.5, confidence: 0.8, status: 'extracted' }),
    ];
    vi.mocked(fetchRun).mockResolvedValueOnce(
      makeRun({ task_type: 'standard_extraction', fields })
    );

    renderInExtraction();

    // Wait for fetch to resolve and state to update
    await screen.findByText('INV-001');
    expect(screen.getByText('invoice_number')).toBeInTheDocument();
    expect(screen.getByText('250.5')).toBeInTheDocument();
    expect(screen.getByText('95% Confidence')).toBeInTheDocument();
    expect(screen.getByText('80% Confidence')).toBeInTheDocument();
  });

  it('shows field cards with verified count badge', async () => {
    const fields = [
      makeField({ id: 'f1', name: 'invoice_number', value: 'INV-001', confidence: 0.95, status: 'verified' }),
      makeField({ id: 'f2', name: 'amount', value: '100', confidence: 0.5, status: 'low_confidence' }),
    ];
    vi.mocked(fetchRun).mockResolvedValueOnce(
      makeRun({ task_type: 'standard_extraction', fields })
    );

    renderInExtraction();

    await screen.findByText('INV-001');
    // "1/2 Verified" badge
    expect(screen.getByText('1/2 Verified')).toBeInTheDocument();
  });

  it('displays error state when fetchRun fails', async () => {
    vi.mocked(fetchRun).mockRejectedValueOnce(new Error('Backend unreachable'));

    renderInExtraction();

    await screen.findByText('Backend Unreachable');
  });
});

describe('Pane3DocumentViewer', () => {
  it('shows no document loaded state when no document', () => {
    render(
      <AllProviders>
        <Pane3DocumentViewer />
      </AllProviders>
    );
    expect(screen.getByText('No document loaded')).toBeInTheDocument();
  });

  it('renders document name when document is set', async () => {
    renderInExtraction();

    // The document is loaded through ExtractionSetup
    expect(await screen.findByText('invoice.pdf')).toBeInTheDocument();
  });
});
