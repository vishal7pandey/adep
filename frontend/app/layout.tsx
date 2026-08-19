import type { Metadata } from 'next';
import { Suspense } from 'react';
import './globals.css';
import { ThemeProvider } from '@/context/ThemeContext';
import { ActiveHighlightProvider } from '@/context/ActiveHighlightContext';
import { WorkbenchProvider } from '@/context/WorkbenchContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { GlobalKeyboardShortcuts } from '@/components/ui/GlobalKeyboardShortcuts';
import { OnboardingTour } from '@/components/ui/OnboardingTour';

import { ErrorBoundary } from '@/components/ui/ErrorBoundary';

export const metadata: Metadata = {
  title: 'ADEP Workbench — Agentic Document Extraction Platform',
  description: 'Local-first 3-pane workbench for intelligent agentic document extraction',
};

const themeInitScript = `(() => {
  try {
    const saved = localStorage.getItem('ltts_theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = saved === 'dark' || (!saved && prefersDark);
    if (isDark) document.documentElement.classList.add('dark');
  } catch (e) { console.warn('Theme init failed:', e); }
})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="h-full flex overflow-hidden" suppressHydrationWarning>
        <ErrorBoundary>
          <ThemeProvider>
            <ActiveHighlightProvider>
              <WorkbenchProvider>
                <GlobalKeyboardShortcuts />
                <OnboardingTour />
                <div className="flex h-screen w-screen overflow-hidden">
                  <Suspense fallback={null}>
                    <Sidebar />
                  </Suspense>
                  <main id="main-content" className="flex-1 flex flex-col min-w-0 h-full overflow-hidden" tabIndex={-1}>
                    {children}
                  </main>
                </div>
                <CommandPalette />
              </WorkbenchProvider>
            </ActiveHighlightProvider>
          </ThemeProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
