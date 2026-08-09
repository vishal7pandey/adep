'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { Layers, Plus, Sparkles, Database, ArrowRight, ArrowLeft, CheckCircle2, Edit2, Trash2, Search, X } from 'lucide-react';
import { AgentDefinition, Skill, Template, fetchDefinitions, fetchSkills, fetchTemplates, createDefinition, updateDefinition, deleteDefinition, ApiError } from '@/lib/api';
import { LttsButton } from '@/components/ui/LttsButton';
import { LttsBadge } from '@/components/ui/LttsBadge';

export default function DefinitionsPage() {
  const [definitions, setDefinitions] = useState<AgentDefinition[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [showWizard, setShowWizard] = useState(false);
  const [editingDefId, setEditingDefId] = useState<string | null>(null);
  const [step, setStep] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredDefinitions = useMemo(() => {
    if (!searchQuery.trim()) return definitions;
    const q = searchQuery.toLowerCase();
    return definitions.filter(
      (def) =>
        def.name.toLowerCase().includes(q) ||
        def.id.toLowerCase().includes(q) ||
        (def.skill_id && def.skill_id.toLowerCase().includes(q)) ||
        (def.template_id && def.template_id.toLowerCase().includes(q)) ||
        (def.system_prompt && def.system_prompt.toLowerCase().includes(q))
    );
  }, [definitions, searchQuery]);

  // Wizard state
  const [defName, setDefName] = useState('');
  const [defDesc, setDefDesc] = useState('');
  const [selectedSkillId, setSelectedSkillId] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [selectedTools, setSelectedTools] = useState<string[]>(['paddle_ocr', 'crop_image']);
  const [systemPrompt, setSystemPrompt] = useState('High precision document metadata extraction.');
  const [maxIterations, setMaxIterations] = useState(15);

  useEffect(() => {
    fetchDefinitions().then(setDefinitions).catch((e) => { setDefinitions([]); setError(e instanceof ApiError ? `API Error ${e.status}: ${e.message}` : String(e)); });
    fetchSkills().then((s) => {
      setSkills(s);
      if (s.length > 0) setSelectedSkillId(s[0].id);
    }).catch((e) => {
      setSkills([]);
      setError((prev) => prev || (e instanceof ApiError ? `Skills fetch error ${e.status}: ${e.message}` : String(e)));
    });
    fetchTemplates().then((t) => {
      setTemplates(t);
      if (t.length > 0) setSelectedTemplateId(t[0].id);
    }).catch((e) => {
      setTemplates([]);
      setError((prev) => prev || (e instanceof ApiError ? `Templates fetch error ${e.status}: ${e.message}` : String(e)));
    });
  }, []);

  const handleOpenCreate = () => {
    setEditingDefId(null);
    setDefName('');
    setDefDesc('');
    if (skills.length > 0) setSelectedSkillId(skills[0].id);
    if (templates.length > 0) setSelectedTemplateId(templates[0].id);
    setSelectedTools(['paddle_ocr', 'crop_image']);
    setSystemPrompt('High precision document metadata extraction.');
    setMaxIterations(15);
    setStep(1);
    setShowWizard(true);
  };

  const handleOpenEdit = (def: AgentDefinition) => {
    setEditingDefId(def.id);
    setDefName(def.name);
    setDefDesc('');
    setSelectedSkillId(def.skill_id || def.skill_ref || (skills[0]?.id ?? ''));
    setSelectedTemplateId(def.template_id || def.template_ref || (templates[0]?.id ?? ''));
    setSystemPrompt(def.system_prompt || 'High precision document metadata extraction.');
    setMaxIterations(def.max_iterations || 15);
    setStep(1);
    setShowWizard(true);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this agent definition?')) return;

    try {
      await deleteDefinition(id);
      setDefinitions((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(`Failed to delete definition: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const toggleTool = (t: string) => {
    setSelectedTools((prev) => (prev.includes(t) ? prev.filter((item) => item !== t) : [...prev, t]));
  };

  const isStepValid = (): boolean => {
    switch (step) {
      case 1:
        return defName.trim().length > 0;
      case 2:
        return selectedSkillId.length > 0;
      case 3:
        return selectedTemplateId.length > 0;
      case 4:
        return selectedTools.length > 0;
      case 5:
        return systemPrompt.trim().length > 0;
      case 6:
        return maxIterations > 0 && maxIterations <= 50;
      case 7:
        return true;
      default:
        return false;
    }
  };

  const handleSaveDefinition = async () => {
    if (!isStepValid()) return;

    try {
      if (editingDefId) {
        const updated = await updateDefinition(editingDefId, {
          name: defName,
          skill_id: selectedSkillId,
          template_id: selectedTemplateId,
          system_prompt: systemPrompt,
          max_iterations: maxIterations,
        });
        setDefinitions((prev) => prev.map((d) => (d.id === editingDefId ? { ...d, ...updated } : d)));
      } else {
        const created = await createDefinition({
          name: defName,
          skill_id: selectedSkillId,
          template_id: selectedTemplateId,
          system_prompt: systemPrompt,
          max_iterations: maxIterations,
        });
        setDefinitions((prev) => [...prev, created]);
      }
      setShowWizard(false);
      setEditingDefId(null);
    } catch (err) {
      setError(`Failed to save definition: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="p-6 h-full overflow-y-auto bg-[var(--pane-bg)]">
      {/* Header with Standardized User-Facing Naming */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-[var(--pane-border)]">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2 text-[var(--primary-text)]">
            <Layers className="w-5 h-5 text-[#0071CE]" />
            Agent Definitions
          </h1>
          <p className="text-xs text-muted mt-1">View, create, and manage agent definitions</p>
        </div>
        <LttsButton variant="primary" onClick={handleOpenCreate}>
          <Plus className="w-4 h-4" /> Create Agent Definition
        </LttsButton>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg border border-[var(--status-error)] bg-[var(--status-error-subtle)] text-xs text-[var(--status-error)]">
          <strong>Failed to load agent definitions:</strong> {error}
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
          placeholder="Search agent definitions..."
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

      {/* Empty Search State */}
      {filteredDefinitions.length === 0 && (
        <div className="py-12 text-center space-y-2">
          <p className="text-sm font-medium text-[var(--primary-text)]">
            {searchQuery ? `No matches found for "${searchQuery}"` : 'No agent definitions available'}
          </p>
          <p className="text-xs text-muted">
            {searchQuery ? 'Try clearing your search query or using a different keyword.' : 'Click "Create Agent Definition" to build your first definition.'}
          </p>
        </div>
      )}

      {/* Available Agent Definitions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDefinitions.map((def) => {
          const matchedSkill = skills.find((s) => s.id === def.skill_id);
          const matchedTmpl = templates.find((t) => t.id === def.template_id);

          return (
            <div
              key={def.id}
              onClick={() => handleOpenEdit(def)}
              className="group relative p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] hover:border-[#0071CE] transition-all space-y-3 shadow-2xs cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-sm text-[var(--primary-text)] group-hover:text-[#0071CE] transition-colors">{def.name}</h3>
                  <span className="font-mono text-[10px] text-[#0071CE]">{def.id}</span>
                </div>

                <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleOpenEdit(def);
                    }}
                    className="p-1 text-muted hover:text-[var(--brand-primary)] hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors"
                    title="Edit Definition"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(def.id, e)}
                    className="p-1 text-muted hover:text-[var(--status-error)] hover:bg-red-500/10 rounded transition-colors"
                    title="Delete Definition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="text-xs text-muted space-y-1.5 font-mono p-2.5 rounded-lg bg-black/5 dark:bg-white/5 border border-[var(--pane-border)]">
                <div className="flex justify-between">
                  <span>Skill:</span>
                  <span className="text-[var(--primary-text)] font-semibold">{matchedSkill?.name || def.skill_id}</span>
                </div>
                <div className="flex justify-between">
                  <span>Template:</span>
                  <span className="text-[var(--primary-text)] font-semibold">{matchedTmpl?.name || def.template_id}</span>
                </div>
                <div className="flex justify-between">
                  <span>Max Cycles:</span>
                  <span className="text-[var(--primary-text)] font-semibold">{def.max_iterations || 15}</span>
                </div>
              </div>

              <p className="text-xs text-muted line-clamp-2">{def.system_prompt}</p>
            </div>
          );
        })}
      </div>

      {/* Build New Agent Wizard Modal */}
      {showWizard && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-[var(--pane-bg)] border border-[var(--pane-border)] rounded-xl w-full max-w-2xl p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
            {/* Wizard Header */}
            <div className="flex items-center justify-between border-b border-[var(--pane-border)] pb-3">
              <div>
                <h2 className="font-bold text-base flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[#0071CE]" /> {editingDefId ? 'Edit Agent Definition' : 'Create Agent Definition'}
                </h2>
                <p className="text-xs text-muted">Step {step} of 7</p>
              </div>
              <LttsButton variant="tertiary" size="sm" onClick={() => setShowWizard(false)}>
                Cancel
              </LttsButton>
            </div>

            {/* Step 1: Name & Description */}
            {step === 1 && (
              <div className="space-y-4 text-xs">
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">Name & Description</h3>
                <div>
                  <label className="block font-medium mb-1">Agent Definition Name *</label>
                  <input
                    type="text"
                    required
                    value={defName}
                    onChange={(e) => setDefName(e.target.value)}
                    placeholder="e.g. Production Invoice Extraction Agent Definition"
                    className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 focus:outline-none focus:border-[#0071CE]"
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">Description</label>
                  <textarea
                    value={defDesc}
                    onChange={(e) => setDefDesc(e.target.value)}
                    rows={3}
                    placeholder="Agent definition purpose and scope"
                    className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Step 2: Skill Cards Grid */}
            {step === 2 && (
              <div className="space-y-3 text-xs">
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">Select Reasoning Skill *</h3>
                <div className="grid grid-cols-1 gap-3">
                  {skills.map((s) => {
                    const isSelected = selectedSkillId === s.id;
                    return (
                      <div
                        key={s.id}
                        onClick={() => setSelectedSkillId(s.id)}
                        className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2 ${
                          isSelected
                            ? 'border-[#0071CE] bg-[#0071CE]/10 ring-2 ring-[#0071CE]/40'
                            : 'border-[var(--card-border)] bg-[var(--card-bg)] hover:border-[#0071CE]/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-xs">{s.name}</h4>
                          {s.semantic_checks_enabled && <LttsBadge variant="verified">Semantic Check</LttsBadge>}
                        </div>
                        <p className="text-muted text-[11px]">{s.description}</p>
                        <div className="flex gap-1 pt-1">
                          {s.tools?.map((t) => (
                            <LttsBadge key={t} variant="tool">
                              {t}
                            </LttsBadge>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 3: Template Cards Grid */}
            {step === 3 && (
              <div className="space-y-3 text-xs">
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">Select Schema Template *</h3>
                <div className="grid grid-cols-1 gap-3">
                  {templates.map((t) => {
                    const isSelected = selectedTemplateId === t.id;
                    return (
                      <div
                        key={t.id}
                        onClick={() => setSelectedTemplateId(t.id)}
                        className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2 ${
                          isSelected
                            ? 'border-[#0071CE] bg-[#0071CE]/10 ring-2 ring-[#0071CE]/40'
                            : 'border-[var(--card-border)] bg-[var(--card-bg)] hover:border-[#0071CE]/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-xs">{t.name}</h4>
                          <LttsBadge variant="info">{t.fields.length} Fields</LttsBadge>
                        </div>
                        <p className="text-muted text-[11px]">{t.description}</p>
                        <div className="font-mono text-[10px] text-muted pt-1">
                          Fields: {t.fields.map((f) => f.name).join(', ')}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 4: Tool Multi-Select Chips */}
            {step === 4 && (
              <div className="space-y-3 text-xs">
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">Tool Preferences *</h3>
                <div className="flex flex-wrap gap-2 pt-2">
                  {['paddle_ocr', 'tesseract', 'crop_image', 'outcome_validator', 'azure_vlm', 'deskew'].map((t) => {
                    const isSelected = selectedTools.includes(t);
                    return (
                      <button
                        type="button"
                        key={t}
                        onClick={() => toggleTool(t)}
                        className={`px-3 py-1.5 rounded-full border text-xs font-semibold transition-all ${
                          isSelected
                            ? 'bg-[#A27CC9] text-white border-[#A27CC9] shadow-2xs'
                            : 'bg-black/5 dark:bg-white/5 border-[var(--card-border)] text-muted'
                        }`}
                      >
                        {t}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 5: System Prompt */}
            {step === 5 && (
              <div className="space-y-3 text-xs">
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">System Prompt Override *</h3>
                <textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  rows={4}
                  className="w-full p-3 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 font-mono text-xs focus:outline-none"
                />
              </div>
            )}

            {/* Step 6: Max Iterations */}
            {step === 6 && (
              <div className="space-y-3 text-xs">
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">Max Iterations Cap *</h3>
                <input
                  type="number"
                  value={maxIterations}
                  onChange={(e) => setMaxIterations(Number(e.target.value))}
                  min={1}
                  max={50}
                  className="w-full p-2.5 rounded-lg border border-[var(--card-border)] bg-black/5 dark:bg-black/20 font-mono text-xs focus:outline-none"
                />
              </div>
            )}

            {/* Step 7: Review & Save */}
            {step === 7 && (
              <div className="space-y-3 text-xs">
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">
                  {editingDefId ? 'Review & Save Changes' : 'Review & Create Agent Definition'}
                </h3>
                <div className="p-4 rounded-xl border border-[var(--card-border)] bg-black/5 dark:bg-white/5 space-y-2 font-mono">
                  <div>Name: <span className="font-bold text-[#0071CE]">{defName || 'Untitled Agent Definition'}</span></div>
                  <div>Skill: <span className="font-bold">{selectedSkillId}</span></div>
                  <div>Template: <span className="font-bold">{selectedTemplateId}</span></div>
                  <div>Tools: <span className="font-bold">{selectedTools.join(', ')}</span></div>
                  <div>Max Cycles: <span className="font-bold">{maxIterations}</span></div>
                </div>
              </div>
            )}

            {/* Wizard Footer Navigation with Per-Step Validation */}
            <div className="flex justify-between border-t border-[var(--pane-border)] pt-4">
              <LttsButton
                variant="tertiary"
                onClick={() => setStep((prev) => Math.max(prev - 1, 1))}
                disabled={step === 1}
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </LttsButton>

              {step < 7 ? (
                <LttsButton
                  variant="primary"
                  onClick={() => setStep((prev) => Math.min(prev + 1, 7))}
                  disabled={!isStepValid()}
                >
                  Next <ArrowRight className="w-3.5 h-3.5" />
                </LttsButton>
              ) : (
                <LttsButton
                  variant="primary"
                  onClick={handleSaveDefinition}
                  disabled={!isStepValid()}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> {editingDefId ? 'Save Changes' : 'Create Agent Definition'}
                </LttsButton>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
