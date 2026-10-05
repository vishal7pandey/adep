'use client';

import React, { useState } from 'react';
import { Sparkles, Save, Copy, Plus, Trash2, ArrowUp, ArrowDown, Sliders } from 'lucide-react';
import { Skill, createSkill, updateSkill } from '@/lib/api';
import { Button } from '@/components/ui/Button';

interface ProbeOrderStep {
  id: string;
  rationale: string;
  action: string;
}

interface InvariantRule {
  id: string;
  fieldName: string;
  type: 'date_compare' | 'numeric_tolerance' | 'coverage_loop' | 'sum_check';
  params: string;
}

interface FailureActionRule {
  id: string;
  condition: string;
  action: 'crop' | 'deskew' | 'denoise' | 'threshold' | 'vlm_escalation';
}

const DOCUMENT_TYPE_PRESETS: Record<string, { prompt: string; tools: string[]; ai: boolean }> = {
  Invoice: {
    prompt: 'Extract vendor name, invoice number, billing date, subtotal, tax amount, and grand total. Validate that subtotal + tax = grand total.',
    tools: ['paddle_ocr', 'crop_image', 'outcome_validator', 'azure_vlm'],
    ai: true,
  },
  Receipt: {
    prompt: 'Extract store name, transaction date, line item totals, and total paid from point-of-sale receipt image.',
    tools: ['paddle_ocr', 'crop_image', 'outcome_validator'],
    ai: false,
  },
  Contract: {
    prompt: 'Extract contracting parties, effective date, expiration date, governing law, and key clauses.',
    tools: ['paddle_ocr', 'crop_image', 'azure_vlm'],
    ai: true,
  },
  'Bank Statement': {
    prompt: 'Extract account holder name, account number, statement period, starting balance, ending balance, and transactions table.',
    tools: ['paddle_ocr', 'crop_image', 'outcome_validator', 'read_table'],
    ai: true,
  },
  Custom: {
    prompt: 'Inspect document and extract requested fields with precision.',
    tools: ['paddle_ocr', 'crop_image', 'outcome_validator'],
    ai: false,
  },
};

