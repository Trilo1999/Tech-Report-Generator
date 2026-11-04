import React, { useEffect, useRef, useState } from "react";
import { ResearchWorkflowState, ReviewSubmission } from "../types/research";
import { getDownloadUrl, getResearchStatus, submitReview } from "../services/api";
import { WorkflowStepper } from "./WorkflowStepper";
import { MetricsGrid } from "./MetricsGrid";
import { CitationLegend } from "./CitationLegend";
import { UnsupportedClaims } from "./UnsupportedClaims";
import { ReportViewer } from "./ReportViewer";
import { ReviewStation } from "./ReviewStation";
import { useAuth } from "../context/AuthContext";

interface ResearchDetailsPageProps {
  threadId: string;
  onBack: () => void;
  onShowToast: (msg: string) => void;
  onOpenAuthModal: (mode: "login" | "register") => void;
}

export const ResearchDetailsPage: React.FC<ResearchDetailsPageProps> = ({
  threadId,
  onBack,
  onShowToast,
  onOpenAuthModal,
}) => {
  const { user } = useAuth();
  const [workflowState, setWorkflowState] = useState<ResearchWorkflowState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const pollIntervalRef = useRef<number | null>(null);
  const timerIntervalRef = useRef<number | null>(null);

  // Initial load of research status
  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setErrorMessage(null);

    getResearchStatus(threadId)
      .then((state) => {
        if (isMounted) {
          setWorkflowState(state);
          setIsLoading(false);
        }
      })
      .catch((err: any) => {
        if (isMounted) {
          setErrorMessage(err.message || `Failed to load research '${threadId}'`);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [threadId]);

  // Status Polling Effect for Background Tasks
  useEffect(() => {
    const isRunning =
      workflowState?.is_running ||
      workflowState?.status === "running" ||
      workflowState?.status === "processing" ||
      workflowState?.status === "review_resuming";

    if (!isRunning) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
      return;
    }

    // Timer for elapsed seconds
    if (!timerIntervalRef.current) {
      timerIntervalRef.current = window.setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }

    // Poller every 1.5s
    let consecutiveErrors = 0;
    if (!pollIntervalRef.current) {
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const updated = await getResearchStatus(threadId);
          consecutiveErrors = 0;
          setWorkflowState(updated);

          if (
            !updated.is_running &&
            updated.status !== "running" &&
            updated.status !== "processing" &&
            updated.status !== "review_resuming"
          ) {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
            pollIntervalRef.current = null;
            timerIntervalRef.current = null;
            setIsSubmittingReview(false);

            if (updated.status === "failed") {
              onShowToast(`Workflow task failed: ${updated.error || "Unknown error"}`);
            } else if (updated.is_pending_review) {
              onShowToast("Draft report ready! Paused at Human Review checkpoint.");
            } else if (updated.status === "completed") {
              onShowToast("Publication PDF report generated successfully!");
            }
          }
        } catch (err: any) {
          consecutiveErrors += 1;
          console.warn(`Polling status failed (${consecutiveErrors}/4):`, err);
          if (consecutiveErrors >= 4) {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
            pollIntervalRef.current = null;
            timerIntervalRef.current = null;
            onShowToast("Server temporarily unavailable. Live polling paused.");
          }
        }
      }, 1500);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    };
  }, [workflowState?.is_running, workflowState?.status, threadId]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    try {
      const updated = await getResearchStatus(threadId);
      setWorkflowState(updated);
      onShowToast("Research status refreshed.");
    } catch (err: any) {
      onShowToast(`Refresh failed: ${err.message || err}`);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleSubmitReview = async (review: ReviewSubmission) => {
    if (!threadId || isSubmittingReview) return;

    if (!user) {
      onOpenAuthModal("login");
      return;
    }

    setIsSubmittingReview(true);
    try {
      const updated = await submitReview(threadId, review);
      setWorkflowState(updated);
      onShowToast(
        review.decision === "approved"
          ? "Approval dispatched! Generating publication PDF in background..."
          : review.decision === "revise"
          ? "Surgical revision requested in background..."
          : "Proposal rejection dispatched."
      );
    } catch (err: any) {
      const msg = err.message || String(err);
      if (msg.includes("401")) {
        onShowToast("Session expired. Please log in.");
        onOpenAuthModal("login");
      } else {
        alert(`Review submission failed: ${msg}`);
      }
      setIsSubmittingReview(false);
    }
  };

  const handleCopyReport = () => {
    if (!workflowState?.draft_report) return;
    const { title, sections } = workflowState.draft_report;
    const text =
      `${title}\n\n` +
      Object.entries(sections)
        .map(([k, v]) => `## ${k}\n${v}`)
        .join("\n\n");
    navigator.clipboard.writeText(text).then(() => {
      onShowToast("Full report copied to clipboard!");
    });
  };

  const handleCopyThreadId = () => {
    navigator.clipboard.writeText(threadId).then(() => {
      onShowToast(`Thread ID '${threadId}' copied!`);
    });
  };

  const isTaskRunning =
    workflowState?.is_running ||
    workflowState?.status === "running" ||
    workflowState?.status === "processing" ||
    workflowState?.status === "review_resuming";

  const getStatusBadge = () => {
    if (isTaskRunning) {
      return (
        <span className="task-badge task-badge-running">
          <span className="task-pulse-dot"></span>
          Running...
        </span>
      );
    }
    if (workflowState?.is_pending_review || workflowState?.status === "review_pending") {
      return (
        <span className="task-badge task-badge-review">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          Review Pending
        </span>
      );
    }
    if (workflowState?.status === "completed") {
      return (
        <span className="task-badge task-badge-completed">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          Completed
        </span>
      );
    }
    if (workflowState?.status === "failed") {
      return (
        <span className="task-badge task-badge-failed">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          Failed
        </span>
      );
    }
    return (
      <span className="task-badge task-badge-draft">
        Draft Ready
      </span>
    );
  };

  // Loading State
  if (isLoading) {
    return (
      <div className="details-container">
        <div className="details-nav-bar">
          <button type="button" className="btn-back-hub" onClick={onBack}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            Back to Research Hub
          </button>
        </div>
        <div className="details-loading-card">
          <div className="task-spinner-ring large-spinner"></div>
          <h3 className="details-loading-title">Loading Research Session...</h3>
          <p className="details-loading-desc">Retrieving state and evidence for <code>{threadId}</code></p>
        </div>
      </div>
    );
  }

  // Error State
  if (errorMessage || !workflowState) {
    return (
      <div className="details-container">
        <div className="details-nav-bar">
          <button type="button" className="btn-back-hub" onClick={onBack}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            Back to Research Hub
          </button>
        </div>
        <div className="details-error-card">
          <div className="details-error-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#F43F5E" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <h3>Unable to Load Research Details</h3>
          <p>{errorMessage || "The requested research task could not be found."}</p>
          <div className="details-error-actions">
            <button type="button" className="btn-primary-action" onClick={handleManualRefresh}>
              Try Again
            </button>
            <button type="button" className="btn-secondary-action" onClick={onBack}>
              Return to Research Hub
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="details-container">
      {/* Top Navigation & Breadcrumbs */}
      <div className="details-nav-bar">
        <button type="button" className="btn-back-hub" onClick={onBack} title="Return to all researches">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          <span>Back to Research Hub</span>
        </button>

        <div className="details-breadcrumbs">
          <span className="crumb-link" onClick={onBack}>Research Hub</span>
          <span className="crumb-sep">/</span>
          <span className="crumb-current">{workflowState.topic || threadId}</span>
        </div>
      </div>

      {/* Main Details Header Banner */}
      <div className="details-header-card">
        <div className="details-header-top">
          <div className="details-title-group">
            <div className="details-topic-row">
              <h1 className="details-title">{workflowState.topic || "Autonomous Research Evaluation"}</h1>
              {getStatusBadge()}
            </div>
            <div className="details-meta-row">
              <button
                type="button"
                className="details-thread-pill"
                onClick={handleCopyThreadId}
                title="Click to copy Thread ID"
              >
                <span>ID: {threadId}</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>

              {workflowState.evidence && (
                <span className="details-meta-item">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                  </svg>
                  {workflowState.evidence.length} Evidence Sources
                </span>
              )}

              {workflowState.status && (
                <span className="details-meta-item">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                  </svg>
                  Status: <code>{workflowState.status}</code>
                </span>
              )}
            </div>
          </div>

          <div className="details-header-actions">
            <button
              type="button"
              className="btn-details-action"
              onClick={handleManualRefresh}
              disabled={isRefreshing}
              title="Refresh status from server"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className={isRefreshing ? "spin-icon" : ""}
              >
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
              </svg>
              Refresh
            </button>

            {workflowState.status === "completed" && (
              <>
                <a
                  href={getDownloadUrl(threadId, "pdf")}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-details-action btn-details-download"
                  title="Download Publication PDF"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  Download PDF
                </a>

                <a
                  href={getDownloadUrl(threadId, "docx")}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-details-action btn-details-docx"
                  title="Download Word Document (.docx)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                  </svg>
                  Download Word (.docx)
                </a>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Live Asynchronous Background Task Progress Banner */}
      {isTaskRunning && (
        <div className="bg-task-banner" style={{ marginTop: "20px" }}>
          <div className="bg-task-pulse-icon">
            <div className="task-spinner-ring"></div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
          </div>
          <div className="bg-task-content">
            <div className="bg-task-header">
              <span className="bg-task-title">Autonomous Research Executing in Background</span>
              <span className="bg-task-timer">Elapsed: {elapsedSeconds}s (polling every 1.5s)</span>
            </div>
            <p className="bg-task-desc">
              Task ID: <code>{threadId}</code> &bull;{" "}
              {workflowState.message ||
                "Agent is synthesizing evidence, executing latency benchmarks, and drafting report non-blockingly."}
            </p>
          </div>
          <button
            type="button"
            className="btn-refresh-task"
            onClick={handleManualRefresh}
            title="Force immediate status poll"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
            </svg>
            Check Status
          </button>
        </div>
      )}

      {/* Workflow Stepper */}
      <WorkflowStepper state={workflowState} isLoading={isTaskRunning} />

      {/* Numerical Metrics and Benchmarks Grid */}
      <MetricsGrid state={workflowState} />

      {/* Citation Legend */}
      <CitationLegend evidenceList={workflowState.evidence} onShowToast={onShowToast} />

      {/* Unsupported Claims & Hallucination Guardrails */}
      {workflowState.unsupported_claims && (
        <UnsupportedClaims claims={workflowState.unsupported_claims} />
      )}

      {/* Full Technical Draft Report Viewer */}
      {workflowState.draft_report && (
        <ReportViewer
          draft={workflowState.draft_report}
          threadId={threadId}
          evidenceList={workflowState.evidence}
          isCompleted={workflowState.status === "completed"}
          onCopy={handleCopyReport}
          onShowToast={onShowToast}
        />
      )}

      {/* Human-in-the-Loop Review Station */}
      {workflowState.draft_report && (
        <ReviewStation
          sections={workflowState.draft_report.sections}
          threadId={threadId}
          isPendingReview={workflowState.is_pending_review}
          isCompleted={workflowState.status === "completed"}
          onSubmitReview={handleSubmitReview}
          isSubmitting={isSubmittingReview || isTaskRunning}
        />
      )}
    </div>
  );
};

export default ResearchDetailsPage;
