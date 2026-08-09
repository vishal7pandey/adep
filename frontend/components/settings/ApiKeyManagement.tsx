'use client';

import React, { useState, useEffect } from 'react';
import { Key, Plus, Trash2, Copy, Check, Shield, AlertTriangle, Eye, EyeOff, Lock, Sparkles } from 'lucide-react';
import { ApiKeyItem, getAuthHeaders } from '@/lib/api';
import { AdeButton } from '@/components/ui/AdeButton';
import { AdeBadge } from '@/components/ui/AdeBadge';

const SAMPLE_KEYS: ApiKeyItem[] = [
  {
    id: 'key_01',
    name: 'Production AP Automation Integration',
    key_prefix: 'adep_live_8f3a...',
    scopes: ['admin', 'extraction:write'],
    created_at: '2026-08-01T10:00:00Z',
    last_used_at: '2026-08-08T05:30:00Z',
    status: 'active',
  },
  {
    id: 'key_02',
    name: 'Staging Pipeline Read-Only',
    key_prefix: 'adep_live_1c9b...',
    scopes: ['read_only'],
    created_at: '2026-08-05T14:20:00Z',
    last_used_at: '2026-08-07T18:12:00Z',
    status: 'active',
  },
];

export const ApiKeyManagement: React.FC = () => {
  const [keys, setKeys] = useState<ApiKeyItem[]>(SAMPLE_KEYS);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRevealModal, setShowRevealModal] = useState(false);
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Form State
  const [keyName, setKeyName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['extraction:write']);

  // Session Key Connector State
  const [sessionKey, setSessionKey] = useState('');
  const [activeConnectedKey, setActiveConnectedKey] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = sessionStorage.getItem('adep_api_key');
      if (stored) setActiveConnectedKey(stored);
    }
  }, []);

  const handleConnectSessionKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionKey.trim()) return;
    sessionStorage.setItem('adep_api_key', sessionKey.trim());
    setActiveConnectedKey(sessionKey.trim());
    setSessionKey('');
  };

  const handleDisconnectSessionKey = () => {
    sessionStorage.removeItem('adep_api_key');
    setActiveConnectedKey(null);
  };

  const handleCreateKey = () => {
    if (!keyName.trim()) return;

    const rawKey = `adep_live_${crypto.randomUUID().replace(/-/g, '')}`;
    const newKeyItem: ApiKeyItem = {
      id: `key_${Date.now()}`,
      name: keyName.trim(),
      key_prefix: `${rawKey.substring(0, 14)}...`,
      scopes: selectedScopes,
      created_at: new Date().toISOString(),
      status: 'active',
    };

    setKeys((prev) => [newKeyItem, ...prev]);
    setCreatedRawKey(rawKey);
    setShowCreateModal(false);
    setShowRevealModal(true);
    setKeyName('');
  };

  const handleRevokeKey = (id: string) => {
    setKeys((prev) => prev.map((k) => (k.id === id ? { ...k, status: 'revoked' } : k)));
  };

  const handleCopyRawKey = () => {
    if (!createdRawKey) return;
    navigator.clipboard.writeText(createdRawKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="h-full flex flex-col bg-[var(--pane-bg)] overflow-hidden space-y-4 p-6">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-[var(--pane-border)] pb-4">
        <div>
          <h1 className="text-lg font-bold text-[var(--primary-text)] flex items-center gap-2">
            <Key className="w-5 h-5 text-[var(--brand-primary)]" /> API Key Management & Auth
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Manage Bearer tokens and session authentication for ADEP API endpoints.
          </p>
        </div>

        <AdeButton variant="primary" onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4" /> Create API Key
        </AdeButton>
      </div>

      {/* Active Session Connector Banner */}
      <div className="p-4 rounded-xl border border-[var(--brand-primary)] bg-[var(--brand-primary-subtle)] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xs text-[var(--brand-primary)]">
            <Lock className="w-4 h-4" />
            <span>Browser Tab Session Credential</span>
          </div>
          <AdeBadge variant={activeConnectedKey ? 'verified' : 'neutral'}>
            {activeConnectedKey ? 'Connected (sessionStorage)' : 'No Auth Key Attached'}
          </AdeBadge>
        </div>

        {activeConnectedKey ? (
          <div className="flex items-center justify-between text-xs">
            <span className="font-mono text-muted">
              Active Key: <strong className="text-[var(--primary-text)]">{activeConnectedKey.substring(0, 14)}...</strong>
            </span>
            <button
              onClick={handleDisconnectSessionKey}
              className="text-xs text-[var(--status-error)] hover:underline font-semibold"
            >
              Clear Session Credential
            </button>
          </div>
        ) : (
          <form onSubmit={handleConnectSessionKey} className="flex items-center gap-2">
            <input
              type="password"
              placeholder="Paste adep_live_... API key for this browser tab"
              value={sessionKey}
              onChange={(e) => setSessionKey(e.target.value)}
              className="flex-1 p-2 rounded-lg border border-[var(--pane-border)] bg-[var(--pane-bg)] font-mono text-xs focus:outline-none focus:border-[var(--brand-primary)]"
            />
            <AdeButton variant="primary" size="sm" type="submit" disabled={!sessionKey.trim()}>
              Attach Credential
            </AdeButton>
          </form>
        )}
      </div>

      {/* API Key List */}
      <div className="flex-1 overflow-y-auto space-y-3">
        <h2 className="font-bold text-sm text-[var(--primary-text)]">Active & Revoked API Keys</h2>
        {keys.map((k) => (
          <div
            key={k.id}
            className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] flex items-center justify-between shadow-2xs text-xs space-y-0"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-[var(--primary-text)]">{k.name}</span>
                <AdeBadge variant={k.status === 'active' ? 'verified' : 'failed'}>
                  {k.status === 'active' ? 'Active' : 'Revoked'}
                </AdeBadge>
              </div>

              <div className="flex items-center gap-3 text-muted text-[11px]">
                <span className="font-mono">{k.key_prefix}</span>
                <span>•</span>
                <span>Created {new Date(k.created_at).toLocaleDateString()}</span>
                {k.last_used_at && (
                  <>
                    <span>•</span>
                    <span>Last used {new Date(k.last_used_at).toLocaleTimeString()}</span>
                  </>
                )}
              </div>

              <div className="flex items-center gap-1.5 pt-1">
                {k.scopes.map((scope) => (
                  <span
                    key={scope}
                    className="px-2 py-0.5 rounded bg-black/10 dark:bg-white/10 text-[10px] font-mono font-semibold text-muted"
                  >
                    {scope}
                  </span>
                ))}
              </div>
            </div>

            {k.status === 'active' && (
              <button
                onClick={() => handleRevokeKey(k.id)}
                className="p-2 text-muted hover:text-[var(--status-error)] hover:bg-red-500/10 rounded-lg transition-colors"
                title="Revoke Key"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Create Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn">
          <div className="w-full max-w-md bg-[var(--pane-bg)] border border-[var(--pane-border)] rounded-2xl shadow-2xl p-6 space-y-4">
            <h2 className="font-bold text-base text-[var(--primary-text)]">Create New API Key</h2>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold mb-1">Key Name / Service Description</label>
                <input
                  type="text"
                  placeholder="e.g. ERP Ingestion Pipeline"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-[var(--pane-border)] bg-[var(--card-bg)] text-xs focus:outline-none focus:border-[var(--brand-primary)]"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Key Scopes & Permissions</label>
                <div className="space-y-1.5 pt-1">
                  {[
                    { id: 'admin', label: 'Admin (Full access)' },
                    { id: 'extraction:write', label: 'Extraction Write (Start runs, upload docs)' },
                    { id: 'read_only', label: 'Read Only (Fetch runs & fields)' },
                  ].map((s) => (
                    <label key={s.id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedScopes.includes(s.id)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedScopes([...selectedScopes, s.id]);
                          else setSelectedScopes(selectedScopes.filter((x) => x !== s.id));
                        }}
                        className="accent-[var(--brand-primary)]"
                      />
                      <span>{s.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--pane-border)]">
              <AdeButton variant="tertiary" onClick={() => setShowCreateModal(false)}>
                Cancel
              </AdeButton>
              <AdeButton variant="primary" onClick={handleCreateKey} disabled={!keyName.trim()}>
                Generate Key
              </AdeButton>
            </div>
          </div>
        </div>
      )}

      {/* One-Time Key Reveal Modal */}
      {showRevealModal && createdRawKey && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
          <div className="w-full max-w-lg bg-[var(--pane-bg)] border border-[var(--status-warning)] rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-[var(--status-warning)] font-bold text-sm">
              <AlertTriangle className="w-5 h-5" />
              <span>Save Your Secret API Key Now</span>
            </div>

            <p className="text-xs text-[var(--primary-text)] leading-relaxed">
              This secret key will <strong className="text-[var(--status-error)]">never be shown again</strong>. Copy it immediately and store it securely in your application configuration.
            </p>

            <div className="p-3 rounded-lg border border-[var(--pane-border)] bg-black/10 dark:bg-black/40 flex items-center justify-between font-mono text-xs">
              <span className="text-[var(--brand-primary)] font-bold break-all select-all">{createdRawKey}</span>
              <AdeButton variant="primary" size="sm" onClick={handleCopyRawKey}>
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy Key'}</span>
              </AdeButton>
            </div>

            <div className="flex justify-end pt-2">
              <AdeButton variant="primary" onClick={() => setShowRevealModal(false)}>
                Done (I have saved my key)
              </AdeButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
