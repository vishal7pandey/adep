'use client';

import React from 'react';
import { ApiKeyManagement } from '@/components/settings/ApiKeyManagement';

export default function SettingsPage() {
  return (
    <div className="h-full w-full">
      <ApiKeyManagement />
    </div>
  );
}
