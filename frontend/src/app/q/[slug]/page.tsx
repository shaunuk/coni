"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getQuestion, getLatestAnswer, getDebateRounds, getSources } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import DebateTimeline from "@/components/DebateTimeline";
import SourcesPanel from "@/components/SourcesPanel";

export default function AnswerPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [question, setQuestion] = useState<any>(null);
  const [answer, setAnswer] = useState<any>(null);
  const [rounds, setRounds] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const q = await getQuestion(slug);
        setQuestion(q);

        const a = await getLatestAnswer(q.id);
        if (a) {
          setAnswer(a);
          const [r, s] = await Promise.all([
            getDebateRounds(a.id),
            getSources(a.id),
          ]);
          setRounds(r);
          setSources(s);
        }
      } catch (err) {
        setError("Failed to load question");
      }
    }
    load();
  }, [slug]);

  // Poll for updates while debating
  useEffect(() => {
    if (!answer || !["preliminary", "debating"].includes(answer.status)) return;

    const interval = setInterval(async () => {
      if (!question) return;
      const a = await getLatestAnswer(question.id);
      if (a) {
        setAnswer(a);
        const [r, s] = await Promise.all([
          getDebateRounds(a.id),
          getSources(a.id),
        ]);
        setRounds(r);
        setSources(s);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [answer, question]);

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!question) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">{question.text}</h1>

      {answer && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <StatusBadge status={answer.status} />
            {answer.confidence !== null && (
              <div className="flex items-center gap-2">
                <div className="w-32 h-2 bg-gray-200 rounded-full">
                  <div
                    className="h-2 bg-green-500 rounded-full"
                    style={{ width: `${answer.confidence * 100}%` }}
                  />
                </div>
                <span className="text-sm text-gray-500">
                  {Math.round(answer.confidence * 100)}%
                </span>
              </div>
            )}
          </div>

          <div className="bg-gray-50 rounded-lg p-6">
            <p className="text-lg text-gray-800">
              {answer.final_answer || answer.preliminary_answer || "Awaiting response..."}
            </p>
          </div>

          {answer.seal_hash && (
            <div className="text-xs text-gray-400 font-mono break-all">
              Seal: {answer.seal_hash}
            </div>
          )}

          <DebateTimeline rounds={rounds} />
          <SourcesPanel sources={sources} />
        </div>
      )}

      {!answer && (
        <div className="text-gray-500">Processing your question...</div>
      )}
    </main>
  );
}
