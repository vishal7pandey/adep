'use client';

import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface AdeButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'destructive' | 'tertiary';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

export const AdeButton: React.FC<AdeButtonProps> = ({
  variant = 'primary',
  size = 'md',
  className,
  children,
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center gap-1.5 font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-[var(--brand-accent)] focus:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-2xs';

  const variantStyles = {
    primary: 'bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-[var(--inverse-text)] active:bg-[var(--brand-primary-hover)]',
    secondary: 'border border-[var(--brand-primary)] text-[var(--brand-primary)] hover:bg-[var(--brand-primary-subtle)] bg-transparent',
    destructive: 'bg-[var(--status-error)] hover:bg-red-700 text-white active:bg-red-800',
    tertiary: 'text-[var(--primary-text)] hover:bg-[var(--surface-raised)] bg-transparent shadow-none',
  };

  const sizeStyles = {
    sm: 'px-2.5 py-1 text-xs',
    md: 'px-3.5 py-1.5 text-xs',
    lg: 'px-4 py-2 text-sm',
  };

  return (
    <button
      className={twMerge(clsx(baseStyles, variantStyles[variant], sizeStyles[size], className))}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};
