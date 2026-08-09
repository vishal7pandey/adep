'use client';

import React, { useState, useEffect } from 'react';
import { KeyboardShortcutsModal } from './KeyboardShortcutsModal';

export const GlobalKeyboardShortcuts: React.FC = () => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore key events when user is typing in form inputs or textareas
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === '?' && !e.shiftKey) {
        // Shift+? or ? key
        e.preventDefault();
        setIsHelpOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:bg-[var(--brand-primary)] focus:text-white focus:px-3 focus:py-2 focus:rounded-md focus:z-[200] focus:shadow-lg text-xs font-bold"
      >
        Skip to main content
      </a>
      <KeyboardShortcutsModal isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
    </>
  );
};
