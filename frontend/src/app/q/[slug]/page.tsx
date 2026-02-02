"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getQuestion,
  getLatestAnswer,
  getDebateRounds,
  getSources,
  submitQuestion,
} from "@/lib/api";
import StreamingText from "@/components/StreamingText";
import ConvergenceVisualization from "@/components/ConvergenceVisualization";
import ValidationResults from "@/components/ValidationResults";
import ComparisonResults from "@/components/ComparisonResults";
import DebateArguments from "@/components/DebateArguments";

interface Message {
  id: string;
  type: "system" | "source" | "streaming" | "debate" | "synthesis" | "final" | "validation";
  source?: string;
  content: string;
  confidence?: number;
  timestamp: Date;
  isStreaming?: boolean;
}

interface Position {
  stance: string;
  supporting_sources: string[];
  claims?: string[];
}

interface ValidationResult {
  source_name: string;
  agrees: boolean;
  objection: string | null;
}

interface ComparisonResult {
  reviewer: string;
  comparisons: Array<{
    source: string;
    agrees: boolean;
    comment: string;
  }>;
  overall_assessment: string;
}

interface WebSocketEvent {
  type: string;
  question_id: string;
  timestamp: string;
  data: Record<string, any>;
}

/**
 * Truncate text at word boundaries to avoid cutting mid-word.
 */
