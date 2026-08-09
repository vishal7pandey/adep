'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, RefreshCw, Copy, Check, Home } from 'lucide-react';
import { AdeButton } from '@/components/ui/AdeButton';
import Link from 'next/link';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    console.error('[ADEP App Root Error]', error);
  }, [error]);

  const handleCopy = () => {
    const text = `[ADEP Application Error]
Digest: ${error.digest || 'N/A'}
Message: ${error.message || 'Unknown server error'}
Stack: ${error.stack || 'N/A'}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-[var(--pane-bg)] p-6 space-y-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-red-500/10 text-[var(--status-error)] flex items-center justify-center shadow-md animate-pulse">
        <AlertTriangle className="w-8 h-8" />
      </div>

      <div className="space-y-1.5 max-w-md">
        <span className="font-mono text-xs font-bold text-[var(--status-error)]">500 — APPLICATION RUNTIME ERROR</span>
        <h1 className="text-xl font-bold text-[var(--primary-text)]">An unexpected error occurred</h1>
        <p className="text-xs text-muted leading-relaxed">
          {error.message || 'The application encountered an unhandled error during execution.'}
        </p>
      </div>

      <div className="flex items-center gap-2 pt-2">
        <AdeButton variant="primary" onClick={() => reset()}>
          <RefreshCw className="w-4 h-4" /> Try Again
        </AdeButton>
        <AdeButton variant="secondary" onClick={handleCopy}>
          {copied ? <Check className="w-4 h-4 text-[var(--status-success)]" /> : <Copy className="w-4 h-4" />}
          <span>{copied ? 'Copied Diagnostics' : 'Copy Diagnostics'}</span>
        </AdeButton>
        <Link href="/">
          <AdeButton variant="tertiary">
            <Home className="w-4 h-4" /> Home
          </AdeButton>
        </Link>
      </div>
    </div>
  );
}
