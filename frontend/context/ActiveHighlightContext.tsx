'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface HeatmapField {
  id: string;
  name: string;
  confidence: number;
  page: number;
  bbox: BBox;
}

interface ActiveHighlightContextType {
  activeBBox: BBox | null;
  activePage: number;
  activeFieldId: string | null;
  hoveredFieldId: string | null;
  heatmapEnabled: boolean;
  heatmapFields: HeatmapField[];
  setActiveHighlight: (bbox: BBox | null, page?: number, fieldId?: string | null) => void;
  setActiveBBox: (bbox: BBox | null) => void;
  setActivePage: (page: number) => void;
  setActiveFieldId: (id: string | null) => void;
  setHoveredFieldId: (id: string | null) => void;
  setHeatmapEnabled: (enabled: boolean) => void;
  setHeatmapFields: (fields: HeatmapField[]) => void;
  clearHighlight: () => void;
}

const ActiveHighlightContext = createContext<ActiveHighlightContextType | undefined>(undefined);

export const ActiveHighlightProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [activeBBox, setActiveBBox] = useState<BBox | null>(null);
  const [activePage, setActivePage] = useState<number>(1);
  const [activeFieldId, setActiveFieldId] = useState<string | null>(null);
  const [hoveredFieldId, setHoveredFieldId] = useState<string | null>(null);
  const [heatmapEnabled, setHeatmapEnabled] = useState(false);
  const [heatmapFields, setHeatmapFields] = useState<HeatmapField[]>([]);

  const setActiveHighlight = (bbox: BBox | null, page = 1, fieldId: string | null = null) => {
    setActiveBBox(bbox);
    setActivePage(page);
    setActiveFieldId(fieldId);
  };

  const clearHighlight = () => {
    setActiveBBox(null);
    setActiveFieldId(null);
    setHoveredFieldId(null);
  };

  return (
    <ActiveHighlightContext.Provider
      value={{
        activeBBox,
        activePage,
        activeFieldId,
        hoveredFieldId,
        heatmapEnabled,
        heatmapFields,
        setActiveHighlight,
        setActiveBBox,
        setActivePage,
        setActiveFieldId,
        setHoveredFieldId,
        setHeatmapEnabled,
        setHeatmapFields,
        clearHighlight,
      }}
    >
      {children}
    </ActiveHighlightContext.Provider>
  );
};

export const useActiveHighlight = (): ActiveHighlightContextType => {
  const context = useContext(ActiveHighlightContext);
  if (!context) {
    throw new Error('useActiveHighlight must be used within an ActiveHighlightProvider');
  }
  return context;
};
