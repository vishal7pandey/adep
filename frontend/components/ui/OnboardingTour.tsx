'use client';

import React, { useState, useEffect } from 'react';
import { Sparkles, ArrowRight, ArrowLeft, X, Check, HelpCircle } from 'lucide-react';
import { AdeButton } from './AdeButton';

export interface TourStep {
  target: string; // CSS selector or identifier
  title: string;
  description: string;
  position: 'center' | 'top' | 'bottom' | 'left' | 'right';
}

const TOUR_STEPS: TourStep[] = [
  {
    target: 'center',
    title: 'Welcome to ADEP Workbench! 🚀',
    description:
      'The Agentic Document Extraction Platform provides local-first, high-precision document metadata extraction with real-time trace logging and visual source grounding.',
    position: 'center',
  },
  {
    target: 'sidebar',
    title: 'Step 1: Navigation & Registry',
    description:
      'Manage extraction sessions, explore Agent Definitions, customize Skills, and configure extraction Schemas from the left navigation bar.',
    position: 'right',
  },
  {
    target: 'pane-1',
    title: 'Step 2: Extraction Agent Definition Console',
    description:
      'Select your Extraction Agent Definition, upload documents, and observe the live reasoning trace, tool calls, and human-in-the-loop approval gates.',
    position: 'bottom',
  },
  {
    target: 'pane-2',
    title: 'Step 3: Structured Extracted Data',
    description:
      'Extracted key-value pairs appear here in real-time with confidence scores. Edit values, copy fields, or export data in JSON, CSV, or Spreadsheet formats.',
    position: 'bottom',
  },
  {
    target: 'pane-3',
    title: 'Step 4: Interactive Document Canvas',
    description:
      'View your source document with bounding-box highlights. Clicking any field in Pane 2 automatically focuses and highlights its exact location on the document canvas.',
    position: 'left',
  },
  {
    target: 'center',
    title: 'You are all set! 🎉',
    description:
      'You can re-trigger this onboarding tour anytime from the Command Palette (⌘K / Ctrl+K) or by pressing ? for keyboard shortcuts.',
    position: 'center',
  },
];

export const OnboardingTour: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  useEffect(() => {
    // First-run check
    const seen = localStorage.getItem('adep_tour_seen');
    if (!seen) {
      setIsOpen(true);
    }

    // Listen for manual re-trigger event
    const handleStartTour = () => {
      setCurrentStep(0);
      setIsOpen(true);
    };

    window.addEventListener('start-onboarding-tour', handleStartTour);
    return () => window.removeEventListener('start-onboarding-tour', handleStartTour);
  }, []);

  if (!isOpen) return null;

  const step = TOUR_STEPS[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === TOUR_STEPS.length - 1;

  const handleNext = () => {
    if (isLast) {
      handleClose();
    } else {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    setCurrentStep((prev) => Math.max(0, prev - 1));
  };

  const handleClose = () => {
    localStorage.setItem('adep_tour_seen', 'true');
    setIsOpen(false);
  };

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div
        className="w-full max-w-lg bg-[var(--pane-bg)] border border-[var(--brand-primary)] rounded-2xl shadow-2xl overflow-hidden space-y-0 animate-scaleUp"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="px-5 py-3.5 bg-[var(--brand-primary-subtle)] border-b border-[var(--pane-border)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[var(--brand-primary)] text-white flex items-center justify-center font-bold text-xs shadow-2xs">
              {currentStep + 1}
            </div>
            <span className="font-semibold text-xs text-[var(--brand-primary)] uppercase tracking-wider">
              Onboarding Guide ({currentStep + 1} / {TOUR_STEPS.length})
            </span>
          </div>

          <button
            onClick={handleClose}
            className="p-1 rounded-full text-muted hover:text-[var(--primary-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)]"
            aria-label="Close tour"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-[var(--brand-primary-subtle)] text-[var(--brand-primary)] shrink-0">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="space-y-1.5">
              <h2 className="font-bold text-base text-[var(--primary-text)]">{step.title}</h2>
              <p className="text-xs text-muted leading-relaxed">{step.description}</p>
            </div>
          </div>

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-1.5 pt-2">
            {TOUR_STEPS.map((_, idx) => (
              <div
                key={idx}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  idx === currentStep
                    ? 'w-6 bg-[var(--brand-primary)]'
                    : 'w-1.5 bg-black/20 dark:bg-white/20'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-black/5 dark:bg-white/5 border-t border-[var(--pane-border)] flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={dontShowAgain}
              onChange={(e) => setDontShowAgain(e.target.checked)}
              className="rounded border-[var(--pane-border)] text-[var(--brand-primary)] focus:ring-[var(--brand-primary)]"
            />
            <span>Don&apos;t show again</span>
          </label>

          <div className="flex items-center gap-2">
            {!isFirst && (
              <AdeButton variant="tertiary" size="sm" onClick={handlePrev}>
                <ArrowLeft className="w-3.5 h-3.5" /> Previous
              </AdeButton>
            )}
            <AdeButton variant="primary" size="sm" onClick={handleNext}>
              <span>{isLast ? 'Get Started' : 'Next Step'}</span>
              {!isLast && <ArrowRight className="w-3.5 h-3.5" />}
            </AdeButton>
          </div>
        </div>
      </div>
    </div>
  );
};
