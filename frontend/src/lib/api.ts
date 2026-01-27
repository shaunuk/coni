const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function submitQuestion(text: string) {
  const res = await fetch(`${API_BASE}/api/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to submit question");
  return res.json();
}

export async function getQuestion(slug: string) {
  const res = await fetch(`${API_BASE}/api/questions/${slug}`);
  if (!res.ok) throw new Error("Question not found");
  return res.json();
}

export async function getLatestAnswer(questionId: string) {
  const res = await fetch(`${API_BASE}/api/answers/${questionId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getDebateRounds(versionId: string) {
  const res = await fetch(`${API_BASE}/api/answers/${versionId}/debate`);
  if (!res.ok) return [];
  return res.json();
}

export async function getSources(versionId: string) {
  const res = await fetch(`${API_BASE}/api/answers/${versionId}/sources`);
  if (!res.ok) return [];
  return res.json();
}
