import React, { ReactNode, useState, useEffect } from 'react';
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

import { Pane2ExtractedData } from '@/components/workbench/Pane2ExtractedData';
import { WorkbenchProvider, useWorkbench } from '@/context/WorkbenchContext';
import { ActiveHighlightProvider } from '@/context/ActiveHighlightContext';
import { fetchRun, exportRunJSON, exportRunCSV, ExtractedField, ExtractionRun } from '@/lib/api';

function AllProviders({ children }: { children: ReactNode }) {
  return (
    <WorkbenchProvider>
      <ActiveHighlightProvider>{children}</ActiveHighlightProvider>
    </WorkbenchProvider>
  );
}

function ExtractionSetup({ children }: { children: ReactNode }) {
  const { setDocument, startRun } = useWorkbench();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setDocument('invoice.pdf', 'doc-1');
    startRun('run-1');
    setReady(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  if (!ready) return null;
  return <>{children}</>;
}

function makeField(overrides: Partial<ExtractedField> = {}): ExtractedField {
  return {
    id: 'f1',
    name: 'invoice_number',
    value: 'INV-001',
    confidence: 0.72,
    status: 'extracted',
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
    total_fields: 1,
    extracted_fields_count: 1,
    fields: [makeField()],
    ...overrides,
  };
}

function renderPane2() {
  return render(
    <AllProviders>
      <ExtractionSetup>
        <Pane2ExtractedData />
      </ExtractionSetup>
    </AllProviders>
  );
}

beforeEach(() => {
  vi.mocked(fetchRun).mockReset();
  vi.mocked(exportRunJSON).mockReset();
  vi.mocked(exportRunCSV).mockReset();
  vi.mocked(fetchRun).mockResolvedValue(makeRun({}));

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

describe('Pane2ExtractedData manual edit [BLK-253]', () => {
  it('preserves original status and confidence on manual edit (does not fabricate verified/1.0)', async () => {
    const fields = [
      makeField({ id: 'f1', name: 'invoice_number', value: 'INV-001', confidence: 0.72, status: 'extracted' }),
    ];
    vi.mocked(fetchRun).mockResolvedValueOnce(
      makeRun({ task_type: 'standard_extraction', fields })
    );

    renderPane2();
    await screen.findByText('INV-001');

    // Click edit button
    const editBtn = screen.getByTitle('Edit Field Value');
    fireEvent.click(editBtn);

    // Change value
    const input = screen.getByDisplayValue('INV-001');
    fireEvent.change(input, { target: { value: 'INV-999' } });

    // Save
    const saveBtn = screen.getByRole('button', { name: '' });
    // The save button contains a Check icon, find it by clicking the green button
    const saveButtons = document.querySelectorAll('button.bg-\\[var\\(--status-success\\)\\]');
    fireEvent.click(saveButtons[0]);

    // Verify the new value is shown
    await waitFor(() => {
      expect(screen.getByText('INV-999')).toBeInTheDocument();
    });

    // Verify status is still 'extracted' (not fabricated to 'verified')
    // The badge should show 72% Confidence, not "Verified"
    expect(screen.getByText('72% Confidence')).toBeInTheDocument();
    // Verified count should be 0 (none were verified before or after edit)
    expect(screen.getByText('0/1 Verified')).toBeInTheDocument();
  });
});

describe('Pane2ExtractedData export error handling [BLK-253]', () => {
  it('shows error notice when JSON export API fails and client-side fallback also fails', async () => {
    vi.mocked(fetchRun).mockResolvedValueOnce(
      makeRun({ task_type: 'standard_extraction', fields: [makeField()] })
    );
    vi.mocked(exportRunJSON).mockRejectedValueOnce(new Error('API down'));

    // Sabotage the client-side fallback by removing createElement
    const origCreate = document.createElement.bind(document);
    const origAppend = document.body.appendChild.bind(document.body);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'a') throw new Error('DOM unavailable');
      return origCreate(tag);
    });

    renderPane2();
    await screen.findByText('INV-001');

    // Open export menu and click JSON
    fireEvent.click(screen.getByText('Export'));
    fireEvent.click(screen.getByText('Download JSON'));

    await waitFor(() => {
      expect(screen.getByText(/Export failed/)).toBeInTheDocument();
    });

    vi.mocked(document.createElement).mockRestore();
  });

  it('shows error notice when CSV export API fails and client-side fallback also fails', async () => {
    vi.mocked(fetchRun).mockResolvedValueOnce(
      makeRun({ task_type: 'standard_extraction', fields: [makeField()] })
    );
    vi.mocked(exportRunCSV).mockRejectedValueOnce(new Error('API down'));

    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'a') throw new Error('DOM unavailable');
      return origCreate(tag);
    });

    renderPane2();
    await screen.findByText('INV-001');

    fireEvent.click(screen.getByText('Export'));
    fireEvent.click(screen.getByText('Download CSV'));

    await waitFor(() => {
      expect(screen.getByText(/Export failed/)).toBeInTheDocument();
    });

    vi.mocked(document.createElement).mockRestore();
  });

  it('falls back to client-side JSON export when API fails', async () => {
    vi.mocked(fetchRun).mockResolvedValueOnce(
      makeRun({ task_type: 'standard_extraction', fields: [makeField()] })
    );
    vi.mocked(exportRunJSON).mockRejectedValueOnce(new Error('API down'));

    renderPane2();
    await screen.findByText('INV-001');

    fireEvent.click(screen.getByText('Export'));
    fireEvent.click(screen.getByText('Download JSON'));

    // Should show the fallback notice (not a hard error)
    await waitFor(() => {
      expect(screen.getByText(/Backend API export failed/)).toBeInTheDocument();
    });
  });

  it('falls back to client-side CSV export when API fails', async () => {
    vi.mocked(fetchRun).mockResolvedValueOnce(
      makeRun({ task_type: 'standard_extraction', fields: [makeField()] })
    );
    vi.mocked(exportRunCSV).mockRejectedValueOnce(new Error('API down'));

    renderPane2();
    await screen.findByText('INV-001');

    fireEvent.click(screen.getByText('Export'));
    fireEvent.click(screen.getByText('Download CSV'));

    await waitFor(() => {
      expect(screen.getByText(/Backend API export failed/)).toBeInTheDocument();
    });
  });
});
