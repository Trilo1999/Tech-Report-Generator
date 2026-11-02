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
  topic?: string;
  status: "idle" | "planning" | "gathering" | "calculating" | "evaluating" | "drafted" | "review_pending" | "revised" | "approved" | "completed" | "rejected";
  subquestions?: string[];
  evidence_count?: number;
  evidence?: EvidenceItem[];
  calculations?: Record<string, any>;
  draft_report?: DraftReport;
  unsupported_claims?: string[];
  is_pending_review?: boolean;
  final_report_path?: string;
}

export type ReviewDecision = "approved" | "revise" | "rejected";

export interface ReviewSubmission {
  decision: ReviewDecision;
  feedback_notes?: string;
  target_sections?: string[];
}
