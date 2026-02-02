"use client";

import { useMemo } from "react";

interface Position {
  stance: string;
  supporting_sources: string[];
  claims?: string[];
}

interface ConvergenceVisualizationProps {
  positions: Position[];
  convergenceScore: number;
  activeSources: Set<string>;
  streamingSources: Set<string>;
}

// Source colors - consistent for each source type
const SOURCE_COLORS: Record<string, string> = {
  "Claude Haiku": "#F97316", // orange
  "Claude Sonnet": "#EA580C", // darker orange
  "GPT-4o Mini": "#22C55E", // green
  "GPT-4o": "#16A34A", // darker green
  "Gemini Flash": "#3B82F6", // blue
  "Gemini Pro": "#2563EB", // darker blue
  "Llama 3.1": "#A855F7", // purple
  "Mistral": "#6B7280", // gray
  "Reddit": "#FF4500", // reddit orange
  "StackOverflow": "#F48024", // SO orange
  "Wikipedia": "#636466", // wiki gray
};

function getSourceColor(sourceName: string): string {
  // Check for exact match first
  if (SOURCE_COLORS[sourceName]) {
    return SOURCE_COLORS[sourceName];
  }
  // Check for partial match
  const lowerName = sourceName.toLowerCase();
  if (lowerName.includes("claude") && lowerName.includes("haiku")) return SOURCE_COLORS["Claude Haiku"];
  if (lowerName.includes("claude") && lowerName.includes("sonnet")) return SOURCE_COLORS["Claude Sonnet"];
  if (lowerName.includes("gpt-4o-mini")) return SOURCE_COLORS["GPT-4o Mini"];
  if (lowerName.includes("gpt-4o")) return SOURCE_COLORS["GPT-4o"];
  if (lowerName.includes("gemini") && lowerName.includes("flash")) return SOURCE_COLORS["Gemini Flash"];
  if (lowerName.includes("gemini") && lowerName.includes("pro")) return SOURCE_COLORS["Gemini Pro"];
  if (lowerName.includes("llama")) return SOURCE_COLORS["Llama 3.1"];
  if (lowerName.includes("mistral")) return SOURCE_COLORS["Mistral"];
  if (lowerName.includes("reddit")) return SOURCE_COLORS["Reddit"];
  if (lowerName.includes("stack")) return SOURCE_COLORS["StackOverflow"];
  if (lowerName.includes("wiki")) return SOURCE_COLORS["Wikipedia"];
  // Fallback to hash-based color
  let hash = 0;
  for (let i = 0; i < sourceName.length; i++) {
    hash = sourceName.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = hash % 360;
  return `hsl(${hue}, 70%, 50%)`;
}

function getShortName(sourceName: string): string {
  const lowerName = sourceName.toLowerCase();
  if (lowerName.includes("claude") && lowerName.includes("haiku")) return "CH";
  if (lowerName.includes("claude") && lowerName.includes("sonnet")) return "CS";
  if (lowerName.includes("gpt-4o-mini")) return "G4m";
  if (lowerName.includes("gpt-4o")) return "G4";
  if (lowerName.includes("gemini") && lowerName.includes("flash")) return "GF";
  if (lowerName.includes("gemini") && lowerName.includes("pro")) return "GP";
  if (lowerName.includes("llama")) return "LL";
  if (lowerName.includes("mistral")) return "MI";
  if (lowerName.includes("reddit")) return "R";
  if (lowerName.includes("stack")) return "SO";
  if (lowerName.includes("wiki")) return "W";
  return sourceName.slice(0, 2).toUpperCase();
}

export default function ConvergenceVisualization({
  positions,
  convergenceScore,
  activeSources,
  streamingSources,
}: ConvergenceVisualizationProps) {
  // Calculate dot positions based on positions and convergence
  const dotPositions = useMemo(() => {
    if (!positions || positions.length === 0) {
      // Default scattered positions when no data
      return Array.from(activeSources).map((source, i) => ({
        source,
        x: 20 + (i % 4) * 20,
        y: 20 + Math.floor(i / 4) * 25,
        position: null,
      }));
    }

    const dots: Array<{ source: string; x: number; y: number; position: string | null }> = [];
    const totalPositions = positions.length;

    positions.forEach((pos, posIndex) => {
      const sources = pos.supporting_sources || [];
      const clusterCenterX = totalPositions === 1
        ? 50
        : 20 + (posIndex * 60) / Math.max(totalPositions - 1, 1);

      // As convergence increases, dots cluster tighter
      const spreadFactor = Math.max(0.2, 1 - convergenceScore);

      sources.forEach((source, sourceIndex) => {
        // Spread sources within their cluster
        const angle = (sourceIndex / Math.max(sources.length, 1)) * Math.PI * 2;
        const radius = 8 * spreadFactor * Math.min(sources.length, 4);

        dots.push({
          source,
          x: clusterCenterX + Math.cos(angle) * radius,
          y: 50 + Math.sin(angle) * radius * 0.6,
          position: pos.stance,
        });
      });
    });

    return dots;
  }, [positions, activeSources, convergenceScore]);

  // All unique sources from all positions
  const allSources = useMemo(() => {
    const sources = new Set<string>();
    positions?.forEach(p => p.supporting_sources?.forEach(s => sources.add(s)));
    activeSources.forEach(s => sources.add(s));
    return Array.from(sources);
  }, [positions, activeSources]);

  return (
    <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-lg p-4">
      {/* Convergence score header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
          Convergence
        </span>
        <span className={`text-sm font-semibold ${
          convergenceScore >= 0.8 ? "text-emerald-600" :
          convergenceScore >= 0.5 ? "text-amber-600" :
          "text-slate-600"
        }`}>
          {Math.round(convergenceScore * 100)}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full mb-4 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            convergenceScore >= 0.8 ? "bg-emerald-500" :
            convergenceScore >= 0.5 ? "bg-amber-500" :
            "bg-slate-400"
          }`}
          style={{ width: `${convergenceScore * 100}%` }}
        />
      </div>

      {/* Visualization area */}
      <div className="relative h-32 w-full">
        <svg viewBox="0 0 100 100" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
          {/* Connection lines between sources in same position */}
          {positions?.map((pos, posIndex) => {
            const sources = pos.supporting_sources || [];
            if (sources.length < 2) return null;

            const dots = dotPositions.filter(d => sources.includes(d.source));
            if (dots.length < 2) return null;

            // Draw lines between all dots in this position
            return dots.map((dot, i) =>
              dots.slice(i + 1).map((otherDot, j) => (
                <line
                  key={`line-${posIndex}-${i}-${j}`}
                  x1={dot.x}
                  y1={dot.y}
                  x2={otherDot.x}
                  y2={otherDot.y}
                  stroke="rgba(148, 163, 184, 0.3)"
                  strokeWidth="0.5"
                  className="transition-all duration-500"
                />
              ))
            );
          })}

          {/* Source dots */}
          {dotPositions.map((dot) => {
            const color = getSourceColor(dot.source);
            const isStreaming = streamingSources.has(dot.source);
            const isActive = activeSources.has(dot.source);

            return (
              <g key={dot.source}>
                {/* Pulse effect for streaming */}
                {isStreaming && (
                  <circle
                    cx={dot.x}
                    cy={dot.y}
                    r="6"
                    fill={color}
                    opacity="0.3"
                    className="source-dot-active"
                  />
                )}
                {/* Main dot */}
                <circle
                  cx={dot.x}
                  cy={dot.y}
                  r="4"
                  fill={color}
                  className={`source-dot ${isActive ? "opacity-100" : "opacity-40"}`}
                />
                {/* Label */}
                <text
                  x={dot.x}
                  y={dot.y + 10}
                  fontSize="4"
                  fill="currentColor"
                  textAnchor="middle"
                  className="text-slate-500 dark:text-slate-400"
                >
                  {getShortName(dot.source)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Position labels */}
      {positions && positions.length > 0 && (
        <div className="mt-3 space-y-2">
          {positions.map((pos, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="flex -space-x-1">
                {(pos.supporting_sources || []).slice(0, 5).map((source) => (
                  <div
                    key={source}
                    className="w-4 h-4 rounded-full border border-white dark:border-slate-800"
                    style={{ backgroundColor: getSourceColor(source) }}
                    title={source}
                  />
                ))}
                {(pos.supporting_sources?.length || 0) > 5 && (
                  <div className="w-4 h-4 rounded-full bg-slate-300 dark:bg-slate-600 flex items-center justify-center text-[8px] font-medium">
                    +{pos.supporting_sources!.length - 5}
                  </div>
                )}
              </div>
              <span className="text-xs text-slate-600 dark:text-slate-300 line-clamp-1">
                {pos.stance}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
        <div className="flex flex-wrap gap-2">
          {allSources.slice(0, 8).map((source) => (
            <div key={source} className="flex items-center gap-1">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: getSourceColor(source) }}
              />
              <span className="text-[10px] text-slate-500 dark:text-slate-400">
                {getShortName(source)}
              </span>
            </div>
          ))}
          {allSources.length > 8 && (
            <span className="text-[10px] text-slate-400">
              +{allSources.length - 8} more
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
