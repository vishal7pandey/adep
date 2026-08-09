'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { Database, Plus, Edit2, ArrowLeft, Search, X } from 'lucide-react';
import dynamic from 'next/dynamic';
import { Template, fetchTemplates, ApiError } from '@/lib/api';
import { AdeButton } from '@/components/ui/AdeButton';
import { AdeBadge } from '@/components/ui/AdeBadge';
import { FieldCardSkeleton } from '@/components/ui/SkeletonLoader';

const TemplateEditorComponent = dynamic(
  () => import('@/components/templates/TemplateEditor').then((mod) => mod.TemplateEditorComponent),
  {
    loading: () => (
      <div className="p-6 space-y-4">
        <FieldCardSkeleton />
        <FieldCardSkeleton />
      </div>
    ),
  }
);

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchTemplates().then(setTemplates).catch((e) => { setTemplates([]); setError(e instanceof ApiError ? `API Error ${e.status}: ${e.message}` : String(e)); });
  }, []);

  const filteredTemplates = useMemo(() => {
    if (!searchQuery.trim()) return templates;
    const q = searchQuery.toLowerCase();
    return templates.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q) ||
        (t.description && t.description.toLowerCase().includes(q)) ||
        (t.fields && t.fields.some((f) => f.name.toLowerCase().includes(q)))
    );
  }, [templates, searchQuery]);

  if (isEditing) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-3 bg-[var(--pane-bg)] border-b border-[var(--pane-border)] flex items-center gap-2">
          <AdeButton
            variant="tertiary"
            size="sm"
            onClick={() => {
              setIsEditing(false);
              setEditingTemplate(null);
            }}
          >
            <ArrowLeft className="w-4 h-4" /> Back to Registry
          </AdeButton>
        </div>
        <div className="flex-1">
          <TemplateEditorComponent
            initialTemplate={editingTemplate}
            onSaveComplete={() => {
              setIsEditing(false);
              fetchTemplates().then(setTemplates);
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto bg-[var(--pane-bg)]">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-[var(--pane-border)]">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2 text-[var(--primary-text)]">
            <Database className="w-5 h-5 text-[#0071CE]" />
            Templates
          </h1>
          <p className="text-xs text-muted mt-1">Define what fields to extract from each document type</p>
        </div>
        <AdeButton
          variant="primary"
          onClick={() => {
            setEditingTemplate(null);
            setIsEditing(true);
          }}
        >
          <Plus className="w-4 h-4" /> Create Template
        </AdeButton>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg border border-[var(--status-error)] bg-[var(--status-error-subtle)] text-xs text-[var(--status-error)]">
          <strong>Failed to load templates:</strong> {error}
          {error.includes('401') && (
            <span className="block mt-1">Authentication is enabled. Set an API key via the API Key Management page.</span>
          )}
          {error.includes('Network error') && (
            <span className="block mt-1">Backend server is not running. Start it with: uv run uvicorn src.api.app:app --reload --port 8000</span>
          )}
        </div>
      )}

      {/* Search Bar */}
      <div className="mb-6 relative max-w-2xl">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search templates..."
          className="w-full pl-9 pr-8 py-2 text-xs rounded-xl bg-[var(--card-bg)] border border-[var(--pane-border)] text-[var(--primary-text)] focus:outline-none focus:border-[#0071CE] transition-colors"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-muted hover:text-[var(--primary-text)]"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Empty State */}
      {filteredTemplates.length === 0 && (
        <div className="py-12 text-center space-y-2">
          <p className="text-sm font-medium text-[var(--primary-text)]">
            {searchQuery ? `No matches found for "${searchQuery}"` : 'No templates available'}
          </p>
          <p className="text-xs text-muted">
            {searchQuery ? 'Try clearing your search query or using a different keyword.' : 'Click "Create Template" to define your first schema template.'}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredTemplates.map((tmpl) => {
          const requiredCount = tmpl.fields.filter((f) => f.required).length;
          return (
            <div
              key={tmpl.id}
              className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs hover:border-[#0071CE] transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-sm text-[var(--primary-text)]">{tmpl.name}</h3>
                  <p className="text-xs text-muted">{tmpl.description}</p>
                </div>

                <AdeButton
                  variant="tertiary"
                  size="sm"
                  onClick={() => {
                    setEditingTemplate(tmpl);
                    setIsEditing(true);
                  }}
                >
                  <Edit2 className="w-3.5 h-3.5" /> Edit
                </AdeButton>
              </div>

              <div className="flex items-center gap-2 pt-1 font-mono text-xs">
                <AdeBadge variant="neutral">{tmpl.fields.length} Fields</AdeBadge>
                <AdeBadge variant="tool">{requiredCount} Required</AdeBadge>
              </div>

              <div className="flex flex-wrap gap-1">
                {tmpl.fields.slice(0, 5).map((f) => (
                  <AdeBadge key={f.name} variant="info">
                    {f.name}
                  </AdeBadge>
                ))}
                {tmpl.fields.length > 5 && (
                  <span className="text-xs text-muted self-center">
                    +{tmpl.fields.length - 5} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
