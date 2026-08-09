'use client';

import React, { useEffect, useState } from 'react';
import { Database, Plus, Edit2, ArrowLeft } from 'lucide-react';
import { Template, fetchTemplates } from '@/lib/api';
import { AdeButton } from '@/components/ui/AdeButton';
import { AdeBadge } from '@/components/ui/AdeBadge';
import { TemplateEditorComponent } from '@/components/templates/TemplateEditor';

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    fetchTemplates().then(setTemplates);
  }, []);

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
            Template Schema Registry & Editor
          </h1>
          <p className="text-xs text-muted mt-1">Define outcome contracts, field data types, required constraints, and confidence thresholds</p>
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

      <div className="space-y-4">
        {templates.map((tmpl) => (
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
                <Edit2 className="w-3.5 h-3.5" /> Edit Schema
              </AdeButton>
            </div>

            <div className="border rounded-lg overflow-hidden border-[var(--pane-border)]">
              <table className="w-full text-xs text-left">
                <thead className="bg-black/5 dark:bg-white/5 border-b border-[var(--pane-border)] font-semibold text-[var(--secondary-text)]">
                  <tr>
                    <th className="p-2">Field Name</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Required</th>
                    <th className="p-2">Threshold</th>
                    <th className="p-2">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {tmpl.fields.map((f) => (
                    <tr key={f.name} className="border-b last:border-0 border-black/5 dark:border-white/5">
                      <td className="p-2 font-mono font-bold text-[#0071CE]">{f.name}</td>
                      <td className="p-2 font-mono text-muted">{f.type}</td>
                      <td className="p-2">{f.required ? 'Yes' : 'No'}</td>
                      <td className="p-2 font-mono">{f.confidence_threshold ? `${Math.round(f.confidence_threshold * 100)}%` : '70%'}</td>
                      <td className="p-2 text-muted">{f.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
