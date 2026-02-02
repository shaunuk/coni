// Progress event types from WebSocket
export type ProgressEventType =
  | "pipeline_started"
  | "source_started"
  | "source_completed"
  | "source_failed"
  | "debate_round_started"
  | "debate_round_completed"
  | "synthesis_started"
  | "synthesis_completed"
  | "pipeline_completed"
  | "pipeline_failed"
  | "ping"
  | "pong";

export interface ProgressEvent {
  type: ProgressEventType;
  question_id: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface PipelineStartedData {
  sources: string[];
}

export interface SourceStartedData {
  source_name: string;
}

export interface SourceCompletedData {
  source_name: string;
  confidence: number;
  claims_count: number;
}

export interface SourceFailedData {
  source_name: string;
  error: string;
}

export interface DebateRoundStartedData {
  round_number: number;
}

export interface DebateRoundCompletedData {
  round_number: number;
  convergence_score: number;
}

export interface SynthesisCompletedData {
  confidence: number;
}

export interface PipelineCompletedData {
  status: string;
  confidence: number;
  final_answer: string;
}

export interface PipelineFailedData {
  error: string;
}

// Source status for UI
export type SourceStatus = "waiting" | "querying" | "completed" | "failed";

export interface SourceState {
  name: string;
  status: SourceStatus;
  confidence?: number;
  claimsCount?: number;
  error?: string;
}

// Debate round status for UI
export type DebateRoundStatus = "pending" | "in_progress" | "completed";

export interface DebateRoundState {
  roundNumber: number;
  status: DebateRoundStatus;
  convergenceScore?: number;
}

// Overall pipeline progress state
export interface PipelineProgress {
  questionId: string;
  stage: "idle" | "gathering" | "debating" | "synthesizing" | "completed" | "failed";
  sources: SourceState[];
  debateRounds: DebateRoundState[];
  finalStatus?: string;
  finalConfidence?: number;
  finalAnswer?: string;
  error?: string;
}

// Question cloud types
export interface RecentQuestion {
  id: string;
  text: string;
  slug: string;
  created_at: string;
  status: string | null;
  confidence: number | null;
}

// Floating bubble position
export interface BubblePosition {
  x: number;
  y: number;
  scale: number;
  opacity: number;
  layer: 1 | 2 | 3;
}

// WebSocket connection state
export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

// API response types
export interface Question {
  id: string;
  text: string;
  slug: string;
  created_at: string;
}

export interface Answer {
  id: string;
  question_id: string;
  version: number;
  status: string;
  preliminary_answer: string | null;
  final_answer: string | null;
  confidence: number | null;
  seal_hash: string | null;
  sealed_at: string | null;
  created_at: string;
}

export interface DebateRound {
  id: string;
  answer_version_id: string;
  round_number: number;
  phase: string;
  positions: Record<string, unknown>;
  arguments: Record<string, unknown>[];
  synthesis: Record<string, unknown> | null;
  convergence_score: number;
}

export interface Source {
  id: string;
  answer_version_id: string;
  source_name: string;
  raw_response: string;
  claims: Array<{
    text: string;
    confidence: number;
    evidence: string | null;
  }>;
  confidence: number;
  source_url: string | null;
}
