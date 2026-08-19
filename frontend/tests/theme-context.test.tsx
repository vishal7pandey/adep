import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { ThemeProvider, useTheme } from '@/context/ThemeContext';

function renderThemeHook() {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <ThemeProvider>{children}</ThemeProvider>
  );
  return renderHook(() => useTheme(), { wrapper });
}

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('initializes as light when no saved theme and no dark class', () => {
    const { result } = renderThemeHook();
    expect(result.current.theme).toBe('light');
  });

  it('initializes as dark when dark class is pre-applied by inline script', () => {
    document.documentElement.classList.add('dark');
    const { result } = renderThemeHook();
    expect(result.current.theme).toBe('dark');
  });

  it('toggleTheme switches from light to dark and adds class', () => {
    const { result } = renderThemeHook();
    expect(result.current.theme).toBe('light');

    act(() => {
      result.current.toggleTheme();
    });

    expect(result.current.theme).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('ltts_theme')).toBe('dark');
  });

  it('toggleTheme switches from dark to light and removes class', () => {
    document.documentElement.classList.add('dark');
    const { result } = renderThemeHook();

    act(() => {
      result.current.toggleTheme();
    });

    expect(result.current.theme).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('ltts_theme')).toBe('light');
  });

  it('should throw when used outside provider', () => {
    expect(() => renderHook(() => useTheme())).toThrow(
      'useTheme must be used within a ThemeProvider'
    );
  });

  it('persists theme choice to localStorage', () => {
    const { result } = renderThemeHook();

    act(() => {
      result.current.toggleTheme();
    });

    expect(localStorage.getItem('ltts_theme')).toBe('dark');

    act(() => {
      result.current.toggleTheme();
    });

    expect(localStorage.getItem('ltts_theme')).toBe('light');
  });
});
