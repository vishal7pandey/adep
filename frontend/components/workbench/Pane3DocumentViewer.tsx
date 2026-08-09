'use client';

import React, { useState } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  RotateCw, 
  Maximize2, 
  FileText,
  Thermometer
} from 'lucide-react';
import { useActiveHighlight } from '@/context/ActiveHighlightContext';
import { useWorkbench } from '@/context/WorkbenchContext';
import { LttsButton } from '@/components/ui/LttsButton';

/**
 * Returns a confidence-based color for heatmap overlay.
 * Green (>0.9), Yellow (0.7-0.9), Red (<0.7)
 */
const getHeatmapColor = (confidence: number) => {
  if (confidence >= 0.9) return { fill: 'var(--heatmap-high-bg)', stroke: 'var(--status-success)', label: 'High' };
  if (confidence >= 0.7) return { fill: 'var(--heatmap-med-bg)', stroke: 'var(--status-warning)', label: 'Medium' };
  return { fill: 'var(--heatmap-low-bg)', stroke: 'var(--status-error)', label: 'Low' };
};

export const Pane3DocumentViewer: React.FC = () => {
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [hoveredHeatmapFieldId, setHoveredHeatmapFieldId] = useState<string | null>(null);

  const { activeBBox, activePage, setActivePage, heatmapEnabled, setHeatmapEnabled, heatmapFields, setActiveFieldId, setActiveBBox } = useActiveHighlight();
  const { documentFileName, documentUrl, runId } = useWorkbench();
  const totalPages = Math.max(1, ...heatmapFields.map((f) => f.page || 1));
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const isLikelyDocumentId =
    !!documentUrl
    && /^[a-zA-Z0-9_-]+$/.test(documentUrl)
    && !documentUrl.includes('.')
    && !documentUrl.includes('\\')
    && !documentUrl.includes('/');

  const isWebUrl = !!documentUrl && (documentUrl.startsWith('http://') || documentUrl.startsWith('https://'));
  const isApiRelativeUrl = !!documentUrl && documentUrl.startsWith('/api/');

  const previewUrl = isLikelyDocumentId
    ? `${apiBaseUrl}/documents/${encodeURIComponent(documentUrl || '')}/page/${activePage}`
    : (isWebUrl || isApiRelativeUrl)
      ? documentUrl
      : runId
        ? `${apiBaseUrl}/runs/${encodeURIComponent(runId)}/preview/${activePage}`
        : null;

  const handleZoomIn = () => setScale((prev) => Math.min(prev + 0.15, 2.5));
  const handleZoomOut = () => setScale((prev) => Math.max(prev - 0.15, 0.5));
  const handleResetZoom = () => setScale(1.0);
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);

  const prevPage = () => setActivePage(Math.max(activePage - 1, 1));
  const nextPage = () => setActivePage(Math.min(activePage + 1, totalPages));

  const pageHeatmapFields = heatmapFields.filter((f) => f.page === activePage);

  if (!documentFileName) {
    return (
      <div className="h-full flex items-center justify-center bg-[var(--pane-bg)]">
        <div className="text-center space-y-2 text-muted p-6">
          <FileText className="w-12 h-12 mx-auto opacity-30 text-[var(--brand-primary)]" />
          <p className="text-sm font-semibold">No document loaded</p>
          <p className="text-xs max-w-xs">Upload a document in Pane 1 to open the viewer.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[var(--pane-bg)] overflow-hidden">
      {/* Sticky Toolbar */}
      <div className="sticky top-0 z-10 bg-[var(--pane-bg)] border-b border-[var(--pane-border)] shadow-2xs">
        <div className="px-4 py-2 flex items-center justify-between bg-black/5 dark:bg-white/5">
          {/* Left Group: Page Navigation & Filename */}
          <div className="flex items-center gap-2">
            <LttsButton variant="tertiary" size="sm" onClick={prevPage} disabled={activePage <= 1}>
              <ChevronLeft className="w-4 h-4" />
            </LttsButton>
            <span className="font-mono text-xs font-semibold text-[var(--primary-text)]">
              Page {activePage} of {totalPages}
            </span>
            <LttsButton variant="tertiary" size="sm" onClick={nextPage} disabled={activePage >= totalPages}>
              <ChevronRight className="w-4 h-4" />
            </LttsButton>
            <span className="font-mono text-[11px] text-muted overflow-hidden text-ellipsis whitespace-nowrap max-w-[160px] pl-2 border-l border-black/10">
              {documentFileName}
            </span>
          </div>

          {/* Right Group: Heatmap Toggle, Zoom Controls & Rotation */}
          <div className="flex items-center gap-1.5">
            {/* BLK-115: Confidence Heatmap Toggle */}
            <button
              onClick={() => setHeatmapEnabled(!heatmapEnabled)}
              title={heatmapEnabled ? 'Hide Confidence Heatmap' : 'Show Confidence Heatmap'}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-semibold border transition-all duration-200 ${
                heatmapEnabled
                  ? 'bg-[var(--brand-primary-muted)] border-[var(--brand-primary)] text-[var(--brand-primary)] shadow-xs'
                  : 'bg-transparent border-transparent text-muted hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              <Thermometer className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Heatmap</span>
            </button>

            <div className="w-px h-4 bg-black/10 dark:bg-white/10 mx-0.5" />

            <LttsButton variant="tertiary" size="sm" onClick={handleZoomOut} title="Zoom Out">
              <ZoomOut className="w-4 h-4" />
            </LttsButton>
            <span className="font-mono text-xs text-muted w-12 text-center">
              {Math.round(scale * 100)}%
            </span>
            <LttsButton variant="tertiary" size="sm" onClick={handleZoomIn} title="Zoom In">
              <ZoomIn className="w-4 h-4" />
            </LttsButton>
            <LttsButton variant="tertiary" size="sm" onClick={handleResetZoom} title="Reset Zoom">
              <Maximize2 className="w-4 h-4" />
            </LttsButton>
            <LttsButton variant="tertiary" size="sm" onClick={handleRotate} title="Rotate 90°">
              <RotateCw className="w-4 h-4" />
            </LttsButton>
          </div>
        </div>

        {/* BLK-115: Heatmap Legend Bar */}
        {heatmapEnabled && pageHeatmapFields.length > 0 && (
          <div className="px-4 py-1.5 flex items-center justify-between bg-black/5 dark:bg-white/5 border-t border-[var(--pane-border)] text-[10px]">
            <span className="text-muted font-semibold">Confidence Overlay</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-[var(--status-success)]" />
                <span className="text-muted">High (&gt;90%)</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-[var(--status-warning)]" />
                <span className="text-muted">Med (70-90%)</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-[var(--status-error)]" />
                <span className="text-muted">Low (&lt;70%)</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Document Viewport with Bounding Box SVG Layer */}
      <div className="flex-1 p-6 overflow-auto flex items-center justify-center bg-black/10 dark:bg-black/40">
        <div
          className="relative bg-white shadow-2xl rounded transition-transform duration-200 ease-out border border-gray-300"
          style={{
            width: `${750 * scale}px`,
            height: `${950 * scale}px`,
            transform: `rotate(${rotation}deg)`,
          }}
        >
          {/* Dynamic Document Content View */}
          <div className="w-full h-full flex items-center justify-center select-none overflow-hidden bg-white">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt={documentFileName || 'Document preview'}
                className="max-w-full max-h-full object-contain"
                draggable={false}
              />
            ) : (
              <div className="text-center space-y-2 px-6">
                <FileText className="w-10 h-10 mx-auto text-gray-400" />
                <p className="text-sm font-semibold text-gray-800">{documentFileName}</p>
                <p className="text-xs text-gray-500">
                  Live preview is unavailable for this local path. Upload through Pane 1 for paged rendering.
                </p>
              </div>
            )}
          </div>

          {/* SVG Overlay Layer — Active BBox + Heatmap (BLK-115) */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-20">
            {/* BLK-115: Confidence Heatmap Overlays */}
            {heatmapEnabled && pageHeatmapFields.map((field) => {
              const color = getHeatmapColor(field.confidence);
              const isHovered = hoveredHeatmapFieldId === field.id;

              return (
                <g key={`heatmap-${field.id}`} className="pointer-events-auto cursor-pointer"
                  onMouseEnter={() => setHoveredHeatmapFieldId(field.id)}
                  onMouseLeave={() => setHoveredHeatmapFieldId(null)}
                  onClick={() => {
                    setActiveFieldId(field.id);
                    setActiveBBox(field.bbox);
                  }}
                >
                  <rect
                    x={field.bbox.x * scale}
                    y={field.bbox.y * scale}
                    width={field.bbox.width * scale}
                    height={field.bbox.height * scale}
                    fill={color.fill}
                    stroke={color.stroke}
                    strokeWidth={isHovered ? 2.5 : 1.5}
                    rx={3}
                    opacity={isHovered ? 1 : 0.85}
                    className="transition-all duration-200"
                  />
                  {/* Confidence label on hover */}
                  {isHovered && (
                    <>
                      <rect
                        x={field.bbox.x * scale}
                        y={(field.bbox.y - 18) * scale}
                        width={Math.max(field.name.length * 5.5 + 50, 80) * scale}
                        height={16 * scale}
                        fill={color.stroke}
                        rx={3}
                      />
                      <text
                        x={(field.bbox.x + 4) * scale}
                        y={(field.bbox.y - 6) * scale}
                        fill="white"
                        fontSize={10 * scale}
                        fontWeight="600"
                        fontFamily="system-ui, sans-serif"
                      >
                        {field.name} — {Math.round(field.confidence * 100)}%
                      </text>
                    </>
                  )}
                </g>
              );
            })}

            {/* Active field bounding box (Electric Blue) */}
            {activeBBox && (
              <g>
                <rect
                  x={activeBBox.x * scale}
                  y={activeBBox.y * scale}
                  width={activeBBox.width * scale}
                  height={activeBBox.height * scale}
                  fill="rgba(0, 181, 226, 0.15)"
                  stroke="var(--brand-accent)"
                  strokeWidth={2.5}
                  rx={4}
                  className="animate-pulse"
                />
              </g>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
};

