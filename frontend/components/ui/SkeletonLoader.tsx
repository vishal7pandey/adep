'use client';

import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div
      className={`animate-pulse rounded bg-black/10 dark:bg-white/10 ${className}`}
    />
  );
};

export const FieldCardSkeleton: React.FC = () => {
  return (
    <div className="p-3.5 rounded-lg border border-[var(--card-border)] bg-[var(--card-bg)] space-y-2.5 shadow-2xs">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-4 w-20 rounded-full" />
      </div>
      <Skeleton className="h-8 w-full rounded-md" />
      <div className="flex justify-end pt-1">
        <Skeleton className="h-3 w-32" />
      </div>
    </div>
  );
};

export const ConsoleCycleSkeleton: React.FC = () => {
  return (
    <div className="p-3 rounded-lg border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs">
      <div className="flex justify-between items-center">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-14" />
      </div>
      <Skeleton className="h-14 w-full rounded-md" />
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-24 rounded-full" />
        <Skeleton className="h-3 w-36" />
      </div>
    </div>
  );
};
