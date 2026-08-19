import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  usePathname: () => '/',
  useRouter: () => ({
    push: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock ThemeContext
vi.mock('@/context/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    toggleTheme: vi.fn(),
  }),
}));

// Mock WorkbenchContext
vi.mock('@/context/WorkbenchContext', () => ({
  useWorkbench: () => ({
    reset: vi.fn(),
    setDocument: vi.fn(),
    startRun: vi.fn(),
    setRunStatus: vi.fn(),
  }),
}));

// Mock API functions
vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    fetchRecentRuns: vi.fn(),
    deleteRun: vi.fn(),
    duplicateRun: vi.fn(),
    renameRun: vi.fn(),
  };
});

import { Sidebar } from '@/components/layout/Sidebar';
import { fetchRecentRuns, deleteRun, duplicateRun, renameRun, ExtractionRun } from '@/lib/api';

function makeRun(overrides: Partial<ExtractionRun> = {}): ExtractionRun {
  return {
    id: 'run-1',
    definition_id: 'def-1',
    document_url: '/docs/invoice.pdf',
    status: 'completed',
    current_cycle: 3,
    total_fields: 5,
    extracted_fields_count: 4,
    fields: [],
    ...overrides,
  };
}

/** Helper: open the context menu for a session row and click the given action */
async function openMenuAndClick(action: 'Rename' | 'Duplicate' | 'Delete') {
  const buttons = screen.getAllByRole('button');
  const moreBtn = buttons.find(
    (b) => b.querySelector('svg.lucide-ellipsis-vertical, svg.lucide-more-vertical')
  );
  expect(moreBtn).toBeTruthy();
  fireEvent.click(moreBtn!);

  const actionBtn = await screen.findByText(action);
  fireEvent.click(actionBtn);
}

