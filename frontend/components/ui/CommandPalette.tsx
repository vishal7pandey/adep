'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Search, 
  FileText, 
  Layers, 
  Sparkles, 
  Database, 
  Plus, 
  Moon, 
  Sun, 
  ArrowRight, 
  CornerDownLeft,
  Command,
  GitCompare
} from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { useWorkbench } from '@/context/WorkbenchContext';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  category: 'action' | 'navigation' | 'session' | 'setting';
  action: () => void;
  keywords?: string[];
}

export const CommandPalette: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const { reset } = useWorkbench();

  const commands: CommandItem[] = [
    {
      id: 'new-session',
      label: 'New Extraction Session',
      description: 'Start a blank extraction session',
      icon: <Plus className="w-4 h-4 text-[var(--brand-primary)]" />,
      category: 'action',
      action: () => { reset(); router.push('/'); },
      keywords: ['new', 'create', 'start', 'session', 'extract'],
    },
    {
      id: 'onboarding-tour',
      label: 'Take Onboarding Tour',
      description: 'Start the interactive 6-step ADEP Workbench guide',
      icon: <Sparkles className="w-4 h-4 text-[var(--brand-primary)]" />,
      category: 'action',
      action: () => {
        window.dispatchEvent(new Event('start-onboarding-tour'));
      },
      keywords: ['onboarding', 'tour', 'guide', 'help', 'tutorial', 'welcome'],
    },
    {
      id: 'compare-runs',
      label: 'Compare Extraction Runs',
      description: 'Side-by-side run diff comparison and confidence delta analysis',
      icon: <GitCompare className="w-4 h-4 text-[var(--brand-primary)]" />,
      category: 'action',
      action: () => {
        router.push('/?view=compare');
      },
      keywords: ['compare', 'diff', 'runs', 'side-by-side', 'delta', 'eval'],
    },
    {
      id: 'nav-home',
      label: 'Go to Workbench',
      description: 'Open the main extraction workbench',
      icon: <FileText className="w-4 h-4 text-[var(--brand-primary)]" />,
      category: 'navigation',
      action: () => router.push('/'),
      keywords: ['home', 'workbench', 'main', 'pane'],
    },
    {
      id: 'nav-agents',
      label: 'Choose Agent',
      description: 'Browse and select extraction agents',
      icon: <Layers className="w-4 h-4 text-[var(--brand-primary)]" />,
      category: 'navigation',
      action: () => router.push('/definitions'),
      keywords: ['agent', 'definition', 'choose', 'select', 'browse'],
    },
    {
      id: 'nav-skills',
      label: 'Skills Library',
      description: 'Manage reasoning skills and tool configurations',
      icon: <Sparkles className="w-4 h-4 text-[var(--brand-primary)]" />,
      category: 'navigation',
      action: () => router.push('/skills'),
      keywords: ['skill', 'library', 'tool', 'reasoning'],
    },
    {
      id: 'nav-templates',
      label: 'Schema Templates',
      description: 'Manage document extraction schema templates',
      icon: <Database className="w-4 h-4 text-[var(--brand-primary)]" />,
      category: 'navigation',
      action: () => router.push('/templates'),
      keywords: ['template', 'schema', 'field', 'structure'],
    },
    {
      id: 'toggle-theme',
      label: theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode',
      description: 'Toggle the application color theme',
      icon: theme === 'light' ? <Moon className="w-4 h-4 text-[var(--status-warning)]" /> : <Sun className="w-4 h-4 text-[var(--status-warning)]" />,
      category: 'setting',
      action: toggleTheme,
      keywords: ['theme', 'dark', 'light', 'mode', 'toggle', 'color'],
    },
  ];

  const filteredCommands = query.trim()
    ? commands.filter((cmd) => {
        const q = query.toLowerCase();
        return (
          cmd.label.toLowerCase().includes(q) ||
          cmd.description?.toLowerCase().includes(q) ||
          cmd.keywords?.some((kw) => kw.includes(q))
        );
      })
    : commands;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Open: Ctrl+K / Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
        setQuery('');
        setSelectedIndex(0);
        return;
      }

      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        setIsOpen(false);
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        return;
      }

      if (e.key === 'Enter' && filteredCommands[selectedIndex]) {
        e.preventDefault();
        filteredCommands[selectedIndex].action();
        setIsOpen(false);
        return;
      }
    },
    [isOpen, filteredCommands, selectedIndex]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) return null;

  const categoryLabel: Record<string, string> = {
    action: 'Actions',
    navigation: 'Navigate',
    session: 'Sessions',
    setting: 'Settings',
  };

  // Group by category
  const grouped: Record<string, CommandItem[]> = {};
  for (const cmd of filteredCommands) {
    if (!grouped[cmd.category]) grouped[cmd.category] = [];
    grouped[cmd.category].push(cmd);
  }

  let flatIndex = 0;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
        onClick={() => setIsOpen(false)}
      />

      {/* Palette */}
      <div className="relative w-full max-w-lg bg-[var(--pane-bg)] border border-[var(--pane-border)] rounded-xl shadow-2xl overflow-hidden animate-slideDown">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--pane-border)]">
          <Search className="w-4.5 h-4.5 text-muted shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search…"
            className="flex-1 bg-transparent text-sm font-medium focus:outline-none placeholder:text-muted"
          />
          <kbd className="px-1.5 py-0.5 rounded bg-black/10 dark:bg-white/10 text-[10px] font-mono text-muted">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-72 overflow-y-auto py-2">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-6 text-center text-muted text-xs">
              No commands match &quot;{query}&quot;
            </div>
          ) : (
            Object.entries(grouped).map(([cat, items]) => (
              <div key={cat}>
                <div className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-muted">
                  {categoryLabel[cat] || cat}
                </div>
                {items.map((cmd) => {
                  const thisIndex = flatIndex++;
                  const isSelected = thisIndex === selectedIndex;

                  return (
                    <button
                      key={cmd.id}
                      onClick={() => {
                        cmd.action();
                        setIsOpen(false);
                      }}
                      onMouseEnter={() => setSelectedIndex(thisIndex)}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                        isSelected
                          ? 'bg-[var(--brand-primary-subtle)] text-[var(--primary-text)]'
                          : 'text-[var(--primary-text)] hover:bg-black/5 dark:hover:bg-white/5'
                      }`}
                    >
                      <div className="shrink-0">{cmd.icon}</div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold">{cmd.label}</div>
                        {cmd.description && (
                          <div className="text-[10px] text-muted truncate">{cmd.description}</div>
                        )}
                      </div>
                      {isSelected && (
                        <CornerDownLeft className="w-3.5 h-3.5 text-muted shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer Hints */}
        <div className="px-4 py-2 border-t border-[var(--pane-border)] flex items-center justify-between text-[10px] text-muted bg-black/5 dark:bg-white/5">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-black/10 dark:bg-white/10 font-mono">↑↓</kbd> Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-black/10 dark:bg-white/10 font-mono">↵</kbd> Select
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-black/10 dark:bg-white/10 font-mono">Esc</kbd> Close
            </span>
          </div>
          <span className="flex items-center gap-1">
            <Command className="w-3 h-3" />
            <span>ADEP Command Palette</span>
          </span>
        </div>
      </div>
    </div>
  );
};
