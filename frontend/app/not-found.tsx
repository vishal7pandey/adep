'use client';

import React from 'react';
import Link from 'next/link';
import { FileQuestion, ArrowLeft, Home } from 'lucide-react';
import { LttsButton } from '@/components/ui/LttsButton';

export default function NotFound() {
  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-[var(--pane-bg)] p-6 space-y-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[var(--brand-primary-subtle)] text-[var(--brand-primary)] flex items-center justify-center shadow-md">
        <FileQuestion className="w-8 h-8" />
      </div>

      <div className="space-y-1.5 max-w-sm">
        <span className="font-mono text-xs font-bold text-[var(--brand-primary)]">404 — PAGE NOT FOUND</span>
        <h1 className="text-xl font-bold text-[var(--primary-text)]">The page you requested does not exist</h1>
        <p className="text-xs text-muted leading-relaxed">
          The requested URL path was not recognized by the ADEP Workbench route handler.
        </p>
      </div>

      <div className="pt-2">
        <Link href="/">
          <LttsButton variant="primary">
            <Home className="w-4 h-4" /> Return to Workbench
          </LttsButton>
        </Link>
      </div>
    </div>
  );
}