describe('Sidebar session management [BLK-248]', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchRecentRuns).mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('handleDeleteSession', () => {
    it('removes session from list on successful delete', async () => {
      const run = makeRun({ id: 'r1', document_url: '/docs/a.pdf' });
      vi.mocked(fetchRecentRuns).mockResolvedValue([run]);
      vi.mocked(deleteRun).mockResolvedValue({ deleted: true });

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('/docs/a.pdf')).toBeInTheDocument());

      await openMenuAndClick('Delete');

      await waitFor(() => expect(vi.mocked(deleteRun)).toHaveBeenCalledWith('r1'));
      await waitFor(() => expect(screen.queryByText('/docs/a.pdf')).not.toBeInTheDocument());
    });

    it('sets sessionError on delete failure instead of unhandled rejection', async () => {
      const run = makeRun({ id: 'r1', document_url: '/docs/a.pdf' });
      vi.mocked(fetchRecentRuns).mockResolvedValue([run]);
      vi.mocked(deleteRun).mockRejectedValue(new Error('Delete failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('/docs/a.pdf')).toBeInTheDocument());

      await openMenuAndClick('Delete');

      await waitFor(() => expect(vi.mocked(deleteRun)).toHaveBeenCalledWith('r1'));
      // Error was caught — sessionError display replaces session list
      await waitFor(() => expect(screen.getByText(/Backend server offline|Auth error/)).toBeInTheDocument());

      consoleSpy.mockRestore();
    });
  });

  describe('handleDuplicateSession', () => {
    it('adds duplicated session to list on success', async () => {
      const run = makeRun({ id: 'r1', document_url: '/docs/a.pdf' });
      const dup = makeRun({ id: 'r2', document_url: '/docs/a.pdf' });
      vi.mocked(fetchRecentRuns).mockResolvedValue([run]);
      vi.mocked(duplicateRun).mockResolvedValue(dup);

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('/docs/a.pdf')).toBeInTheDocument());

      await openMenuAndClick('Duplicate');

      await waitFor(() => expect(vi.mocked(duplicateRun)).toHaveBeenCalledWith('r1'));
    });

    it('sets sessionError on duplicate failure', async () => {
      const run = makeRun({ id: 'r1', document_url: '/docs/a.pdf' });
      vi.mocked(fetchRecentRuns).mockResolvedValue([run]);
      vi.mocked(duplicateRun).mockRejectedValue(new Error('Duplicate failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('/docs/a.pdf')).toBeInTheDocument());

      await openMenuAndClick('Duplicate');

      await waitFor(() => expect(vi.mocked(duplicateRun)).toHaveBeenCalledWith('r1'));
      // Error was caught — sessionError display replaces session list
      await waitFor(() => expect(screen.getByText(/Backend server offline|Auth error/)).toBeInTheDocument());

      consoleSpy.mockRestore();
    });
  });

  describe('handleRenameSession', () => {
    it('updates name field (not document_url) on successful rename', async () => {
      const run = makeRun({ id: 'r1', document_url: '/docs/a.pdf' });
      vi.mocked(fetchRecentRuns).mockResolvedValue([run]);
      vi.mocked(renameRun).mockResolvedValue({ id: 'r1', name: 'My Custom Name' });

      const promptMock = vi.fn(() => 'My Custom Name');
      vi.stubGlobal('prompt', promptMock);

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('/docs/a.pdf')).toBeInTheDocument());

      await openMenuAndClick('Rename');

      await waitFor(() => expect(vi.mocked(renameRun)).toHaveBeenCalledWith('r1', 'My Custom Name'));
      await waitFor(() => expect(screen.getByText('My Custom Name')).toBeInTheDocument());

      vi.unstubAllGlobals();
    });

    it('does not corrupt document_url when renaming [BLK-248]', async () => {
      const run = makeRun({ id: 'r1', document_url: '/docs/important.pdf' });
      vi.mocked(fetchRecentRuns).mockResolvedValue([run]);
      vi.mocked(renameRun).mockResolvedValue({ id: 'r1', name: 'Renamed Session' });

      const promptMock = vi.fn(() => 'Renamed Session');
      vi.stubGlobal('prompt', promptMock);

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('/docs/important.pdf')).toBeInTheDocument());

      await openMenuAndClick('Rename');

      await waitFor(() => expect(screen.getByText('Renamed Session')).toBeInTheDocument());
      expect(screen.queryByText('/docs/important.pdf')).not.toBeInTheDocument();

      vi.unstubAllGlobals();
    });

    it('sets sessionError on rename failure instead of unhandled rejection', async () => {
      const run = makeRun({ id: 'r1', document_url: '/docs/a.pdf' });
      vi.mocked(fetchRecentRuns).mockResolvedValue([run]);
      vi.mocked(renameRun).mockRejectedValue(new Error('Rename failed'));

      const promptMock = vi.fn(() => 'New Name');
      vi.stubGlobal('prompt', promptMock);
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('/docs/a.pdf')).toBeInTheDocument());

      await openMenuAndClick('Rename');

      // renameRun was called (handler attempted the rename)
      await waitFor(() => expect(vi.mocked(renameRun)).toHaveBeenCalledWith('r1', 'New Name'));
      // No unhandled rejection — the error was caught and setSessionError was called
      // After error, session list is replaced by error message, so we verify via error display
      await waitFor(() => expect(screen.getByText(/Backend server offline|Auth error/)).toBeInTheDocument());

      vi.unstubAllGlobals();
      consoleSpy.mockRestore();
    });
  });

  describe('session display', () => {
    it('shows name field when available, falling back to document_url then id', async () => {
      const runs = [
        makeRun({ id: 'r1', name: 'Custom Name', document_url: '/docs/a.pdf' }),
        makeRun({ id: 'r2', document_url: '/docs/b.pdf' }),
        makeRun({ id: 'r3', document_url: '' }),
      ];
      vi.mocked(fetchRecentRuns).mockResolvedValue(runs);

      render(<Sidebar />);
      await waitFor(() => expect(screen.getByText('Custom Name')).toBeInTheDocument());
      expect(screen.getByText('/docs/b.pdf')).toBeInTheDocument();
      expect(screen.getByText('r3')).toBeInTheDocument();
    });
  });
});
