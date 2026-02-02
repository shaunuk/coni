"use client";

interface StreamingTextProps {
  text: string;
  isStreaming: boolean;
  maxLength?: number;
}

export default function StreamingText({
  text,
  isStreaming,
  maxLength = 500,
}: StreamingTextProps) {
  // Truncate text if needed
  const displayText = text.length > maxLength
    ? text.slice(0, text.lastIndexOf(" ", maxLength) || maxLength) + "..."
    : text;

  return (
    <span className="streaming-text whitespace-pre-wrap">
      {displayText}
      {isStreaming && (
        <span className="typing-cursor" aria-hidden="true" />
      )}
    </span>
  );
}
