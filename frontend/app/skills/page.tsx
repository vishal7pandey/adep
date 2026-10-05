'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { Sparkles, Plus, Check, Edit2, ArrowLeft, Search, X, Trash2 } from 'lucide-react';
import dynamic from 'next/dynamic';
import { Skill, fetchSkills, deleteSkill, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { FieldCardSkeleton } from '@/components/ui/SkeletonLoader';

const SkillEditorComponent = dynamic(
  () => import('@/components/skills/SkillEditor').then((mod) => mod.SkillEditorComponent),
  {
    loading: () => (
      <div className="p-6 space-y-4">
        <FieldCardSkeleton />
        <FieldCardSkeleton />
      </div>
    ),
  }
);

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchSkills().then(setSkills).catch((e) => { setSkills([]); setError(e instanceof ApiError ? `API Error ${e.status}: ${e.message}` : String(e)); });
  }, []);

  const filteredSkills = useMemo(() => {
    if (!searchQuery.trim()) return skills;
    const q = searchQuery.toLowerCase();
    return skills.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q) ||
        (s.description && s.description.toLowerCase().includes(q)) ||
        (s.tools && s.tools.some((t) => t.toLowerCase().includes(q)))
    );
  }, [skills, searchQuery]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this skill?')) return;

    try {
      await deleteSkill(id);
      setSkills((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setError(`Failed to delete skill: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (isEditing) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-3 bg-[var(--pane-bg)] border-b border-[var(--pane-border)] flex items-center gap-2">
          <Button
            variant="tertiary"
            size="sm"
            onClick={() => {
              setIsEditing(false);
              setEditingSkill(null);
            }}
          >
            <ArrowLeft className="w-4 h-4" /> Back to Registry
          </Button>
        </div>
        <div className="flex-1">
          <SkillEditorComponent
            initialSkill={editingSkill}
            onSaveComplete={() => {
              setIsEditing(false);
              fetchSkills().then(setSkills);
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
            <Sparkles className="w-5 h-5 text-[#0071CE]" />
            Skills Registry & Editor
          </h1>
          <p className="text-xs text-muted mt-1">Configure reasoning prompts, tool preferences, probe order, and pragmatic semantic checks</p>
        </div>
        <Button
          variant="primary"
          onClick={() => {
            setEditingSkill(null);
            setIsEditing(true);
          }}
        >
          <Plus className="w-4 h-4" /> Create Skill
        </Button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg border border-[var(--status-error)] bg-[var(--status-error-subtle)] text-xs text-[var(--status-error)]">
          <strong>Failed to load skills:</strong> {error}
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
          placeholder="Search skills..."
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
      {filteredSkills.length === 0 && (
        <div className="py-12 text-center space-y-2">
          <p className="text-sm font-medium text-[var(--primary-text)]">
            {searchQuery ? `No matches found for "${searchQuery}"` : 'No skills available'}
          </p>
          <p className="text-xs text-muted">
            {searchQuery ? 'Try clearing your search query or using a different keyword.' : 'Click "Create Skill" to configure your first skill.'}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredSkills.map((skill) => (
          <div
            key={skill.id}
            className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] space-y-3 shadow-2xs hover:border-[#0071CE] transition-all"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-sm text-[var(--primary-text)]">{skill.name}</h3>
                <p className="text-xs text-muted">{skill.description}</p>
              </div>

              <div className="flex items-center gap-2">
                {skill.semantic_checks_enabled && <Badge variant="verified">Semantic Check</Badge>}
                <Button
                  variant="tertiary"
                  size="sm"
                  onClick={() => {
                    setEditingSkill(skill);
                    setIsEditing(true);
                  }}
                >
                  <Edit2 className="w-3.5 h-3.5" /> Edit
                </Button>
                <button
                  onClick={(e) => handleDelete(skill.id, e)}
                  className="p-1.5 text-muted hover:text-[var(--status-error)] hover:bg-red-500/10 rounded transition-colors"
                  title="Delete Skill"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {skill.tools && (
              <div className="flex items-center gap-2 pt-1">
                <span className="text-[11px] text-muted font-medium">Tools:</span>
                <div className="flex flex-wrap gap-1">
                  {skill.tools.map((t) => (
                    <Badge key={t} variant="tool">
                      {t}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
