import React, { useState } from "react";
import { Navbar } from "./components/Navbar";
import { Hero } from "./components/Hero";
import { TopicInput } from "./components/TopicInput";
import { WorkflowStepper } from "./components/WorkflowStepper";
import { MetricsGrid } from "./components/MetricsGrid";
import { CitationLegend } from "./components/CitationLegend";
import { UnsupportedClaims } from "./components/UnsupportedClaims";
import { ReportViewer } from "./components/ReportViewer";
import { ReviewStation } from "./components/ReviewStation";
import { Toast } from "./components/Toast";
import { ResearchWorkflowState, ReviewSubmission } from "./types/research";
import { startResearch, submitReview } from "./services/api";

export const App: React.FC = () => {
  const [topic, setTopic] = useState("python vs java Architecture Evaluation on llm integration");
  const [workflowState, setWorkflowState] = useState<ResearchWorkflowState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleLaunchResearch = async (overrideTopic?: string) => {
    const targetTopic = overrideTopic || topic;
    if (!targetTopic.trim() || isLoading) return;

    setIsLoading(true);
    try {
      const data = await startResearch(targetTopic);
      setWorkflowState(data);
      showToast("Research synthesis initiated successfully!");
    } catch (err: any) {
      alert(`Research launch failed: ${err.message || err}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitReview = async (review: ReviewSubmission) => {
    if (!workflowState?.thread_id || isSubmittingReview) return;

    setIsSubmittingReview(true);
    try {
      const updated = await submitReview(workflowState.thread_id, review);
      setWorkflowState(updated);
      if (review.decision === "approved") {
        showToast("Report approved and publication PDF generated!");
      } else if (review.decision === "revise") {
        showToast("Surgical revision applied successfully!");
      } else {
        showToast("Proposal rejected.");
      }
    } catch (err: any) {
      alert(`Review submission failed: ${err.message || err}`);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleCopyReport = () => {
    if (!workflowState?.draft_report) return;
    const { title, sections } = workflowState.draft_report;
    const text = `${title}\n\n` + Object.entries(sections).map(([k, v]) => `## ${k}\n${v}`).join("\n\n");
    navigator.clipboard.writeText(text).then(() => {
      showToast("Full report copied to clipboard!");
    });
  };

  return (
    <div className="container">
      <Navbar threadId={workflowState?.thread_id} />
      <Hero />

      <TopicInput
        topic={topic}
        setTopic={setTopic}
        onLaunch={handleLaunchResearch}
        isLoading={isLoading}
      />

      <WorkflowStepper state={workflowState} isLoading={isLoading} />

      {workflowState && <MetricsGrid state={workflowState} />}
      {workflowState && <CitationLegend />}

      {workflowState?.unsupported_claims && (
        <UnsupportedClaims claims={workflowState.unsupported_claims} />
      )}

      {workflowState?.draft_report && (
        <ReportViewer
          draft={workflowState.draft_report}
          threadId={workflowState.thread_id}
          isCompleted={workflowState.status === "completed"}
          onCopy={handleCopyReport}
        />
      )}

      {workflowState?.draft_report && (
        <ReviewStation
          sections={workflowState.draft_report.sections}
          threadId={workflowState.thread_id}
          isPendingReview={workflowState.is_pending_review}
          isCompleted={workflowState.status === "completed"}
          onSubmitReview={handleSubmitReview}
          isSubmitting={isSubmittingReview}
        />
      )}

      <Toast message={toastMessage} />
    </div>
  );
};

export default App;