export const SkillEditorComponent: React.FC<{ initialSkill?: Skill | null; onSaveComplete?: () => void }> = ({
  initialSkill,
  onSaveComplete,
}) => {
  const [editorMode, setEditorMode] = useState<'simple' | 'advanced'>('simple');
  const [editingSkillId, setEditingSkillId] = useState<string | null>(initialSkill?.id || null);
  const [documentType, setDocumentType] = useState<string>('Invoice');

  // Form State
  const [name, setName] = useState(initialSkill?.name || '');
  const [description, setDescription] = useState(initialSkill?.description || '');
  const [systemPrompt, setSystemPrompt] = useState(initialSkill?.system_prompt || DOCUMENT_TYPE_PRESETS.Invoice.prompt);
  const [selectedTools, setSelectedTools] = useState<string[]>(initialSkill?.tools || DOCUMENT_TYPE_PRESETS.Invoice.tools);

  // Validation Checkboxes (Simple Mode)
  const [verifyAi, setVerifyAi] = useState(initialSkill?.semantic_checks_enabled ?? true);
  const [semanticPrompt, setSemanticPrompt] = useState(initialSkill?.semantic_prompt || 'Verify extracted total matches sum of line items.');

  // Advanced Mode State initialized from initialSkill if present
  const [probeSteps, setProbeSteps] = useState<ProbeOrderStep[]>(() => {
    if (initialSkill?.probe_order && Array.isArray(initialSkill.probe_order)) {
      return initialSkill.probe_order.map((item: any, idx: number) => {
        if (Array.isArray(item)) {
          return { id: String(idx + 1), action: item[0] || '', rationale: item[1] || '' };
        }
        return { id: item.id || String(idx + 1), action: item.action || '', rationale: item.rationale || '' };
      });
    }
    return [
      { id: '1', rationale: 'Initial full page text scan', action: 'Run OCR on page 1' },
      { id: '2', rationale: 'Inspect low confidence regions', action: 'Crop bbox and validate values' },
    ];
  });

  const [invariants, setInvariants] = useState<InvariantRule[]>(() => {
    if (initialSkill?.invariants && Array.isArray(initialSkill.invariants)) {
      return initialSkill.invariants.map((inv: any, idx: number) => ({
        id: inv.id || `inv-${idx + 1}`,
        fieldName: inv.fieldName || inv.field || '',
        type: inv.type || 'sum_check',
        params: inv.params || '',
      }));
    }
    return [
      { id: 'inv-1', fieldName: 'total_amount', type: 'sum_check', params: 'subtotal + tax == total_amount' },
    ];
  });

  const [failureActions, setFailureActions] = useState<FailureActionRule[]>(() => {
    if (initialSkill?.failure_actions) {
      if (Array.isArray(initialSkill.failure_actions)) {
        return initialSkill.failure_actions.map((fa: any, idx: number) => ({
          id: fa.id || `fa-${idx + 1}`,
          condition: fa.condition || '',
          action: fa.action || 'vlm_escalation',
        }));
      }
      if (typeof initialSkill.failure_actions === 'object') {
        return Object.entries(initialSkill.failure_actions).map(([condition, action], idx) => ({
          id: `fa-${idx + 1}`,
          condition,
          action: action as any,
        }));
      }
    }
    return [
      { id: 'fa-1', condition: 'confidence < 0.6', action: 'vlm_escalation' },
    ];
  });

  const handleDocumentTypeChange = (type: string) => {
    setDocumentType(type);
    const preset = DOCUMENT_TYPE_PRESETS[type] || DOCUMENT_TYPE_PRESETS.Custom;
    setSystemPrompt(preset.prompt);
    setSelectedTools(preset.tools);
    setVerifyAi(preset.ai);
  };

  const toggleTool = (t: string) => {
    setSelectedTools((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  };

  const addProbeStep = () => {
    setProbeSteps((prev) => [
      ...prev,
      { id: crypto.randomUUID(), rationale: 'Custom step', action: 'Execute tool' },
    ]);
  };

  const deleteProbeStep = (id: string) => {
    setProbeSteps((prev) => prev.filter((s) => s.id !== id));
  };

  const moveProbeStep = (index: number, direction: 'up' | 'down') => {
    const newSteps = [...probeSteps];
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= newSteps.length) return;
    const temp = newSteps[index];
    newSteps[index] = newSteps[targetIdx];
    newSteps[targetIdx] = temp;
    setProbeSteps(newSteps);
  };

  const addInvariant = () => {
    setInvariants((prev) => [
      ...prev,
      { id: crypto.randomUUID(), fieldName: 'invoice_date', type: 'date_compare', params: 'date <= today' },
    ]);
  };

  const deleteInvariant = (id: string) => {
    setInvariants((prev) => prev.filter((i) => i.id !== id));
  };

  const addFailureAction = () => {
    setFailureActions((prev) => [
      ...prev,
      { id: crypto.randomUUID(), condition: 'ocr_error', action: 'deskew' },
    ]);
  };

  const deleteFailureAction = (id: string) => {
    setFailureActions((prev) => prev.filter((fa) => fa.id !== id));
  };

  const handleSave = async () => {
    if (!name || !documentType) return;

    // Convert frontend models to backend-expected shapes
    const failureActionsObj = Object.fromEntries(failureActions.map((fa) => [fa.condition, fa.action]));
    const probeOrderTuples = probeSteps.map((s) => [s.action, s.rationale]);

    const payload = {
      name,
      description,
      semantic_checks_enabled: verifyAi,
      semantic_prompt: semanticPrompt,
      tools: selectedTools,
      system_prompt: systemPrompt,
      probe_order: probeOrderTuples as any,
      invariants: invariants as any,
      failure_actions: failureActionsObj as any,
    };

    if (editingSkillId) {
      await updateSkill(editingSkillId, payload);
    } else {
      await createSkill(payload);
    }

    if (onSaveComplete) onSaveComplete();
  };

  const handleClone = () => {
    setName(`${name} (Copy)`);
    setEditingSkillId(null);
  };

  const isFormValid = name.trim().length > 0 && documentType.length > 0;

  return (
    <div className="h-full flex flex-col bg-[var(--pane-bg)] overflow-hidden">
      {/* Top Header */}
      <div className="px-6 py-4 border-b border-[var(--pane-border)] flex items-center justify-between bg-black/5 dark:bg-white/5 shrink-0">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2 text-[var(--primary-text)]">
            <Sparkles className="w-5 h-5 text-[var(--brand-primary)]" /> Skill Editor
          </h2>
          <p className="text-xs text-muted">Configure document reasoning instructions and extraction preferences</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Simple / Advanced Mode Selector */}
          <div className="flex items-center bg-black/10 dark:bg-white/10 p-0.5 rounded-lg text-xs font-semibold">
            <button
              onClick={() => setEditorMode('simple')}
              className={`px-3 py-1 rounded-md transition-colors ${
                editorMode === 'simple' ? 'bg-[var(--brand-primary)] text-white shadow-2xs' : 'text-muted'
              }`}
            >
              Simple Mode
            </button>
            <button
              onClick={() => setEditorMode('advanced')}
              className={`px-3 py-1 rounded-md transition-colors ${
                editorMode === 'advanced' ? 'bg-[var(--brand-primary)] text-white shadow-2xs' : 'text-muted'
              }`}
            >
              Advanced Mode
            </button>
          </div>

          <Button variant="tertiary" onClick={handleClone}>
            <Copy className="w-4 h-4" /> Clone Skill
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={!isFormValid}>
            <Save className="w-4 h-4" /> Save Skill
          </Button>
        </div>
      </div>

      {/* Main Body */}
      <div className="flex-1 p-6 overflow-y-auto max-w-3xl space-y-6 text-xs">
        {/* Simple Mode Sections */}
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-4 shadow-2xs">
            <h3 className="font-bold text-sm text-[var(--primary-text)]">1. Basic Information</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-semibold mb-1">Skill Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Standard Invoice Extraction Skill"
                  className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 focus:outline-none focus:border-[var(--brand-primary)]"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Document Type Preset *</label>
                <select
                  value={documentType}
                  onChange={(e) => handleDocumentTypeChange(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-[var(--pane-bg)] font-medium focus:outline-none focus:border-[var(--brand-primary)]"
                >
                  {Object.keys(DOCUMENT_TYPE_PRESETS).map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block font-semibold mb-1">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="High precision extraction skill for invoices and receipts"
                className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 focus:outline-none focus:border-[var(--brand-primary)]"
              />
            </div>
          </div>

          {/* System Prompt */}
          <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-[var(--primary-text)]">2. System Instructions Prompt</h3>

            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={4}
              className="w-full p-3 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 font-mono text-xs focus:outline-none"
            />
          </div>

          {/* Tools Selection */}
          <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-[var(--primary-text)]">3. Allowed Tools</h3>
            <div className="grid grid-cols-2 gap-3 pt-1">
              {[
                { id: 'paddle_ocr', label: 'OCR (Text Extraction)', desc: 'Extracts raw text blocks from document' },
                { id: 'crop_image', label: 'Visual Inspection (Crop Region)', desc: 'Crops specific region for detail check' },
                { id: 'outcome_validator', label: 'Outcome Validator (Field Rules)', desc: 'Validates extracted data invariants' },
                { id: 'azure_vlm', label: 'VLM Escalation (Vision LLM)', desc: 'Uses Vision LLM on complex visual regions' },
                { id: 'read_table', label: 'Table Reader', desc: 'Parses multi-row tabular data' },
                { id: 'deskew', label: 'Deskew / Denoise Image', desc: 'Preprocesses distorted document scans' },
              ].map((t) => {
                const isChecked = selectedTools.includes(t.id);
                return (
                  <label
                    key={t.id}
                    className={`flex items-start gap-2.5 p-3 rounded-lg border cursor-pointer transition-all ${
                      isChecked
                        ? 'border-[var(--brand-primary)] bg-[var(--brand-primary-subtle)]'
                        : 'border-[var(--card-border)] bg-black/5 dark:bg-white/5'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleTool(t.id)}
                      className="mt-0.5 accent-[var(--brand-primary)]"
                    />
                    <div>
                      <div className="font-semibold text-xs text-[var(--primary-text)]">{t.label}</div>
                      <div className="text-[10px] text-muted">{t.desc}</div>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Validation Rules */}
          <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-[var(--primary-text)]">4. Validation Options</h3>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={verifyAi}
                  onChange={(e) => setVerifyAi(e.target.checked)}
                  className="accent-[var(--brand-primary)]"
                />
                <span className="font-medium">AI verification (LLM pragmatic semantic check)</span>
              </label>
            </div>

            {verifyAi && (
              <div className="pt-2">
                <label className="block font-semibold mb-1 text-[var(--brand-primary)]">Semantic Verification Prompt</label>
                <textarea
                  value={semanticPrompt}
                  onChange={(e) => setSemanticPrompt(e.target.value)}
                  rows={2}
                  className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 font-mono text-xs focus:outline-none"
                />
              </div>
            )}
          </div>
        </div>

        {/* Collapsible Advanced Mode Sections */}
        {editorMode === 'advanced' && (
          <div className="space-y-4 pt-4 border-t-2 border-dashed border-[var(--pane-border)]">
            <h3 className="font-bold text-sm text-[var(--brand-primary)] flex items-center gap-1.5">
              <Sliders className="w-4 h-4" /> Advanced Configuration
            </h3>

            {/* Extraction Steps */}
            <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-xs">Extraction Steps (Probe Order)</h4>
                <Button variant="secondary" size="sm" onClick={addProbeStep}>
                  <Plus className="w-3.5 h-3.5" /> Add Step
                </Button>
              </div>

              <div className="space-y-2">
                {probeSteps.map((step, idx) => (
                  <div key={step.id} className="p-3 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-white/5 flex items-center gap-3">
                    <span className="font-bold font-mono text-[var(--brand-primary)]">#{idx + 1}</span>
                    <div className="flex-1 space-y-1">
                      <input
                        type="text"
                        value={step.rationale}
                        onChange={(e) => {
                          const val = e.target.value;
                          setProbeSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, rationale: val } : s)));
                        }}
                        className="w-full font-semibold bg-transparent focus:outline-none"
                      />
                      <input
                        type="text"
                        value={step.action}
                        onChange={(e) => {
                          const val = e.target.value;
                          setProbeSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, action: val } : s)));
                        }}
                        className="w-full font-mono text-muted text-[11px] bg-transparent focus:outline-none"
                      />
                    </div>

                    <div className="flex items-center gap-1">
                      <button onClick={() => moveProbeStep(idx, 'up')} className="p-1 hover:bg-black/10 rounded" title="Move up">
                        <ArrowUp className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => moveProbeStep(idx, 'down')} className="p-1 hover:bg-black/10 rounded" title="Move down">
                        <ArrowDown className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => deleteProbeStep(step.id)} className="p-1 hover:bg-red-500/20 rounded text-red-500" title="Delete step">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Validation Rules */}
            <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-xs">Validation Rules (Invariants)</h4>
                <Button variant="secondary" size="sm" onClick={addInvariant}>
                  <Plus className="w-3.5 h-3.5" /> Add Rule
                </Button>
              </div>

              <div className="space-y-2">
                {invariants.map((inv) => (
                  <div key={inv.id} className="p-3 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-white/5 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <input
                        type="text"
                        value={inv.fieldName}
                        onChange={(e) => {
                          const val = e.target.value;
                          setInvariants((prev) => prev.map((i) => (i.id === inv.id ? { ...i, fieldName: val } : i)));
                        }}
                        placeholder="Field name"
                        className="flex-1 p-1.5 font-mono font-semibold text-xs rounded border border-black/10 bg-[var(--pane-bg)] focus:outline-none focus:border-[var(--brand-primary)]"
                      />
                      <select
                        value={inv.type}
                        onChange={(e) => {
                          const val = e.target.value as InvariantRule['type'];
                          setInvariants((prev) => prev.map((i) => (i.id === inv.id ? { ...i, type: val } : i)));
                        }}
                        className="p-1.5 text-xs rounded border border-black/10 bg-[var(--pane-bg)] focus:outline-none focus:border-[var(--brand-primary)]"
                      >
                        <option value="date_compare">date_compare</option>
                        <option value="numeric_tolerance">numeric_tolerance</option>
                        <option value="coverage_loop">coverage_loop</option>
                        <option value="sum_check">sum_check</option>
                      </select>
                      <button onClick={() => deleteInvariant(inv.id)} className="p-1 hover:bg-red-500/20 rounded text-red-500" title="Delete rule">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <input
                      type="text"
                      value={inv.params}
                      onChange={(e) => {
                        const val = e.target.value;
                        setInvariants((prev) => prev.map((i) => (i.id === inv.id ? { ...i, params: val } : i)));
                      }}
                      placeholder="Rule expression"
                      className="w-full p-2 font-mono text-xs rounded border border-black/10 bg-[var(--pane-bg)] focus:outline-none"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Fallback Behavior */}
            <div className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-xs">Fallback Behavior (Failure Actions)</h4>
                <Button variant="secondary" size="sm" onClick={addFailureAction}>
                  <Plus className="w-3.5 h-3.5" /> Add Behavior
                </Button>
              </div>

              <div className="space-y-2">
                {failureActions.map((fa) => (
                  <div key={fa.id} className="p-3 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-white/5 flex items-center gap-2">
                    <input
                      type="text"
                      value={fa.condition}
                      onChange={(e) => {
                        const val = e.target.value;
                        setFailureActions((prev) => prev.map((item) => (item.id === fa.id ? { ...item, condition: val } : item)));
                      }}
                      placeholder="e.g. confidence < 0.6"
                      className="flex-1 p-1.5 font-mono text-xs rounded border border-black/10 bg-[var(--pane-bg)] focus:outline-none focus:border-[var(--brand-primary)]"
                    />
                    <select
                      value={fa.action}
                      onChange={(e) => {
                        const val = e.target.value as FailureActionRule['action'];
                        setFailureActions((prev) => prev.map((item) => (item.id === fa.id ? { ...item, action: val } : item)));
                      }}
                      className="p-1.5 text-xs rounded border border-black/10 bg-[var(--pane-bg)] focus:outline-none focus:border-[var(--brand-primary)]"
                    >
                      <option value="crop">crop</option>
                      <option value="deskew">deskew</option>
                      <option value="denoise">denoise</option>
                      <option value="threshold">threshold</option>
                      <option value="vlm_escalation">vlm_escalation</option>
                    </select>
                    <button onClick={() => deleteFailureAction(fa.id)} className="p-1 hover:bg-red-500/20 rounded text-red-500" title="Delete action">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
