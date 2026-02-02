"use client";

interface Comparison {
  source?: string;
  other_source?: string;  // Backend uses this field name
  agrees?: boolean;
  agree?: boolean;  // Backend uses this field name
  comment: string;
}

interface ComparisonResult {
  reviewer: string;
  comparisons: Comparison[];
  overall_assessment: string;
}

interface ComparisonResultsProps {
  results: ComparisonResult[];
}

function formatSourceName(name: string): string {
  // Convert "openrouter:anthropic/claude-3-5-haiku" to "Claude Haiku"
  if (name.includes("claude")) return "Claude Haiku";
  if (name.includes("gpt-4o-mini")) return "GPT-4o Mini";
  if (name.includes("gemini")) return "Gemini Flash";
  return name.replace("openrouter:", "").split("/").pop() || name;
}

export default function ComparisonResults({ results }: ComparisonResultsProps) {
  if (results.length === 0) return null;

  return (
    <div className="bg-slate-800/50 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">Cross-Comparison</h3>
        <span className="text-sm text-slate-400">
          {results.length} AI{results.length !== 1 ? "s" : ""} reviewed others
        </span>
      </div>

      <div className="space-y-3">
        {results.map((result, idx) => (
          <div key={idx} className="bg-slate-700/50 rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-purple-400">
                {formatSourceName(result.reviewer)}
              </span>
              <span className="text-xs text-slate-500">reviewed:</span>
            </div>

            <div className="grid gap-2 pl-2">
              {result.comparisons.map((comp, compIdx) => {
                const sourceName = comp.source || comp.other_source || "Unknown";
                const doesAgree = comp.agrees ?? comp.agree ?? false;
                return (
                  <div
                    key={compIdx}
                    className="flex items-start gap-2 text-sm"
                  >
                    <span
                      className={`mt-0.5 w-4 h-4 flex items-center justify-center rounded-full ${
                        doesAgree
                          ? "bg-green-500/20 text-green-400"
                          : "bg-amber-500/20 text-amber-400"
                      }`}
                    >
                      {doesAgree ? "+" : "?"}
                    </span>
                    <div className="flex-1">
                      <span className="text-slate-300">
                        {formatSourceName(sourceName)}:
                      </span>{" "}
                      <span className="text-slate-400">{comp.comment}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {result.overall_assessment && (
              <p className="text-xs text-slate-500 italic pl-2 border-l-2 border-slate-600 mt-2">
                {result.overall_assessment}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
