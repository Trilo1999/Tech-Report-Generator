export interface EvidenceItem {
  source_id: string;
  source_type: string;
  title: string;
  content: string;
  reliability_score?: number;
  metadata?: Record<string, any>;
}

export interface DraftReport {
  title: string;
  sections: Record<string, string>;
  cited_sources: string[];
  unsupported_claims: string[];
}

export interface ResearchWorkflowState {
  thread_id: string;
  task_id?: string;
  topic?: string;
  status:
    | "idle"
    | "running"
    | "planning"
    | "gathering"
    | "calculating"
    | "evaluating"
    | "drafted"
    | "review_pending"
    | "processing"
    | "review_resuming"
    | "revised"
    | "approved"
    | "completed"
    | "rejected"
    | "failed";
  subquestions?: string[];
  evidence_count?: number;
  evidence?: EvidenceItem[];
  calculations?: Record<string, any>;
  draft_report?: DraftReport;
  unsupported_claims?: string[];
  is_pending_review?: boolean;
  is_running?: boolean;
  final_report_path?: string;
  message?: string;
  status_url?: string;
  error?: string;
}

export type ReviewDecision = "approved" | "revise" | "rejected";

export interface ReviewSubmission {
  decision: ReviewDecision;
  feedback_notes?: string;
  target_sections?: string[];
  sync?: boolean;
}

export interface ResearchTaskSummary {
  task_id: string;
  thread_id: string;
  topic: string;
  user_id?: string;
  user_name?: string;
  status: string;
  is_running: boolean;
  is_pending_review?: boolean;
  evidence_count?: number;
  has_report?: boolean;
  error?: string;
  created_at: number;
  updated_at: number;
}
