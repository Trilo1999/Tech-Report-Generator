import { ResearchTaskSummary, ResearchWorkflowState, ReviewSubmission } from "../types/research";
import { DemoUser, TokenResponse, User } from "../types/auth";

const getBaseUrl = (): string => {
  if (typeof window !== "undefined") {
    if ((window as any).__API_BASE_URL__) {
      return (window as any).__API_BASE_URL__;
    }
    // When running Docusaurus dev server locally on port 3000, call backend on 8000 directly
    if (window.location.port === "3000" && window.location.hostname === "localhost") {
      return "http://localhost:8000";
    }
    return "";
  }
  return "http://localhost:8000";
};

const BASE_URL = getBaseUrl();

export const TOKEN_STORAGE_KEY = "antigravity_auth_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// ──────────────────────────────────────────────
// Auth API Endpoints
// ──────────────────────────────────────────────
export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Login failed (HTTP ${res.status})`);
  }
  return res.json();
}

export async function registerApi(
  email: string,
  name: string,
  password: string,
  role: string = "researcher"
): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password, role }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Registration failed (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getMeApi(): Promise<User> {
  const res = await fetch(`${BASE_URL}/api/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to authenticate user (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getDemoUsersApi(): Promise<DemoUser[]> {
  const res = await fetch(`${BASE_URL}/api/auth/demo-users`);
  if (!res.ok) {
    throw new Error(`Failed to load demo accounts (HTTP ${res.status})`);
  }
  return res.json();
}

// ──────────────────────────────────────────────
// Research Workflow Endpoints (Authenticated)
// ──────────────────────────────────────────────
export async function startResearch(topic: string, threadId?: string): Promise<ResearchWorkflowState> {
  const res = await fetch(`${BASE_URL}/api/research/start`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ topic, thread_id: threadId || undefined }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to initiate research (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getResearchStatus(threadId: string): Promise<ResearchWorkflowState> {
  const res = await fetch(`${BASE_URL}/api/research/status/${threadId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch status for thread ${threadId} (HTTP ${res.status})`);
  }
  return res.json();
}

export async function submitReview(threadId: string, review: ReviewSubmission): Promise<ResearchWorkflowState> {
  const res = await fetch(`${BASE_URL}/api/research/review/${threadId}`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(review),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to submit review (HTTP ${res.status})`);
  }
  return res.json();
}

export function getDownloadUrl(threadId: string, format: "pdf" | "docx" = "pdf"): string {
  const token = getStoredToken();
  const params = new URLSearchParams();
  if (format) params.append("format", format);
  if (token) params.append("token", token);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return `${BASE_URL}/api/research/download/${threadId}${qs}`;
}

export async function listUserTasks(): Promise<ResearchTaskSummary[]> {
  const res = await fetch(`${BASE_URL}/api/research/tasks`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch user research tasks (HTTP ${res.status})`);
  }
  return res.json();
}

export async function deleteResearchTaskApi(threadId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/research/tasks/${threadId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete task ${threadId} (HTTP ${res.status})`);
  }
}
