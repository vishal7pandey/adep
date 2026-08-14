import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Clean up DOM after each test
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

// Mock sessionStorage for API auth context
if (typeof window !== 'undefined') {
  const sessionStorageMock = (() => {
    let store: Record<string, string> = {};
    return {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = String(value); },
      removeItem: (key: string) => { delete store[key]; },
      clear: () => { store = {}; },
    };
  })();
  Object.defineProperty(window, 'sessionStorage', {
    value: sessionStorageMock,
    writable: true,
  });
}

// Mock global fetch to prevent accidental real network calls
// Individual tests override this with their own mocks.
vi.stubGlobal(
  'fetch',
  vi.fn(() =>
    Promise.reject(new Error('Network error: tests must mock fetch'))
  )
);
