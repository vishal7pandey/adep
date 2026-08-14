'use client';

import React, { useState, useEffect } from 'react';
import { Key, Plus, Trash2, Copy, Check, Shield, AlertTriangle, Eye, EyeOff, Lock, Sparkles, RefreshCw } from 'lucide-react';
import { ApiKeyItem, fetchApiKeys, createApiKey, deleteApiKey, ApiError } from '@/lib/api';
import { LttsButton } from '@/components/ui/LttsButton';
import { LttsBadge } from '@/components/ui/LttsBadge';

export const ApiKeyManagement: React.FC = () => {
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRevealModal, setShowRevealModal] = useState(false);
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Form State
  const [keyName, setKeyName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['admin']);

  // Session Key Connector State
  const [sessionKey, setSessionKey] = useState('');
  const [activeConnectedKey, setActiveConnectedKey] = useState<string | null>(null);

  const loadKeys = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchApiKeys();
      setKeys(data);
    } catch (err) {
      setKeys([]);
      setError(err instanceof ApiError ? `API Error ${err.status}: ${err.message}` : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = sessionStorage.getItem('adep_api_key');
      if (stored) setActiveConnectedKey(stored);
    }
    loadKeys();
  }, []);

  const handleConnectSessionKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionKey.trim()) return;
    sessionStorage.setItem('adep_api_key', sessionKey.trim());
    setActiveConnectedKey(sessionKey.trim());
    setSessionKey('');
    loadKeys();
  };

  const handleDisconnectSessionKey = () => {
    sessionStorage.removeItem('adep_api_key');
    setActiveConnectedKey(null);
    loadKeys();
  };

  const handleCreateKey = async () => {
    if (!keyName.trim()) return;
    setError(null);

    try {
      const resp = await createApiKey({
        name: keyName.trim(),
        scopes: selectedScopes,
      });

      setKeys((prev) => [resp, ...prev]);
      setCreatedRawKey(resp.secret);
      setShowCreateModal(false);
      setShowRevealModal(true);
      setKeyName('');
    } catch (err) {
      setError(`Failed to create API key: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!window.confirm('Are you sure you want to revoke this API key?')) return;
    setError(null);

    try {
      await deleteApiKey(keyId);
      setKeys((prev) => prev.map((k) => ((k.key_id || k.id) === keyId ? { ...k, active: false, status: 'revoked' } : k)));
    } catch (err) {
      setError(`Failed to revoke API key: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
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

        <div className="flex items-center gap-2">
          <LttsButton variant="tertiary" size="sm" onClick={loadKeys} disabled={isLoading}>
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </LttsButton>
          <LttsButton variant="primary" onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4" /> Create API Key
          </LttsButton>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg border border-[var(--status-error)] bg-[var(--status-error-subtle)] text-xs text-[var(--status-error)] flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold underline ml-2">Dismiss</button>
        </div>
      )}

      {/* Active Session Connector Banner */}
      <div className="p-4 rounded-xl border border-[var(--brand-primary)] bg-[var(--brand-primary-subtle)] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xs text-[var(--brand-primary)]">
            <Lock className="w-4 h-4" />
            <span>Browser Tab Session Credential</span>
          </div>
          <LttsBadge variant={activeConnectedKey ? 'verified' : 'neutral'}>
            {activeConnectedKey ? 'Connected (sessionStorage)' : 'No Auth Key Attached'}
          </LttsBadge>
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
            <LttsButton variant="primary" size="sm" type="submit" disabled={!sessionKey.trim()}>
              Attach Credential
            </LttsButton>
          </form>
        )}
      </div>

      {/* API Key List */}
      <div className="flex-1 overflow-y-auto space-y-3">
        <h2 className="font-bold text-sm text-[var(--primary-text)]">Active & Revoked API Keys</h2>
        {isLoading ? (
          <div className="py-8 text-center text-xs text-muted">Loading API keys...</div>
        ) : keys.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted border border-dashed border-[var(--pane-border)] rounded-xl">
            No API keys found on server. Click "Create API Key" above to generate one.
          </div>
        ) : (
          keys.map((k) => {
            const keyId = k.key_id || k.id || '';
            const isActive = k.active !== false && k.status !== 'revoked';

            return (
              <div
                key={keyId}
                className="p-4 rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] flex items-center justify-between shadow-2xs text-xs space-y-0"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-[var(--primary-text)]">{k.name}</span>
                    <LttsBadge variant={isActive ? 'verified' : 'failed'}>
                      {isActive ? 'Active' : 'Revoked'}
                    </LttsBadge>
                  </div>

                  <div className="flex items-center gap-3 text-muted text-[11px]">
                    <span className="font-mono">{k.key_prefix || (keyId ? `${keyId.substring(0, 12)}...` : '')}</span>
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

                {isActive && (
                  <button
                    onClick={() => handleRevokeKey(keyId)}
                    className="p-2 text-muted hover:text-[var(--status-error)] hover:bg-red-500/10 rounded-lg transition-colors"
                    title="Revoke Key"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            );
          })
        )}
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
              <LttsButton variant="tertiary" onClick={() => setShowCreateModal(false)}>
                Cancel
              </LttsButton>
              <LttsButton variant="primary" onClick={handleCreateKey} disabled={!keyName.trim()}>
                Generate Key
              </LttsButton>
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
              <LttsButton variant="primary" size="sm" onClick={handleCopyRawKey}>
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy Key'}</span>
              </LttsButton>
            </div>

            <div className="flex justify-end pt-2">
              <LttsButton variant="primary" onClick={() => setShowRevealModal(false)}>
                Done (I have saved my key)
              </LttsButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
