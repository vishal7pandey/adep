'use client';

import React, { useState } from 'react';
import { Sparkles, X, Loader2, AlertCircle, Check, Plus, Trash2, Wand2 } from 'lucide-react';
import { generateTemplate, GeneratedTemplate, ApiError } from '@/lib/api';
import { LttsButton } from '@/components/ui/LttsButton';
import { LttsBadge } from '@/components/ui/LttsBadge';

interface AiTemplateComposerProps {
  onApply: (template: GeneratedTemplate) => void;
  onClose: () => void;
}

const EXAMPLE_PROMPTS = [
  'Extract vendor name, invoice number, invoice date, due date, total amount, subtotal, tax amount, and line items with quantity, rate, and total.',
  'Extract contract title, effective date, expiration date, parties, contract value, and payment terms.',
  'Extract receipt merchant, transaction date, total amount, payment method, and itemized purchases.',
];

export const AiTemplateComposer: React.FC<AiTemplateComposerProps> = ({ onApply, onClose }) => {
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generated, setGenerated] = useState<GeneratedTemplate | null>(null);

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setGenerated(null);
    try {
      const result = await generateTemplate(description.trim());
      setGenerated(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API Error ${err.status}: ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to generate template');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (generated) {
      onApply(generated);
      onClose();
    }
  };

  const updateFieldName = (idx: number, name: string) => {
    if (!generated) return;
    setGenerated({
      ...generated,
      fields: generated.fields.map((f, i) => (i === idx ? { ...f, name } : f)),
    });
  };

  const updateFieldType = (idx: number, type: string) => {
    if (!generated) return;
    setGenerated({
      ...generated,
      fields: generated.fields.map((f, i) => (i === idx ? { ...f, type } : f)),
    });
  };

  const updateFieldThreshold = (idx: number, threshold: number) => {
    if (!generated) return;
    setGenerated({
      ...generated,
      fields: generated.fields.map((f, i) => (i === idx ? { ...f, confidence_threshold: threshold } : f)),
    });
  };

  const updateFieldRequired = (idx: number, required: boolean) => {
    if (!generated) return;
    setGenerated({
      ...generated,
      fields: generated.fields.map((f, i) => (i === idx ? { ...f, required } : f)),
    });
  };

  const updateFieldDescription = (idx: number, desc: string) => {
    if (!generated) return;
    setGenerated({
      ...generated,
      fields: generated.fields.map((f, i) => (i === idx ? { ...f, description: desc } : f)),
    });
  };

  const removeField = (idx: number) => {
    if (!generated) return;
    setGenerated({
      ...generated,
      fields: generated.fields.filter((_, i) => i !== idx),
    });
  };

  const addField = () => {
    if (!generated) return;
    setGenerated({
      ...generated,
      fields: [
        ...generated.fields,
        { name: `field_${generated.fields.length + 1}`, type: 'string', description: '', required: false, confidence_threshold: 0.8 },
      ],
    });
  };

  const updateGeneratedName = (name: string) => {
    if (!generated) return;
    setGenerated({ ...generated, name });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-[var(--card-border)] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--brand-primary-subtle)] flex items-center justify-center">
              <Wand2 className="w-4.5 h-4.5 text-[var(--brand-primary)]" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[var(--primary-text)]">AI Template Composer</h2>
              <p className="text-[10px] text-muted">Describe what you want to extract — AI generates the schema</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted hover:text-[var(--primary-text)] hover:bg-[var(--surface-raised)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Description input (hidden once generated) */}
          {!generated && (
            <>
              <div>
                <label className="block text-xs font-semibold text-[var(--primary-text)] mb-1.5">
                  Describe your extraction target
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Extract vendor name, invoice number, invoice date, line items with quantity, rate, and total, plus the final total including tax."
                  rows={5}
                  className="w-full p-3 rounded-lg border border-[var(--card-border)] bg-[var(--pane-bg)] text-xs text-[var(--primary-text)] focus:outline-none focus:border-[var(--brand-primary)] resize-none"
                  disabled={loading}
                />
                <p className="text-[10px] text-muted mt-1.5">
                  Be specific about field names, data types, and whether fields are required.
                </p>
              </div>

              {/* Example prompts */}
              {!loading && (
                <div>
                  <p className="text-[10px] font-semibold text-muted uppercase tracking-wide mb-2">Examples</p>
                  <div className="space-y-1.5">
                    {EXAMPLE_PROMPTS.map((prompt, i) => (
                      <button
                        key={i}
                        onClick={() => setDescription(prompt)}
                        className="w-full text-left p-2.5 rounded-lg border border-[var(--card-border)] bg-[var(--pane-bg)] text-[11px] text-muted hover:text-[var(--primary-text)] hover:border-[var(--brand-primary)] transition-all"
                      >
                        <Sparkles className="w-3 h-3 inline mr-1.5 text-[var(--brand-primary)] opacity-60" />
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Loading state */}
              {loading && (
                <div className="flex flex-col items-center justify-center py-8 gap-3">
                  <Loader2 className="w-8 h-8 text-[var(--brand-primary)] animate-spin" />
                  <p className="text-xs text-muted">Generating schema from your description…</p>
                  <p className="text-[10px] text-muted">This may take a few seconds</p>
                </div>
              )}

              {/* Error state */}
              {error && !loading && (
                <div className="flex items-start gap-2 p-3 rounded-lg border border-[var(--status-error)] bg-[var(--status-error-subtle)] text-xs text-[var(--status-error)]">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Generation failed</p>
                    <p className="mt-0.5">{error}</p>
                    {error.includes('404') && (
                      <p className="mt-1 text-[10px]">The backend AI Template Composer endpoint may not be deployed yet (BLK-070).</p>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Generated schema preview (editable) */}
          {generated && (
            <>
              <div className="flex items-center gap-2 p-3 rounded-lg border border-[var(--status-success)] bg-[var(--status-success-subtle)]">
                <Check className="w-4 h-4 text-[var(--status-success)] shrink-0" />
                <p className="text-xs text-[var(--status-success)] font-medium">
                  Schema generated — review and edit below, then apply to editor.
                </p>
              </div>

              {/* Generated template name */}
              <div>
                <label className="block text-xs font-semibold text-[var(--primary-text)] mb-1">Template Name</label>
                <input
                  type="text"
                  value={generated.name}
                  onChange={(e) => updateGeneratedName(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-[var(--pane-bg)] text-xs text-[var(--primary-text)] focus:outline-none focus:border-[var(--brand-primary)]"
                />
              </div>

              {/* Field count badge */}
              <div className="flex items-center gap-2">
                <LttsBadge variant="info">{generated.fields.length} Fields</LttsBadge>
                <LttsBadge variant="tool">
                  {generated.fields.filter((f) => f.required).length} Required
                </LttsBadge>
              </div>

              {/* Editable fields */}
              <div className="space-y-2.5">
                {generated.fields.map((field, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-[var(--card-border)] bg-[var(--pane-bg)] space-y-2.5"
                  >
                    <div className="grid grid-cols-12 gap-2.5 items-center">
                      <div className="col-span-4">
                        <label className="block font-semibold text-[10px] mb-1 text-muted">Field Name</label>
                        <input
                          type="text"
                          value={field.name}
                          onChange={(e) => updateFieldName(idx, e.target.value)}
                          className="w-full p-1.5 rounded border border-[var(--card-border)] font-mono text-xs bg-[var(--card-bg)] focus:outline-none focus:border-[var(--brand-primary)]"
                        />
                      </div>

                      <div className="col-span-3">
                        <label className="block font-semibold text-[10px] mb-1 text-muted">Type</label>
                        <select
                          value={field.type}
                          onChange={(e) => updateFieldType(idx, e.target.value)}
                          className="w-full p-1.5 rounded border border-[var(--card-border)] text-xs bg-[var(--card-bg)] focus:outline-none"
                        >
                          <option value="string">String</option>
                          <option value="number">Number</option>
                          <option value="date">Date</option>
                          <option value="boolean">Boolean</option>
                          <option value="array">Array</option>
                        </select>
                      </div>

                      <div className="col-span-3">
                        <label className="block font-semibold text-[10px] mb-1 text-muted">Min Confidence</label>
                        <input
                          type="number"
                          step="0.05"
                          min="0.1"
                          max="1.0"
                          value={field.confidence_threshold ?? 0.8}
                          onChange={(e) => updateFieldThreshold(idx, parseFloat(e.target.value))}
                          className="w-full p-1.5 rounded border border-[var(--card-border)] font-mono text-xs bg-[var(--card-bg)] focus:outline-none"
                        />
                      </div>

                      <div className="col-span-2 flex items-center justify-end gap-2 pt-4">
                        <label className="flex items-center gap-1 cursor-pointer text-[10px] font-semibold text-muted">
                          <input
                            type="checkbox"
                            checked={field.required}
                            onChange={(e) => updateFieldRequired(idx, e.target.checked)}
                            className="accent-[var(--brand-primary)]"
                          />
                          Req
                        </label>
                        <button
                          onClick={() => removeField(idx)}
                          className="p-1 text-muted hover:text-red-500 rounded hover:bg-black/10 transition-colors"
                          title="Remove Field"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <input
                      type="text"
                      value={field.description}
                      onChange={(e) => updateFieldDescription(idx, e.target.value)}
                      placeholder="Field description / extraction hint"
                      className="w-full p-1.5 rounded border border-[var(--card-border)] text-[11px] bg-[var(--card-bg)] focus:outline-none focus:border-[var(--brand-primary)]"
                    />
                  </div>
                ))}

                <LttsButton variant="secondary" size="sm" onClick={addField}>
                  <Plus className="w-3.5 h-3.5" /> Add Field
                </LttsButton>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-[var(--card-border)] flex items-center justify-between shrink-0">
          <div className="text-[10px] text-muted">
            {generated
              ? 'Review the schema — click Apply to load it into the editor'
              : 'The AI generates a draft schema for you to review and refine'}
          </div>
          <div className="flex items-center gap-2">
            <LttsButton variant="tertiary" size="sm" onClick={onClose}>
              Cancel
            </LttsButton>
            {!generated && (
              <LttsButton
                variant="primary"
                size="sm"
                onClick={handleGenerate}
                disabled={!description.trim() || loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating…
                  </>
                ) : (
                  <>
                    <Wand2 className="w-3.5 h-3.5" /> Generate
                  </>
                )}
              </LttsButton>
            )}
            {generated && (
              <>
                <LttsButton
                  variant="secondary"
                  size="sm"
                  onClick={() => { setGenerated(null); setError(null); }}
                >
                  Start Over
                </LttsButton>
                <LttsButton variant="primary" size="sm" onClick={handleApply}>
                  <Check className="w-3.5 h-3.5" /> Apply to Editor
                </LttsButton>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