function truncateAtWord(text: string, maxLength: number = 500): string {
  if (text.length <= maxLength) return text;
  const lastSpace = text.lastIndexOf(" ", maxLength);
  if (lastSpace === -1) {
    return text.slice(0, maxLength) + "...";
  }
  return text.slice(0, lastSpace) + "...";
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export default function AnswerPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [question, setQuestion] = useState<any>(null);
  const [answer, setAnswer] = useState<any>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [seenSourceIds, setSeenSourceIds] = useState<Set<string>>(new Set());
  const [seenRoundIds, setSeenRoundIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const hasLoadedRef = useRef(false);

  // Streaming and convergence state
  const [streamingContent, setStreamingContent] = useState<Map<string, string>>(new Map());
  const [activeSources, setActiveSources] = useState<Set<string>>(new Set());
  const [streamingSources, setStreamingSources] = useState<Set<string>>(new Set());
  const [positions, setPositions] = useState<Position[]>([]);
  const [convergenceScore, setConvergenceScore] = useState(0);
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([]);
  const [agreementPercentage, setAgreementPercentage] = useState(0);
  const [showValidation, setShowValidation] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [comparisonResults, setComparisonResults] = useState<ComparisonResult[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  const [debateRounds, setDebateRounds] = useState<Array<{
    round_number: number;
    arguments: Array<{
      target_stance: string;
      counterargument: string;
      strength: string;
      suggests_merger_with?: string;
    }>;
  }>>([]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Add a message
  const addMessage = useCallback((msg: Omit<Message, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      { ...msg, id: crypto.randomUUID(), timestamp: new Date() },
    ]);
  }, []);

  // Update or add streaming message
  const updateStreamingMessage = useCallback((source: string, content: string, isComplete: boolean) => {
    setStreamingContent((prev) => {
      const next = new Map(prev);
      if (isComplete) {
        next.delete(source);
      } else {
        next.set(source, content);
      }
      return next;
    });

    if (isComplete) {
      setStreamingSources((prev) => {
        const next = new Set(prev);
        next.delete(source);
        return next;
      });
    } else {
      setStreamingSources((prev) => {
        const next = new Set(prev);
        next.add(source);
        return next;
      });
    }
  }, []);

  // Handle WebSocket events
  const handleWebSocketEvent = useCallback((event: WebSocketEvent) => {
    const { type, data } = event;

    switch (type) {
      case "pipeline_started":
        addMessage({
          type: "system",
          content: `Querying ${data.sources?.length || 11} AI models and web sources...`,
        });
        setActiveSources(new Set(data.sources || []));
        break;

      case "source_started":
        setActiveSources((prev) => {
          const next = new Set(prev);
          next.add(data.source_name);
          return next;
        });
        break;

      case "source_streaming":
        updateStreamingMessage(
          data.source_name,
          data.partial_content,
          data.is_complete
        );
        break;

      case "source_completed":
        setActiveSources((prev) => {
          const next = new Set(prev);
          // Keep it active but stop streaming
          return next;
        });
        setStreamingSources((prev) => {
          const next = new Set(prev);
          next.delete(data.source_name);
          return next;
        });
        // Clear streaming content for this source
        setStreamingContent((prev) => {
          const next = new Map(prev);
          next.delete(data.source_name);
          return next;
        });
        break;

      case "source_failed":
        setActiveSources((prev) => {
          const next = new Set(prev);
          next.delete(data.source_name);
          return next;
        });
        break;

      case "debate_round_started":
        addMessage({
          type: "debate",
          content: `Debate Round ${data.round_number}: Sources exchanging counterarguments...`,
        });
        break;

      case "debate_arguments":
        setDebateRounds((prev) => [
          ...prev.filter((r) => r.round_number !== data.round_number),
          {
            round_number: data.round_number,
            arguments: data.arguments || [],
          },
        ]);
        break;

      case "debate_round_completed":
        setConvergenceScore(data.convergence_score);
        break;

      case "position_update":
        setPositions(data.positions || []);
        setConvergenceScore(data.convergence_score);
        break;

      case "comparison_started":
        addMessage({
          type: "system",
          content: "AIs comparing their answers with each other...",
        });
        setShowComparison(true);
        setComparisonResults([]);
        break;

      case "comparison_complete":
        setComparisonResults((prev) => [
          ...prev,
          {
            reviewer: data.reviewer,
            comparisons: data.comparisons || [],
            overall_assessment: data.overall_assessment || "",
          },
        ]);
        break;

      case "comparison_finished":
        // All comparisons done
        break;

      case "synthesis_started":
        addMessage({
          type: "synthesis",
          content: "Synthesizing positions into final consensus answer...",
        });
        break;

      case "synthesis_completed":
        // Will be handled by pipeline_completed
        break;

      case "validation_started":
        addMessage({
          type: "system",
          content: "Cross-validating consensus with each AI source...",
        });
        setShowValidation(true);
        break;

      case "source_validated":
        setValidationResults((prev) => [
          ...prev,
          {
            source_name: data.source_name,
            agrees: data.agrees,
            objection: data.objection,
          },
        ]);
        break;

      case "validation_completed":
        setAgreementPercentage(data.agreement_percentage);
        break;

      case "pipeline_completed":
        addMessage({
          type: "final",
          content: data.final_answer,
          confidence: data.confidence,
        });
        // Refresh answer data
        if (question?.id) {
          getLatestAnswer(question.id).then((a) => {
            if (a) setAnswer(a);
          });
        }
        break;

      case "pipeline_failed":
        addMessage({
          type: "system",
          content: `Error: ${data.error}`,
        });
        break;
    }
  }, [addMessage, updateStreamingMessage, question?.id]);

  // Connect WebSocket
  useEffect(() => {
    if (!question?.id) return;

    const wsUrl = `${WS_BASE}/ws/progress/${question.id}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "ping") {
          ws.send("pong");
          return;
        }
        if (data.type === "pong") return;
        handleWebSocketEvent(data);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      console.log("WebSocket disconnected");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // Keep connection alive with pings
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 25000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [question?.id, handleWebSocketEvent]);

  // Load initial data
  useEffect(() => {
    if (hasLoadedRef.current) return;
    hasLoadedRef.current = true;

    async function load() {
      try {
        const q = await getQuestion(slug);
        setQuestion(q);

        addMessage({
          type: "system",
          content: "Starting consensus search across 8 AI models and 3 web sources...",
        });

        const a = await getLatestAnswer(q.id);
        if (a) {
          setAnswer(a);

          // Load existing sources
          const sources = await getSources(a.id);
          const newSeenIds = new Set<string>();
          for (const s of sources) {
            newSeenIds.add(s.id);
            addMessage({
              type: "source",
              source: s.source_name,
              content: truncateAtWord(s.raw_response ?? "") || "No response",
              confidence: s.confidence,
            });
          }
          setSeenSourceIds(newSeenIds);

          // Load existing debate rounds
          const rounds = await getDebateRounds(a.id);
          const newSeenRounds = new Set<string>();
          for (const r of rounds) {
            newSeenRounds.add(r.id);
            if (r.phase === "counterarguments") {
              addMessage({
                type: "debate",
                content: `Round ${r.round_number}: Convergence at ${Math.round(r.convergence_score * 100)}%`,
              });
              if (r.positions) {
                setPositions(r.positions);
              }
              setConvergenceScore(r.convergence_score);
            } else if (r.phase === "synthesis") {
              if (r.synthesis?.reasoning) {
                addMessage({
                  type: "synthesis",
                  content: r.synthesis.reasoning,
                });
              }
              // Load validation results if available
              if (r.validation_results) {
                setValidationResults(r.validation_results.validation_results || []);
                setAgreementPercentage(r.validation_results.agreement_percentage || 0);
                setShowValidation(true);
              }
            }
          }
          setSeenRoundIds(newSeenRounds);

          // Show final answer if complete
          if (a.final_answer && !["preliminary", "debating"].includes(a.status)) {
            addMessage({
              type: "final",
              content: a.final_answer,
              confidence: a.confidence,
            });
          }
        }
      } catch (err) {
        setError("Question not found");
      }
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  // Poll for updates (fallback if WebSocket is not connected)
  useEffect(() => {
    if (!question) return;
    if (wsConnected) return; // Don't poll if WebSocket is connected

    // If answer exists and is complete, no need to poll
    if (answer && !["preliminary", "debating"].includes(answer.status)) return;

    const interval = setInterval(async () => {
      try {
        const a = await getLatestAnswer(question.id);
        if (!a) return;

        // Check for new sources
        const sources = await getSources(a.id);
        for (const s of sources) {
          if (!seenSourceIds.has(s.id)) {
            setSeenSourceIds((prev) => {
              const next = new Set(prev);
              next.add(s.id);
              return next;
            });
            addMessage({
              type: "source",
              source: s.source_name,
              content: truncateAtWord(s.raw_response ?? "") || "No response",
              confidence: s.confidence,
            });
          }
        }

        // Check for new debate rounds
        const rounds = await getDebateRounds(a.id);
        for (const r of rounds) {
          if (!seenRoundIds.has(r.id)) {
            setSeenRoundIds((prev) => {
              const next = new Set(prev);
              next.add(r.id);
              return next;
            });
            if (r.phase === "counterarguments") {
              addMessage({
                type: "debate",
                content: `Round ${r.round_number}: Sources debating... Convergence at ${Math.round(r.convergence_score * 100)}%`,
              });
              if (r.positions) {
                setPositions(r.positions);
              }
              setConvergenceScore(r.convergence_score);
            } else if (r.phase === "synthesis" && r.synthesis) {
              addMessage({
                type: "synthesis",
                content: r.synthesis.reasoning || "Synthesizing positions into final answer...",
              });
            }
          }
        }

        // Check if complete
        if (a.final_answer && !["preliminary", "debating"].includes(a.status)) {
          if (answer?.status !== a.status) {
            addMessage({
              type: "final",
              content: a.final_answer,
              confidence: a.confidence,
            });
          }
        }

        setAnswer(a);
      } catch (err) {
        // Ignore
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [answer, question, seenSourceIds, seenRoundIds, addMessage, wsConnected]);

  const handleSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim() || submitting) return;

      setSubmitting(true);
      try {
        const newQuestion = await submitQuestion(query);
        router.push(`/q/${newQuestion.slug}`);
      } catch (err) {
        console.error("Failed:", err);
      } finally {
        setSubmitting(false);
      }
    },
    [query, submitting, router]
  );

  if (error) {
    return (
      <main className="min-h-screen bg-white dark:bg-slate-950">
        <div className="max-w-3xl mx-auto px-6 py-16 text-center">
          <p className="text-slate-500 mb-4">{error}</p>
          <Link href="/" className="text-slate-900 dark:text-white hover:underline">
            Back
          </Link>
        </div>
      </main>
    );
  }

  if (!question) {
    return (
      <main className="min-h-screen bg-white dark:bg-slate-950 flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-slate-900 dark:border-white border-t-transparent rounded-full animate-spin" />
      </main>
    );
  }

  const isProcessing = answer && ["preliminary", "debating"].includes(answer.status);
  const isComplete = answer && !["preliminary", "debating"].includes(answer.status);

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      {/* Header */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link href="/" className="text-lg font-light text-slate-900 dark:text-white">
            Consensus
          </Link>
          <form onSubmit={handleSearch} className="flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask another question..."
              className="w-full px-3 py-1.5 bg-slate-100 dark:bg-slate-800 border-0 rounded-lg
                       text-sm text-slate-900 dark:text-white placeholder-slate-400
                       focus:outline-none focus:ring-2 focus:ring-slate-900 dark:focus:ring-white"
            />
          </form>
          <Link href="/about" className="text-sm text-slate-400 hover:text-slate-900 dark:hover:text-white">
            About
          </Link>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Messages column */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
            {/* Question */}
            <div className="flex justify-end">
              <div className="bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl rounded-br-md px-4 py-3 max-w-[80%]">
                <p className="text-sm font-medium">{question.text}</p>
              </div>
            </div>

            {/* Streaming sources */}
            {Array.from(streamingContent.entries()).map(([source, content]) => (
              <StreamingSourceBubble
                key={`streaming-${source}`}
                source={source}
                content={content}
                isStreaming={streamingSources.has(source)}
              />
            ))}

            {/* Messages */}
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {/* Processing indicator */}
            {isProcessing && streamingContent.size === 0 && (
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <span>Gathering more responses...</span>
              </div>
            )}

            {/* Cross-comparison results */}
            {showComparison && comparisonResults.length > 0 && (
              <ComparisonResults results={comparisonResults} />
            )}

            {/* Debate arguments */}
            {debateRounds.length > 0 && (
              <DebateArguments rounds={debateRounds} />
            )}

            {/* Validation results */}
            {showValidation && validationResults.length > 0 && (
              <ValidationResults
                results={validationResults}
                agreementPercentage={agreementPercentage}
              />
            )}

            {/* Final summary */}
            {isComplete && answer && (
              <div className="mt-8 p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2 mb-4">
                  <span className={`text-sm font-medium ${
                    answer.status === "consensus_reached" ? "text-emerald-600" : "text-amber-600"
                  }`}>
                    {answer.status === "consensus_reached" ? "Consensus Reached" : "Contested"}
                  </span>
                  {answer.confidence && (
                    <span className="text-sm text-slate-400">
                      {Math.round(answer.confidence * 100)}% confidence
                    </span>
                  )}
                </div>
                <p className="text-slate-800 dark:text-slate-200 leading-relaxed">
                  {answer.final_answer}
                </p>
                {answer.seal_hash && (
                  <p className="mt-4 text-xs text-slate-400 font-mono">
                    Sealed: {answer.seal_hash.slice(0, 20)}...
                  </p>
                )}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Convergence visualization sidebar */}
        {(isProcessing || positions.length > 0) && (
          <div className="hidden lg:block w-80 border-l border-slate-200 dark:border-slate-800 p-4 overflow-y-auto">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">
              Source Convergence
            </h3>
            <ConvergenceVisualization
              positions={positions}
              convergenceScore={convergenceScore}
              activeSources={activeSources}
              streamingSources={streamingSources}
            />
          </div>
        )}
      </div>
    </main>
  );
}

function StreamingSourceBubble({
  source,
  content,
  isStreaming,
}: {
  source: string;
  content: string;
  isStreaming: boolean;
}) {
  const getSourceIcon = (source: string) => {
    const s = source.toLowerCase();
    if (s.includes("claude")) return <span className="text-orange-500">C</span>;
    if (s.includes("gpt")) return <span className="text-green-500">G</span>;
    if (s.includes("gemini")) return <span className="text-blue-500">G</span>;
    if (s.includes("llama")) return <span className="text-purple-500">L</span>;
    if (s.includes("mistral")) return <span className="text-gray-500">M</span>;
    return <span className="text-gray-500">?</span>;
  };

  const getSourceName = (source: string) => {
    const s = source.toLowerCase();
    if (s.includes("claude") && s.includes("haiku")) return "Claude Haiku";
    if (s.includes("claude") && s.includes("sonnet")) return "Claude Sonnet";
    if (s.includes("gpt-4o-mini")) return "GPT-4o Mini";
    if (s.includes("gpt-4o")) return "GPT-4o";
    if (s.includes("gemini") && s.includes("flash")) return "Gemini Flash";
    if (s.includes("gemini") && s.includes("pro")) return "Gemini Pro";
    if (s.includes("llama")) return "Llama 3.1";
    if (s.includes("mistral")) return "Mistral";
    return source;
  };

  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-sm font-bold shrink-0">
        {getSourceIcon(source)}
      </div>
      <div className="rounded-2xl rounded-tl-md px-4 py-3 max-w-[80%] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-slate-900 dark:text-white">
            {getSourceName(source)}
          </span>
          {isStreaming && (
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          )}
        </div>
        <p className="text-sm text-slate-700 dark:text-slate-300">
          <StreamingText
            text={content}
            isStreaming={isStreaming}
            maxLength={500}
          />
        </p>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const getSourceIcon = (source?: string) => {
    if (!source) return <span>?</span>;
    const s = source.toLowerCase();
    if (s.includes("claude")) return <span className="text-orange-500">C</span>;
    if (s.includes("gpt")) return <span className="text-green-500">G</span>;
    if (s.includes("gemini")) return <span className="text-blue-500">G</span>;
    if (s.includes("llama")) return <span className="text-purple-500">L</span>;
    if (s.includes("mistral")) return <span className="text-gray-500">M</span>;
    if (s.includes("reddit")) return <span className="text-orange-600">R</span>;
    if (s.includes("stack")) return <span className="text-orange-500">S</span>;
    if (s.includes("wiki")) return <span className="text-gray-600">W</span>;
    return <span>?</span>;
  };

  const getSourceName = (source?: string) => {
    if (!source) return "Unknown";
    const s = source.toLowerCase();
    if (s.includes("claude") && s.includes("haiku")) return "Claude Haiku";
    if (s.includes("claude") && s.includes("sonnet")) return "Claude Sonnet";
    if (s.includes("gpt-4o-mini")) return "GPT-4o Mini";
    if (s.includes("gpt-4o")) return "GPT-4o";
    if (s.includes("gemini") && s.includes("flash")) return "Gemini Flash";
    if (s.includes("gemini") && s.includes("pro")) return "Gemini Pro";
    if (s.includes("llama")) return "Llama 3.1";
    if (s.includes("mistral")) return "Mistral";
    if (s.includes("reddit")) return "Reddit";
    if (s.includes("stack")) return "StackOverflow";
    if (s.includes("wiki")) return "Wikipedia";
    return source;
  };

  const getTypeStyles = () => {
    switch (message.type) {
      case "system":
        return "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs";
      case "source":
        return "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700";
      case "debate":
        return "bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200";
      case "synthesis":
        return "bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 text-purple-800 dark:text-purple-200";
      case "final":
        return "bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800";
      default:
        return "bg-white dark:bg-slate-900";
    }
  };

  if (message.type === "system") {
    return (
      <div className="flex justify-center">
        <span className={`px-3 py-1 rounded-full ${getTypeStyles()}`}>
          {message.content}
        </span>
      </div>
    );
  }

  if (message.type === "debate") {
    return (
      <div className="flex justify-center">
        <div className={`px-4 py-2 rounded-lg ${getTypeStyles()} text-sm`}>
          <span className="mr-1">&#x2696;</span> {message.content}
        </div>
      </div>
    );
  }

  if (message.type === "synthesis") {
    return (
      <div className="flex justify-center">
        <div className={`px-4 py-2 rounded-lg ${getTypeStyles()} text-sm max-w-[80%]`}>
          <span className="mr-1">&#x1F9E0;</span> {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-sm font-bold shrink-0">
        {getSourceIcon(message.source)}
      </div>
      <div className={`rounded-2xl rounded-tl-md px-4 py-3 max-w-[80%] ${getTypeStyles()}`}>
        {message.source && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-slate-900 dark:text-white">
              {getSourceName(message.source)}
            </span>
            {message.confidence !== undefined && (
              <span className="text-xs text-slate-400">
                {Math.round(message.confidence * 100)}%
              </span>
            )}
          </div>
        )}
        <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
    </div>
  );
}
