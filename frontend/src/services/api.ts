import { ResearchWorkflowState, ReviewSubmission } from "../types/research";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function startResearch(topic: string, threadId?: string): Promise<ResearchWorkflowState> {
  const res = await fetch(`${BASE_URL}/api/research/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, thread_id: threadId || undefined }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to initiate research (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getResearchStatus(threadId: string): Promise<ResearchWorkflowState> {
  const res = await fetch(`${BASE_URL}/api/research/status/${threadId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch status for thread ${threadId} (HTTP ${res.status})`);
  }
  return res.json();
}

export async function submitReview(threadId: string, review: ReviewSubmission): Promise<ResearchWorkflowState> {
  const res = await fetch(`${BASE_URL}/api/research/review/${threadId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(review),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to submit review (HTTP ${res.status})`);
  }
  return res.json();
}

export function getDownloadUrl(threadId: string): string {
  return `${BASE_URL}/api/research/download/${threadId}`;
}
