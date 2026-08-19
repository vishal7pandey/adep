import React, { ReactNode, useEffect } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

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

vi.mock('@/components/workbench/GraphVisualizationView', () => ({
  GraphVisualizationView: () => <div data-testid="graph-view">Graph View</div>,
}));

import { Pane3DocumentViewer } from '@/components/workbench/Pane3DocumentViewer';
import { WorkbenchProvider, useWorkbench } from '@/context/WorkbenchContext';
import { ActiveHighlightProvider, useActiveHighlight } from '@/context/ActiveHighlightContext';
import { fetchRun, ExtractedField, ExtractionRun } from '@/lib/api';

function AllProviders({ children }: { children: ReactNode }) {
  return (
    <WorkbenchProvider>
      <ActiveHighlightProvider>{children}</ActiveHighlightProvider>
    </WorkbenchProvider>
  );
}

function DocSetup({ children, pages }: { children: ReactNode; pages?: number }) {
  const { setDocument } = useWorkbench();
  const { setTotalPages } = useActiveHighlight();
  useEffect(() => {
    setDocument('invoice.pdf', 'doc-1');
    if (pages) setTotalPages(pages);
  }, [setDocument, setTotalPages, pages]);
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

beforeEach(() => {
  vi.mocked(fetchRun).mockReset();
  vi.mocked(fetchRun).mockResolvedValue(makeRun({}));
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('ActiveHighlightContext totalPages [BLK-250]', () => {
  it('setTotalPages updates the total pages value', async () => {
    const TestComponent = () => {
      const { totalPages, setTotalPages } = useActiveHighlight();
      useEffect(() => {
        setTotalPages(7);
      // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return <div>Pages: {totalPages}</div>;
    };

    render(
      <AllProviders>
        <TestComponent />
      </AllProviders>
    );

    await waitFor(() => {
      expect(screen.getByText('Pages: 7')).toBeInTheDocument();
    });
  });

  it('activeBBoxPage is set when setActiveBBox is called with page', async () => {
    const TestComponent = () => {
      const { activeBBoxPage, setActiveBBox } = useActiveHighlight();
      useEffect(() => {
        setActiveBBox({ x: 10, y: 10, width: 100, height: 20 }, 3);
      // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return <div>BBoxPage: {activeBBoxPage}</div>;
    };

    render(
      <AllProviders>
        <TestComponent />
      </AllProviders>
    );

    await waitFor(() => {
      expect(screen.getByText('BBoxPage: 3')).toBeInTheDocument();
    });
  });

  it('activeBBoxPage is null when setActiveBBox is called with null', async () => {
    const TestComponent = () => {
      const { activeBBoxPage, setActiveBBox } = useActiveHighlight();
      useEffect(() => {
        setActiveBBox({ x: 10, y: 10, width: 100, height: 20 }, 1);
        setActiveBBox(null);
      // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return <div>BBoxPage: {activeBBoxPage === null ? 'null' : 'set'}</div>;
    };

    render(
      <AllProviders>
        <TestComponent />
      </AllProviders>
    );

    await waitFor(() => {
      expect(screen.getByText('BBoxPage: null')).toBeInTheDocument();
    });
  });

  it('default totalPages is 1', () => {
    const TestComponent = () => {
      const { totalPages } = useActiveHighlight();
      return <div>Pages: {totalPages}</div>;
    };

    render(
      <AllProviders>
        <TestComponent />
      </AllProviders>
    );

    expect(screen.getByText('Pages: 1')).toBeInTheDocument();
  });
});

describe('Pane3DocumentViewer pagination [BLK-250]', () => {
  it('uses totalPages from context instead of heatmap field data', () => {
    render(
      <AllProviders>
        <DocSetup pages={5}>
          <Pane3DocumentViewer />
        </DocSetup>
      </AllProviders>
    );

    // Should show "Page 1 of 5" from context, not "Page 1 of 1" from empty heatmap
    expect(screen.getByText(/Page 1 of 5/)).toBeInTheDocument();
  });

  it('defaults to 1 page when totalPages not set', () => {
    render(
      <AllProviders>
        <DocSetup>
          <Pane3DocumentViewer />
        </DocSetup>
      </AllProviders>
    );

    expect(screen.getByText(/Page 1 of 1/)).toBeInTheDocument();
  });

  it('navigates to next page within totalPages bounds', () => {
    render(
      <AllProviders>
        <DocSetup pages={3}>
          <Pane3DocumentViewer />
        </DocSetup>
      </AllProviders>
    );

    expect(screen.getByText(/Page 1 of 3/)).toBeInTheDocument();

    // Click next page button (ChevronRight)
    const buttons = screen.getAllByRole('button');
    const nextBtn = buttons.find(b => b.querySelector('svg.lucide-chevron-right'));
    expect(nextBtn).toBeTruthy();
    fireEvent.click(nextBtn!);

    expect(screen.getByText(/Page 2 of 3/)).toBeInTheDocument();
  });

  it('disables next page button on last page', () => {
    render(
      <AllProviders>
        <DocSetup pages={2}>
          <Pane3DocumentViewer />
        </DocSetup>
      </AllProviders>
    );

    // Navigate to last page
    const buttons = screen.getAllByRole('button');
    const nextBtn = buttons.find(b => b.querySelector('svg.lucide-chevron-right'))!;
    fireEvent.click(nextBtn);

    expect(screen.getByText(/Page 2 of 2/)).toBeInTheDocument();
    // Next button should now be disabled
    expect(nextBtn).toBeDisabled();
  });

  it('does not show fabricated page count from heatmap fields', () => {
    // Even if heatmapFields has data on page 10, totalPages should come from context
    const TestWrapper = () => {
      const { setTotalPages, setHeatmapFields } = useActiveHighlight();
      useEffect(() => {
        setTotalPages(3);
        setHeatmapFields([
          { id: 'f1', name: 'field', confidence: 0.9, page: 10, bbox: { x: 0, y: 0, width: 10, height: 10 } },
        ]);
      // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return null;
    };

    render(
      <AllProviders>
        <TestWrapper />
        <DocSetup pages={3}>
          <Pane3DocumentViewer />
        </DocSetup>
      </AllProviders>
    );

    // Should show "Page 1 of 3" from context, NOT "Page 1 of 10" from heatmap fields
    expect(screen.getByText(/Page 1 of 3/)).toBeInTheDocument();
    expect(screen.queryByText(/Page 1 of 10/)).not.toBeInTheDocument();
  });
});
