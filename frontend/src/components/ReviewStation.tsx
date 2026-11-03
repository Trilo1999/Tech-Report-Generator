import React, { useState } from "react";
import { ReviewDecision, ReviewSubmission } from "../types/research";
import { getDownloadUrl } from "../services/api";
import { useAuth } from "../context/AuthContext";

interface ReviewStationProps {
  sections: Record<string, string>;
  threadId: string;
  isPendingReview?: boolean;
  isCompleted?: boolean;
  onSubmitReview: (submission: ReviewSubmission) => void;
  isSubmitting: boolean;
}

export const ReviewStation: React.FC<ReviewStationProps> = ({
  sections,
  threadId,
  isPendingReview,
  isCompleted,
  onSubmitReview,
  isSubmitting,
}) => {
  const { user, hasRole } = useAuth();
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [selectedSections, setSelectedSections] = useState<string[]>([]);

  // RBAC Permission Checks
  const canApproveOrReject = hasRole(["admin", "reviewer"]);
  const canRevise = hasRole(["admin", "reviewer", "researcher"]);
  const isViewer = user?.role === "viewer";

  const handleToggleSection = (sec: string) => {
    setSelectedSections((prev) =>
      prev.includes(sec) ? prev.filter((s) => s !== sec) : [...prev, sec]
    );
  };

  const handleAction = (decision: ReviewDecision) => {
    onSubmitReview({
      decision,
      feedback_notes: feedbackNotes,
      target_sections: selectedSections,
    });
  };

  if (!isPendingReview && !isCompleted) return null;

  return (
    <div className="review-station">
      <div className="review-header-flex">
        <h3>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polygon points="12 8 8 12 12 16 12 8"></polygon>
          </svg>
          Human-in-the-Loop Review Station
        </h3>

        {user && (
          <span className={`rbac-pill ${isViewer ? "pill-warning" : "pill-info"}`}>
            RBAC: {user.role.toUpperCase()}
          </span>
        )}
      </div>

      <p>
        {isPendingReview
          ? "The workflow is suspended at the checkpoint boundary. Review the evidence-grounded draft above and choose an action:"
          : "This report has completed the human review boundary and is approved for distribution."}
      </p>

      {/* Viewer read-only notification */}
      {isPendingReview && isViewer && (
        <div className="rbac-notice-banner">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
          </svg>
          <div>
            <strong>Read-Only Observer Access:</strong>
            <span> Your role is 'viewer'. Review verdicts and surgical revisions require 'reviewer' or 'admin' privileges.</span>
          </div>
        </div>
      )}

      {/* Researcher revision-only notification */}
      {isPendingReview && user?.role === "researcher" && (
        <div className="rbac-info-banner">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <div>
            <strong>Researcher Privileges:</strong>
            <span> You may request section revisions. Final publication approvals require 'reviewer' or 'admin' role.</span>
          </div>
        </div>
      )}

      {isPendingReview && (
        <>
          <div style={{ marginBottom: "14px" }}>
            <label style={{ fontSize: "13px", fontWeight: 700, color: "#FFF", display: "block", marginBottom: "6px" }}>
              Revision Instructions & Reviewer Notes:
            </label>
            <textarea
              className="feedback-textarea"
              value={feedbackNotes}
              onChange={(e) => setFeedbackNotes(e.target.value)}
              placeholder="e.g. Include enterprise security considerations and declare an explicit winner for my project..."
              disabled={isSubmitting || isViewer}
            />
          </div>

          <div style={{ marginBottom: "18px" }}>
            <label style={{ fontSize: "13px", fontWeight: 700, color: "#FFF", display: "block", marginBottom: "6px" }}>
              Target Specific Sections for Surgical Revision (Optional):
            </label>
            <div className="section-chips">
              {Object.keys(sections).map((sec) => {
                const isSelected = selectedSections.includes(sec);
                return (
                  <label key={sec} className={`chip-label ${isSelected ? "selected" : ""} ${isViewer ? "disabled" : ""}`}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggleSection(sec)}
                      disabled={isSubmitting || isViewer}
                    />
                    {sec}
                  </label>
                );
              })}
            </div>
          </div>
        </>
      )}

      <div className="review-actions">
        {isPendingReview && (
          <>
            <button
              className={`btn ${canApproveOrReject ? "btn-success" : "btn-disabled"}`}
              onClick={() => handleAction("approved")}
              disabled={isSubmitting || !canApproveOrReject}
              title={!canApproveOrReject ? "Only Reviewer or Admin can approve reports" : ""}
            >
              {isSubmitting ? (
                <>
                  <div className="spinner"></div> Processing...
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  Approve & Publish PDF
                </>
              )}
            </button>

            <button
              className={`btn ${canRevise ? "btn-amber" : "btn-disabled"}`}
              onClick={() => handleAction("revise")}
              disabled={isSubmitting || !canRevise}
              title={!canRevise ? "Viewer role cannot request revisions" : ""}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
              Request Surgical Revision
            </button>

            <button
              className={`btn ${canApproveOrReject ? "btn-danger" : "btn-disabled"}`}
              onClick={() => handleAction("rejected")}
              disabled={isSubmitting || !canApproveOrReject}
              title={!canApproveOrReject ? "Only Reviewer or Admin can reject proposals" : ""}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
              Reject Proposal
            </button>
          </>
        )}

        {isCompleted && (
          <a
            href={getDownloadUrl(threadId)}
            className="btn btn-primary"
            download
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download Publication PDF
          </a>
        )}
      </div>
    </div>
  );
};
