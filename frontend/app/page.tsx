import { Suspense } from 'react';
import { WorkbenchLayout } from '@/components/workbench/WorkbenchLayout';

export default function Home() {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      <Suspense fallback={null}>
        <WorkbenchLayout />
      </Suspense>
    </div>
  );
}
