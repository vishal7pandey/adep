'use client';

import React from 'react';
import { Keyboard, X, Command } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const shortcuts = [
    { key: '⌘ K / Ctrl K', description: 'Open Global Command Palette' },
    { key: '?', description: 'Toggle Keyboard Shortcuts Modal' },
    { key: 'Space', description: 'Pause / Resume active extraction run' },
    { key: '1', description: 'Set Disclosure Level 1 (Summary)' },
    { key: '2', description: 'Set Disclosure Level 2 (Detailed)' },
    { key: '3', description: 'Set Disclosure Level 3 (Expert)' },
    { key: 'Esc', description: 'Close modals, menus, and dropdowns' },
    { key: 'Tab', description: 'Cycle focus through interactive elements' },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div
        className="w-full max-w-md bg-[var(--pane-bg)] border border-[var(--pane-border)] rounded-xl shadow-2xl overflow-hidden animate-slideDown"
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-title"
      >
        <div className="px-4 py-3 border-b border-[var(--pane-border)] flex items-center justify-between bg-black/5 dark:bg-white/5">
          <div className="flex items-center gap-2 font-bold text-sm text-[var(--primary-text)]">
            <Keyboard className="w-4 h-4 text-[var(--brand-primary)]" />
            <h2 id="shortcuts-title">Keyboard Shortcuts</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-muted hover:text-[var(--primary-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)]"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-2 max-h-[60vh] overflow-y-auto">
          {shortcuts.map((s, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-black/5 dark:hover:bg-white/5 text-xs"
            >
              <span className="text-[var(--primary-text)] font-medium">{s.description}</span>
              <kbd className="px-2 py-0.5 rounded bg-black/10 dark:bg-white/10 font-mono text-[10px] font-bold text-muted border border-black/10 dark:border-white/10 shadow-2xs">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="px-4 py-2 border-t border-[var(--pane-border)] text-center text-[10px] text-muted bg-black/5 dark:bg-white/5">
          Press <kbd className="px-1 py-0.5 rounded bg-black/10 dark:bg-white/10 font-mono font-bold">Esc</kbd> anytime to close
        </div>
      </div>
    </div>
  );
};
