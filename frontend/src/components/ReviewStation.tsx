import React, { useState } from "react";
import { ReviewDecision, ReviewSubmission } from "../types/research";
import { getDownloadUrl } from "../services/api";

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
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [selectedSections, setSelectedSections] = useState<string[]>([]);

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
      <h3>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polygon points="12 8 8 12 12 16 12 8"></polygon>
        </svg>
        Human-in-the-Loop Review Station
      </h3>
      <p>
        {isPendingReview
          ? "The workflow is suspended at the checkpoint boundary. Review the evidence-grounded draft above and choose an action:"
          : "This report has completed the human review boundary and is approved for distribution."}
      </p>

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
              disabled={isSubmitting}
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
                  <label key={sec} className={`chip-label ${isSelected ? "selected" : ""}`}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggleSection(sec)}
                      disabled={isSubmitting}
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
              className="btn btn-success"
              onClick={() => handleAction("approved")}
              disabled={isSubmitting}
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
              className="btn btn-amber"
              onClick={() => handleAction("revise")}
              disabled={isSubmitting}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
              Request Surgical Revision
            </button>

            <button
              className="btn btn-danger"
              onClick={() => handleAction("rejected")}
              disabled={isSubmitting}
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
          <a href={getDownloadUrl(threadId)} className="btn btn-primary" download>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download PDF Report
          </a>
        )}
      </div>
    </div>
  );
};
