"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { submitQuestion } from "@/lib/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    try {
      const question = await submitQuestion(query);
      router.push(`/q/${question.slug}`);
    } catch (err) {
      console.error("Failed to submit question:", err);
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white dark:bg-slate-950">
      {/* Nav */}
      <nav className="absolute top-0 right-0 p-6">
        <Link
          href="/about"
          className="text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
        >
          About
        </Link>
      </nav>

      {/* Main content */}
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-xl">
          {/* Logo */}
          <h1 className="text-4xl font-light text-center text-slate-900 dark:text-white mb-2 tracking-tight">
            Consensus
          </h1>
          <p className="text-center text-slate-400 dark:text-slate-500 text-sm mb-10">
            Multi-source knowledge synthesis
          </p>

          {/* Search */}
          <form onSubmit={handleSubmit}>
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question..."
                disabled={loading}
                className="w-full px-5 py-4 bg-slate-50 dark:bg-slate-900
                         border border-slate-200 dark:border-slate-800 rounded-xl
                         text-slate-900 dark:text-white placeholder-slate-400
                         focus:outline-none focus:ring-2 focus:ring-slate-900 dark:focus:ring-white
                         focus:border-transparent transition-all"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="absolute right-2 top-1/2 -translate-y-1/2
                         px-4 py-2 bg-slate-900 dark:bg-white
                         text-white dark:text-slate-900 text-sm font-medium
                         rounded-lg hover:bg-slate-700 dark:hover:bg-slate-100
                         disabled:opacity-40 disabled:cursor-not-allowed
                         transition-colors"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                  </span>
                ) : (
                  "Search"
                )}
              </button>
            </div>
          </form>

          {/* Features */}
          <div className="mt-12 flex justify-center gap-8 text-xs text-slate-400 dark:text-slate-500">
            <span>8 AI models</span>
            <span className="text-slate-300 dark:text-slate-700">·</span>
            <span>Web search</span>
            <span className="text-slate-300 dark:text-slate-700">·</span>
            <span>Debate synthesis</span>
          </div>
        </div>
      </div>
    </main>
  );
}
