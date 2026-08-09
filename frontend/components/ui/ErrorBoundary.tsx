'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Copy, Check, ShieldAlert } from 'lucide-react';
import { LttsButton } from '@/components/ui/LttsButton';

interface Props {
  children: ReactNode;
  paneName?: string;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  copied: boolean;
  errorId: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      copied: false,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    const errorId = `ERR_${Date.now().toString(36).toUpperCase()}_${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
    return { hasError: true, error, errorId };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    // Log error cleanly to console (excluding sensitive data)
    console.error(`[ADEP ErrorBoundary ${this.props.paneName || 'Global'}]`, error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      copied: false,
      errorId: null,
    });
  };

  handleCopyError = () => {
    const { error, errorInfo, errorId } = this.state;
    const payload = `[ADEP Error Report]
Error ID: ${errorId}
Pane: ${this.props.paneName || 'Global'}
Message: ${error?.message || 'Unknown error'}
Component Stack:
${errorInfo?.componentStack || 'N/A'}`;

    navigator.clipboard.writeText(payload);
    this.setState({ copied: true });
    setTimeout(() => this.setState({ copied: false }), 2500);
  };

  render() {
    if (this.state.hasError) {
      const isPane = Boolean(this.props.paneName);

      return (
        <div
          className={`w-full flex flex-col items-center justify-center p-6 bg-[var(--pane-bg)] border border-[var(--pane-border)] text-center space-y-4 ${
            isPane ? 'h-full rounded-xl m-1' : 'min-h-screen'
          }`}
        >
          <div className="w-12 h-12 rounded-full bg-red-500/10 text-[var(--status-error)] flex items-center justify-center animate-bounce">
            <AlertTriangle className="w-6 h-6" />
          </div>

          <div className="space-y-1 max-w-md">
            <h2 className="text-sm font-bold text-[var(--primary-text)]">
              {this.props.fallbackTitle || (isPane ? `Could not load ${this.props.paneName}` : 'Something went wrong')}
            </h2>
            <p className="text-xs text-muted leading-relaxed">
              {this.state.error?.message || 'An unexpected rendering error occurred in this application module.'}
            </p>
            {this.state.errorId && (
              <span className="inline-block font-mono text-[10px] text-muted/70 bg-black/5 dark:bg-white/5 px-2 py-0.5 rounded">
                Ref ID: {this.state.errorId}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 pt-2">
            <LttsButton variant="primary" size="sm" onClick={this.handleReset}>
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </LttsButton>
            <LttsButton variant="secondary" size="sm" onClick={this.handleCopyError}>
              {this.state.copied ? <Check className="w-3.5 h-3.5 text-[var(--status-success)]" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{this.state.copied ? 'Copied' : 'Copy Diagnostics'}</span>
            </LttsButton>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
