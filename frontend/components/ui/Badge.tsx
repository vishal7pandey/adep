'use client';

import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface BadgeProps {
  variant?: 'verified' | 'medium' | 'failed' | 'tool' | 'info' | 'neutral';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  children,
  className,
}) => {
  const baseStyles = 'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-all';

  const variantStyles = {
    verified: 'bg-[var(--status-success)] text-white',
    medium: 'bg-[var(--status-warning)] text-black',
    failed: 'bg-[var(--status-error)] text-white',
    tool: 'bg-[var(--badge-tool-bg)] text-[var(--badge-tool-text)] rounded-full px-2.5',
    info: 'bg-[var(--brand-primary)] text-white',
    neutral: 'bg-[var(--surface-raised)] text-[var(--primary-text)]',
  };

  return (
    <span className={twMerge(clsx(baseStyles, variantStyles[variant], className))}>
      {children}
    </span>
  );
};
