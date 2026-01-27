interface DebateRound {
  round_number: number;
  phase: string;
  positions: { stance: string; supporting_sources: string[] }[];
  arguments: { source_name: string; argument: string }[];
  synthesis: { final_answer: string; confidence: number } | null;
  convergence_score: number | null;
}

export default function DebateTimeline({ rounds }: { rounds: DebateRound[] }) {
  if (!rounds.length) return null;

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-3">Debate Timeline</h3>
      <div className="space-y-4">
        {rounds.map((round) => (
          <details key={round.round_number} className="border rounded p-3">
            <summary className="cursor-pointer font-medium">
              Round {round.round_number} — {round.phase}
              {round.convergence_score !== null && (
                <span className="ml-2 text-sm text-gray-500">
                  ({Math.round(round.convergence_score * 100)}% convergence)
                </span>
              )}
            </summary>
            <div className="mt-3 space-y-2">
              {round.positions.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Positions:</h4>
                  {round.positions.map((pos, i) => (
                    <div key={i} className="ml-3 text-sm text-gray-600">
                      <strong>{pos.stance}</strong>
                      <span className="text-xs text-gray-400 ml-1">
                        ({pos.supporting_sources.join(", ")})
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {round.arguments.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Arguments:</h4>
                  {round.arguments.map((arg, i) => (
                    <div key={i} className="ml-3 text-sm text-gray-600">
                      <strong>{arg.source_name}:</strong> {arg.argument}
                    </div>
                  ))}
                </div>
              )}
              {round.synthesis && (
                <div className="bg-green-50 rounded p-2">
                  <h4 className="text-sm font-medium text-green-800">Synthesis:</h4>
                  <p className="text-sm text-green-700">{round.synthesis.final_answer}</p>
                </div>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
