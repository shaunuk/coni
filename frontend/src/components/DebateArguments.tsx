"use client";

import { useState } from "react";

interface Argument {
  target_stance: string;
  counterargument: string;
  strength: "weak" | "medium" | "strong";
  suggests_merger_with?: string;
}

interface DebateRound {
  round_number: number;
  arguments: Argument[];
}

interface DebateArgumentsProps {
  rounds: DebateRound[];
}

function strengthColor(strength: string): string {
  switch (strength) {
    case "strong":
      return "text-red-400";
    case "medium":
      return "text-amber-400";
    case "weak":
      return "text-green-400";
    default:
      return "text-slate-400";
  }
}

function strengthIcon(strength: string): string {
  switch (strength) {
    case "strong":
      return "!!!";
    case "medium":
      return "!!";
    case "weak":
      return "!";
    default:
      return "?";
  }
}

export default function DebateArguments({ rounds }: DebateArgumentsProps) {
  const [expandedRound, setExpandedRound] = useState<number | null>(
    rounds.length > 0 ? rounds[rounds.length - 1].round_number : null
  );

  if (rounds.length === 0) return null;

  return (
    <div className="bg-slate-800/50 rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-white flex items-center gap-2">
        <span className="text-amber-400">Debate Arguments</span>
        <span className="text-sm text-slate-400 font-normal">
          {rounds.length} round{rounds.length !== 1 ? "s" : ""}
        </span>
      </h3>

      <div className="space-y-2">
        {rounds.map((round) => (
          <div key={round.round_number} className="bg-slate-700/50 rounded-lg overflow-hidden">
            <button
              onClick={() =>
                setExpandedRound(
                  expandedRound === round.round_number ? null : round.round_number
                )
              }
              className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-slate-700/70 transition-colors"
            >
              <span className="text-sm font-medium text-slate-300">
                Round {round.round_number}
              </span>
              <span className="text-xs text-slate-500">
                {round.arguments.length} argument{round.arguments.length !== 1 ? "s" : ""}
                {expandedRound === round.round_number ? " -" : " +"}
              </span>
            </button>

            {expandedRound === round.round_number && (
              <div className="px-3 pb-3 space-y-2">
                {round.arguments.map((arg, idx) => (
                  <div
                    key={idx}
                    className="pl-3 border-l-2 border-slate-600 space-y-1"
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className={`text-xs font-mono ${strengthColor(arg.strength)}`}
                        title={`${arg.strength} counterargument`}
                      >
                        {strengthIcon(arg.strength)}
                      </span>
                      <div className="flex-1">
                        <p className="text-xs text-slate-500 mb-1">
                          Challenging: <span className="text-slate-400">{arg.target_stance?.slice(0, 60)}...</span>
                        </p>
                        <p className="text-sm text-slate-300">
                          {arg.counterargument}
                        </p>
                        {arg.suggests_merger_with && (
                          <p className="text-xs text-purple-400 mt-1">
                            Suggests merging with: {arg.suggests_merger_with.slice(0, 50)}...
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
