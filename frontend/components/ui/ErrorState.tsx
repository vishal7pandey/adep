'use client';

import React, { useState, useEffect } from 'react';
import { AlertCircle, RefreshCcw, WifiOff, Clock, ShieldAlert, Copy, Check } from 'lucide-react';
import { Button } from './Button';

interface ErrorStateProps {
  title?: string;
  message: string;
  status?: number;
  requestId?: string;
  onRetry?: () => void;
  autoRetrySeconds?: number;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  status = 0,
  requestId,
  onRetry,
  autoRetrySeconds,
}) => {
  const [countdown, setCountdown] = useState<number | null>(autoRetrySeconds || (status === 429 ? 10 : null));
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (countdown === null || countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer);
          if (onRetry) onRetry();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown, onRetry]);

  const handleCopyDetails = () => {
    const details = `Error: ${title || 'ApiError'}\nStatus: ${status}\nMessage: ${message}\nRequest ID: ${requestId || 'N/A'}`;
    navigator.clipboard.writeText(details).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const isNetworkError = status === 0;
  const is429 = status === 429;
  const is404 = status === 404;

  const displayTitle =
    title ||
    (isNetworkError
      ? 'Backend Unreachable'
      : is429
      ? 'Rate Limit Exceeded'
      : is404
      ? 'Resource Not Found'
      : 'API Execution Failed');

  return (
    <div className="p-6 rounded-xl border border-[var(--status-error)]/30 bg-[var(--status-error-subtle)] space-y-4 text-xs animate-fadeIn">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-[var(--status-error)] text-white shrink-0">
          {isNetworkError ? (
            <WifiOff className="w-5 h-5" />
          ) : is429 ? (
            <Clock className="w-5 h-5 animate-pulse" />
          ) : (
            <ShieldAlert className="w-5 h-5" />
          )}
        </div>

        <div className="flex-1 space-y-1">
          <h4 className="font-bold text-sm text-[var(--primary-text)]">{displayTitle}</h4>
          <p className="text-[var(--primary-text)] font-medium leading-relaxed">{message}</p>

          {is429 && countdown !== null && countdown > 0 && (
            <p className="text-xs font-semibold text-[var(--status-warning)] flex items-center gap-1 pt-1">
              <Clock className="w-3.5 h-3.5" />
              <span>Auto-retrying in {countdown} seconds…</span>
            </p>
          )}

          {requestId && (
            <p className="font-mono text-[10px] text-muted pt-1">
              Request ID: <span className="select-all">{requestId}</span>
            </p>
          )}
        </div>
      </div>

      {/* Recovery CTAs */}
      <div className="flex items-center justify-between pt-2 border-t border-black/10 dark:border-white/10">
        <button
          onClick={handleCopyDetails}
          className="flex items-center gap-1 text-[11px] text-muted hover:text-[var(--primary-text)] font-medium transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-[var(--status-success)]" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Details copied' : 'Copy error details'}</span>
        </button>

        {onRetry && (
          <Button variant="primary" size="sm" onClick={onRetry}>
            <RefreshCcw className="w-3.5 h-3.5" />
            <span>Retry Now</span>
          </Button>
        )}
      </div>
    </div>
  );
};
