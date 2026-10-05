'use client';

import React, { useState } from 'react';
import { Database, Plus, Trash2, Save, Copy, CheckCircle2, Wand2 } from 'lucide-react';
import { Template, FieldSchema, createTemplate, GeneratedTemplate } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { AiTemplateComposer } from '@/components/templates/AiTemplateComposer';

export const TemplateEditorComponent: React.FC<{ initialTemplate?: Template | null; onSaveComplete?: () => void }> = ({
  initialTemplate,
  onSaveComplete,
}) => {
  const [name, setName] = useState(initialTemplate?.name || '');
  const [description, setDescription] = useState(initialTemplate?.description || '');
  const [fields, setFields] = useState<FieldSchema[]>(initialTemplate?.fields || []);
  const [showComposer, setShowComposer] = useState(false);

  const handleApplyGenerated = (generated: GeneratedTemplate) => {
    setName(generated.name);
    setFields(generated.fields);
  };

  const addField = () => {
    setFields((prev) => [
      ...prev,
      { name: `field_${prev.length + 1}`, type: 'string', description: '', required: false, confidence_threshold: 0.8 },
    ]);
  };

  const removeField = (index: number) => {
    setFields((prev) => prev.filter((_, i) => i !== index));
  };

  const updateField = (index: number, key: keyof FieldSchema, value: unknown) => {
    setFields((prev) =>
      prev.map((f, i) => (i === index ? { ...f, [key]: value } : f))
    );
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    await createTemplate({
      name,
      description,
      fields,
    });
    if (onSaveComplete) onSaveComplete();
  };

  return (
    <div className="h-full flex flex-col bg-[var(--pane-bg)] overflow-hidden">
      {/* Top Header */}
      <div className="px-6 py-4 border-b border-[var(--pane-border)] flex items-center justify-between bg-black/5 dark:bg-white/5 shrink-0">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2 text-[var(--primary-text)]">
            <Database className="w-5 h-5 text-[var(--brand-primary)]" /> Schema Template Builder
          </h2>
          <p className="text-xs text-muted mt-0.5">
            Define target structured output fields and validation confidence thresholds
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={() => setShowComposer(true)}>
            <Wand2 className="w-4 h-4" /> Auto-generate from Description
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={!name.trim() || fields.length === 0}>
            <Save className="w-4 h-4" /> Save Template
          </Button>
        </div>
      </div>

      {/* Main Form Body */}
      <div className="flex-1 p-6 overflow-y-auto max-w-4xl space-y-6 text-xs">
        {/* Section 1: Template Details */}
        <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-4 shadow-2xs">
          <div>
            <h3 className="font-bold text-sm text-[var(--primary-text)]">1. Basic Information</h3>
            <p className="text-[11px] text-muted">Provide a clear name and purpose for this document schema template.</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold mb-1">
                Template Name *
                <InfoTooltip text="Unique name describing this extraction target schema" />
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Commercial Invoice Schema"
                className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 focus:outline-none focus:border-[var(--brand-primary)]"
              />
              <p className="text-[10px] text-muted mt-1">Short recognizable title used in Agent Definitions</p>
            </div>

            <div>
              <label className="block font-semibold mb-1">
                Description
                <InfoTooltip text="Detailed explanation of fields covered by this schema" />
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Schema for standard AP commercial invoices"
                className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 focus:outline-none focus:border-[var(--brand-primary)]"
              />
              <p className="text-[10px] text-muted mt-1">Helps team members select the correct schema</p>
            </div>
          </div>
        </div>

        {/* Section 2: Fields List */}
        <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-sm text-[var(--primary-text)]">2. Document Target Fields</h3>
              <p className="text-[11px] text-muted">Add and configure each field the Agent Definition should extract from documents.</p>
            </div>
            <Button variant="secondary" size="sm" onClick={addField}>
              <Plus className="w-3.5 h-3.5" /> Add Field
            </Button>
          </div>

          {fields.length === 0 ? (
            <div className="p-8 text-center text-muted border border-dashed border-[var(--card-border)] rounded-xl bg-black/5 dark:bg-white/5 space-y-3">
              <Database className="w-8 h-8 mx-auto opacity-30 text-[var(--brand-primary)]" />
              <p className="text-sm font-semibold text-[var(--primary-text)]">No fields defined yet</p>
              <p className="text-xs max-w-sm mx-auto text-muted">
                Start by adding your first target extraction field for this document schema template.
              </p>
              <Button variant="primary" size="sm" onClick={addField}>
                <Plus className="w-3.5 h-3.5" /> Add First Field
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {fields.map((field, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-white/5 space-y-3"
                >
                  <div className="grid grid-cols-12 gap-3 items-center">
                    <div className="col-span-4">
                      <label className="block font-semibold text-[11px] mb-1">
                        Field Name *
                        <InfoTooltip text="JSON property key name (e.g. vendor_name)" />
                      </label>
                      <input
                        type="text"
                        value={field.name}
                        onChange={(e) => updateField(idx, 'name', e.target.value)}
                        placeholder="vendor_name"
                        className="w-full p-2 rounded border border-[var(--card-border)] font-mono text-xs bg-[var(--pane-bg)] focus:outline-none"
                      />
                    </div>

                    <div className="col-span-3">
                      <label className="block font-semibold text-[11px] mb-1">
                        Data Type
                        <InfoTooltip text="Expected data type for field validation" />
                      </label>
                      <select
                        value={field.type}
                        onChange={(e) => updateField(idx, 'type', e.target.value)}
                        className="w-full p-2 rounded border border-[var(--card-border)] text-xs bg-[var(--pane-bg)] focus:outline-none"
                      >
                        <option value="string">String (Text)</option>
                        <option value="number">Number (Amount/Qty)</option>
                        <option value="date">Date (YYYY-MM-DD)</option>
                        <option value="boolean">Boolean (True/False)</option>
                        <option value="array">Array (Line Items)</option>
                      </select>
                    </div>

                    <div className="col-span-3">
                      <label className="block font-semibold text-[11px] mb-1">
                        Min Confidence
                        <InfoTooltip text="Minimum confidence threshold required (0.0 to 1.0)" />
                      </label>
                      <input
                        type="number"
                        step="0.05"
                        min="0.1"
                        max="1.0"
                        value={field.confidence_threshold || 0.8}
                        onChange={(e) => updateField(idx, 'confidence_threshold', parseFloat(e.target.value))}
                        className="w-full p-2 rounded border border-[var(--card-border)] font-mono text-xs bg-[var(--pane-bg)] focus:outline-none"
                      />
                    </div>

                    <div className="col-span-2 flex items-center justify-end pt-5">
                      <button
                        onClick={() => removeField(idx)}
                        className="p-1.5 text-muted hover:text-red-500 rounded hover:bg-black/10 transition-colors"
                        title="Remove Field"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-12 gap-3 items-center pt-1 border-t border-black/5 dark:border-white/5">
                    <div className="col-span-9">
                      <input
                        type="text"
                        value={field.description}
                        onChange={(e) => updateField(idx, 'description', e.target.value)}
                        placeholder="Description / hint for Agent Definition"
                        className="w-full p-1.5 rounded border border-[var(--card-border)] text-[11px] bg-[var(--pane-bg)] focus:outline-none"
                      />
                    </div>

                    <div className="col-span-3 flex items-center justify-end">
                      <label className="flex items-center gap-1.5 cursor-pointer text-[11px] font-semibold">
                        <input
                          type="checkbox"
                          checked={field.required}
                          onChange={(e) => updateField(idx, 'required', e.target.checked)}
                          className="accent-[var(--brand-primary)]"
                        />
                        <span>Required Field</span>
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* AI Template Composer Modal (BLK-067) */}
      {showComposer && (
        <AiTemplateComposer
          onApply={handleApplyGenerated}
          onClose={() => setShowComposer(false)}
        />
      )}
    </div>
  );
};
