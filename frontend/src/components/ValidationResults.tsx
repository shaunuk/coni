"use client";

import { useState } from "react";

interface ValidationResult {
  source_name: string;
  agrees: boolean;
  objection: string | null;
}

interface ValidationResultsProps {
  results: ValidationResult[];
  agreementPercentage: number;
}

function getShortName(sourceName: string): string {
  const lowerName = sourceName.toLowerCase();
  if (lowerName.includes("claude") && lowerName.includes("haiku")) return "Claude Haiku";
  if (lowerName.includes("claude") && lowerName.includes("sonnet")) return "Claude Sonnet";
  if (lowerName.includes("gpt-4o-mini")) return "GPT-4o Mini";
  if (lowerName.includes("gpt-4o")) return "GPT-4o";
  if (lowerName.includes("gemini") && lowerName.includes("flash")) return "Gemini Flash";
  if (lowerName.includes("gemini") && lowerName.includes("pro")) return "Gemini Pro";
  if (lowerName.includes("llama")) return "Llama 3.1";
  if (lowerName.includes("mistral")) return "Mistral";
  if (lowerName.includes("reddit")) return "Reddit";
  if (lowerName.includes("stack")) return "StackOverflow";
  if (lowerName.includes("wiki")) return "Wikipedia";
  // Extract model name from openrouter format
  if (sourceName.includes(":")) {
    return sourceName.split(":")[1].split("/").pop() || sourceName;
  }
  return sourceName;
}

export default function ValidationResults({
  results,
  agreementPercentage,
}: ValidationResultsProps) {
  const [expandedObjections, setExpandedObjections] = useState<Set<string>>(new Set());

  const toggleObjection = (sourceName: string) => {
    setExpandedObjections((prev) => {
      const next = new Set(prev);
      if (next.has(sourceName)) {
        next.delete(sourceName);
      } else {
        next.add(sourceName);
      }
      return next;
    });
  };

  const agreeingCount = results.filter((r) => r.agrees).length;
  const objectingCount = results.filter((r) => !r.agrees).length;

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 mt-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          Cross-Validation
        </h3>
        <div className={`text-sm font-medium px-2 py-1 rounded ${
          agreementPercentage >= 80
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
            : agreementPercentage >= 50
            ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
            : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
        }`}>
          {Math.round(agreementPercentage)}% Agreement
        </div>
      </div>

      {/* Summary */}
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
        {agreeingCount} of {results.length} sources validated the consensus.
        {objectingCount > 0 && ` ${objectingCount} raised objections.`}
      </p>

      {/* Results grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {results.map((result, index) => (
          <div
            key={result.source_name}
            className={`relative p-2 rounded-lg border ${
              result.agrees
                ? "border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20"
                : "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 cursor-pointer"
            }`}
            onClick={() => !result.agrees && result.objection && toggleObjection(result.source_name)}
          >
            {/* Icon */}
            <div
              className="validation-icon absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {result.agrees ? (
                <span className="bg-emerald-500 text-white w-full h-full rounded-full flex items-center justify-center">
                  &#x2713;
                </span>
              ) : (
                <span className="bg-red-500 text-white w-full h-full rounded-full flex items-center justify-center">
                  &#x2717;
                </span>
              )}
            </div>

            {/* Source name */}
            <span className={`text-xs font-medium block truncate ${
              result.agrees
                ? "text-emerald-700 dark:text-emerald-300"
                : "text-red-700 dark:text-red-300"
            }`}>
              {getShortName(result.source_name)}
            </span>

            {/* Expand indicator for objections */}
            {!result.agrees && result.objection && (
              <span className="text-[10px] text-red-500 dark:text-red-400 mt-1 block">
                {expandedObjections.has(result.source_name) ? "Click to hide" : "Click to see objection"}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Expanded objections */}
      {results
        .filter((r) => !r.agrees && r.objection && expandedObjections.has(r.source_name))
        .map((result) => (
          <div
            key={`objection-${result.source_name}`}
            className="expandable-content mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
          >
            <div className="flex items-start gap-2">
              <span className="text-red-500 shrink-0">&#x2717;</span>
              <div>
                <span className="text-xs font-semibold text-red-700 dark:text-red-300 block mb-1">
                  {getShortName(result.source_name)} objects:
                </span>
                <p className="text-xs text-red-600 dark:text-red-400">
                  {result.objection}
                </p>
              </div>
            </div>
          </div>
        ))}
    </div>
  );
}
