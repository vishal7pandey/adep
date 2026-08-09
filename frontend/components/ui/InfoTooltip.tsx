'use client';

import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface InfoTooltipProps {
  text: string;
}

export const InfoTooltip: React.FC<InfoTooltipProps> = ({ text }) => {
  const [show, setShow] = useState(false);

  return (
    <div className="relative inline-flex items-center ml-1">
      <button
        type="button"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="text-muted hover:text-[var(--brand-primary)] transition-colors focus:outline-none"
        title={text}
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>

      {show && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-48 p-2 rounded-lg bg-[var(--card-bg)] border border-[var(--card-border)] text-[var(--primary-text)] text-[10px] font-normal leading-tight shadow-xl z-50 pointer-events-none animate-fadeIn">
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[var(--card-bg)]" />
        </div>
      )}
    </div>
  );
};
