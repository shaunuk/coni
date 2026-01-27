"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitQuestion } from "@/lib/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const question = await submitQuestion(query);
      router.push(`/q/${question.slug}`);
    } catch (err) {
      console.error("Failed to submit question:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-white">
      <div className="text-center mb-12">
        <h1 className="text-6xl font-bold text-gray-900 mb-4">Consensus</h1>
        <p className="text-xl text-gray-500">
          Humanity&apos;s Knowledge, Verified
        </p>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-2xl px-4">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
            className="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-full
                       focus:outline-none focus:border-blue-500 text-gray-900
                       placeholder-gray-400 shadow-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2
                       bg-blue-600 text-white rounded-full hover:bg-blue-700
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {loading ? "Asking..." : "Ask"}
          </button>
        </div>
      </form>
    </main>
  );
}
