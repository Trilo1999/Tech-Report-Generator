import React, { useEffect, useRef, useState } from "react";
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
import { AuthModal } from "./components/AuthModal";
import { ProfileModal } from "./components/ProfileModal";
import { ResearchTracker } from "./components/ResearchTracker";
import { ResearchWorkflowState, ReviewSubmission } from "./types/research";
import { getResearchStatus, startResearch, submitReview } from "./services/api";
import { useAuth } from "./context/AuthContext";

export const App: React.FC = () => {
  const { user } = useAuth();
  const [topic, setTopic] = useState("python vs java Architecture Evaluation on llm integration");
  const [workflowState, setWorkflowState] = useState<ResearchWorkflowState | null>(null);
  const [isLaunching, setIsLaunching] = useState(false);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<"login" | "register">("login");
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [refreshTrackerTrigger, setRefreshTrackerTrigger] = useState(0);

  const trackerRef = useRef<HTMLDivElement | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const openAuth = (mode: "login" | "register") => {
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  const scrollToTracker = () => {
    trackerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Restore persistent active research on load or user switch
  useEffect(() => {
    if (!user) {
      setWorkflowState(null);
      return;
    }
    const savedThreadId = localStorage.getItem("active_research_thread_id");
    if (savedThreadId && !workflowState) {
      getResearchStatus(savedThreadId)
        .then((state) => {
          setWorkflowState(state);
          if (state.topic) setTopic(state.topic);
        })
        .catch(() => {
          localStorage.removeItem("active_research_thread_id");
        });
    }
  }, [user]);

  // Status Polling Effect
  useEffect(() => {
    const isRunning =
      workflowState?.is_running ||
      workflowState?.status === "running" ||
      workflowState?.status === "processing" ||
      workflowState?.status === "review_resuming";

    if (!isRunning || !workflowState?.thread_id) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      setElapsedSeconds(0);
      return;
    }

    // Timer for elapsed seconds
    const timerInterval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    // Poller every 1.5 seconds
    const threadId = workflowState.thread_id;
    let consecutiveErrors = 0;
    const poller = setInterval(async () => {
      try {
        const updated = await getResearchStatus(threadId);
        consecutiveErrors = 0;
        setWorkflowState(updated);

        // Check if finished running or failed
        if (!updated.is_running && updated.status !== "running" && updated.status !== "processing" && updated.status !== "review_resuming") {
          clearInterval(poller);
          clearInterval(timerInterval);
          setIsSubmittingReview(false);
          setRefreshTrackerTrigger((prev) => prev + 1);

          if (updated.status === "failed") {
            showToast(`Workflow task failed: ${updated.error || "Unknown error"}`);
          } else if (updated.is_pending_review) {
            showToast("Draft report ready! Paused at Human Review checkpoint.");
          } else if (updated.status === "completed") {
            showToast("Publication PDF report generated successfully!");
          }
        }
      } catch (err: any) {
        consecutiveErrors += 1;
        console.warn(`Polling status failed (${consecutiveErrors}/4):`, err);
        if (consecutiveErrors >= 4) {
          clearInterval(poller);
          clearInterval(timerInterval);
          showToast("Server temporarily unavailable. Polling paused.");
        }
      }
    }, 1500);

    pollIntervalRef.current = poller;

    return () => {
      clearInterval(poller);
      clearInterval(timerInterval);
    };
  }, [workflowState?.is_running, workflowState?.status, workflowState?.thread_id]);

  const handleManualRefresh = async () => {
    if (!workflowState?.thread_id) return;
    try {
      const updated = await getResearchStatus(workflowState.thread_id);
      setWorkflowState(updated);
      setRefreshTrackerTrigger((prev) => prev + 1);
      showToast("Status updated from server.");
    } catch (err: any) {
      showToast(`Refresh failed: ${err.message || err}`);
    }
  };

  const handleSelectTask = async (threadId: string) => {
    try {
      const state = await getResearchStatus(threadId);
      setWorkflowState(state);
      if (state.topic) setTopic(state.topic);
      localStorage.setItem("active_research_thread_id", threadId);
      showToast(`Tracking research '${threadId}'`);
    } catch (err: any) {
      showToast(`Failed to load research: ${err.message || err}`);
    }
  };

  const handleLaunchResearch = async (overrideTopic?: string) => {
    const targetTopic = overrideTopic || topic;
    if (!targetTopic.trim() || isLaunching) return;

    if (!user) {
      openAuth("login");
      return;
    }

    setIsLaunching(true);
    try {
      // Dispatches asynchronous background task
      const initialTaskState = await startResearch(targetTopic);
      setWorkflowState(initialTaskState);
      localStorage.setItem("active_research_thread_id", initialTaskState.thread_id);
      setRefreshTrackerTrigger((prev) => prev + 1);
      showToast("Research task started in background! Live monitoring active.");
    } catch (err: any) {
      const msg = err.message || String(err);
      if (msg.includes("401") || msg.toLowerCase().includes("unauthorized") || msg.toLowerCase().includes("token")) {
        showToast("Authentication required. Please log in.");
        openAuth("login");
      } else {
        alert(`Research launch failed: ${msg}`);
      }
    } finally {
      setIsLaunching(false);
    }
  };

  const handleSubmitReview = async (review: ReviewSubmission) => {
    if (!workflowState?.thread_id || isSubmittingReview) return;

    if (!user) {
      openAuth("login");
      return;
    }

    setIsSubmittingReview(true);
    try {
      // Dispatches asynchronous review resumption in background
      const updated = await submitReview(workflowState.thread_id, review);
      setWorkflowState(updated);
      setRefreshTrackerTrigger((prev) => prev + 1);
      showToast(
        review.decision === "approved"
          ? "Approval dispatched! Generating publication PDF in background..."
          : review.decision === "revise"
          ? "Surgical revision requested in background..."
          : "Proposal rejection dispatched."
      );
    } catch (err: any) {
      const msg = err.message || String(err);
      if (msg.includes("401")) {
        showToast("Session expired. Please log in.");
        openAuth("login");
      } else {
        alert(`Review submission failed: ${msg}`);
      }
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

  const isTaskRunning =
    workflowState?.is_running ||
    workflowState?.status === "running" ||
    workflowState?.status === "processing" ||
    workflowState?.status === "review_resuming";

  return (
    <div className="container">
      <Navbar
        threadId={workflowState?.thread_id}
        onOpenAuthModal={openAuth}
        onOpenProfileModal={() => setIsProfileModalOpen(true)}
        onShowToast={showToast}
        onScrollToTracker={scrollToTracker}
      />
      <Hero />

      <TopicInput
        topic={topic}
        setTopic={setTopic}
        onLaunch={handleLaunchResearch}
        isLoading={isLaunching || isTaskRunning}
        onOpenAuthModal={() => openAuth("login")}
      />

      {/* Persistent Research Hub & Status Tracker */}
      <div ref={trackerRef}>
        <ResearchTracker
          activeThreadId={workflowState?.thread_id}
          onSelectTask={handleSelectTask}
          onShowToast={showToast}
          refreshTrigger={refreshTrackerTrigger}
        />
      </div>

      {/* Live Asynchronous Background Task Progress Banner */}
      {isTaskRunning && workflowState && (
        <div className="bg-task-banner">
          <div className="bg-task-pulse-icon">
            <div className="task-spinner-ring"></div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
          </div>
          <div className="bg-task-content">
            <div className="bg-task-header">
              <span className="bg-task-title">
                Autonomous Research Executing in Background
              </span>
              <span className="bg-task-timer">Elapsed: {elapsedSeconds}s (polling every 1.5s)</span>
            </div>
            <p className="bg-task-desc">
              Task ID: <code>{workflowState.thread_id}</code> &bull;{" "}
              {workflowState.message || "Agent is synthesizing evidence, executing latency benchmarks, and drafting report non-blockingly."}
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

      <WorkflowStepper state={workflowState} isLoading={isLaunching || isTaskRunning} />

      {workflowState && <MetricsGrid state={workflowState} />}
      {workflowState && (
        <CitationLegend
          evidenceList={workflowState.evidence}
          onShowToast={showToast}
        />
      )}

      {workflowState?.unsupported_claims && (
        <UnsupportedClaims claims={workflowState.unsupported_claims} />
      )}

      {workflowState?.draft_report && (
        <ReportViewer
          draft={workflowState.draft_report}
          threadId={workflowState.thread_id}
          evidenceList={workflowState.evidence}
          isCompleted={workflowState.status === "completed"}
          onCopy={handleCopyReport}
          onShowToast={showToast}
        />
      )}

      {workflowState?.draft_report && (
        <ReviewStation
          sections={workflowState.draft_report.sections}
          threadId={workflowState.thread_id}
          isPendingReview={workflowState.is_pending_review}
          isCompleted={workflowState.status === "completed"}
          onSubmitReview={handleSubmitReview}
          isSubmitting={isSubmittingReview || isTaskRunning}
        />
      )}

      {/* Login & Sign Up Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        initialMode={authModalMode}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={(msg) => showToast(msg)}
      />

      {/* User Profile & Security Details Modal */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        onOpenAuthModal={openAuth}
        onShowToast={showToast}
      />

      <Toast message={toastMessage} />
    </div>
  );
};

export default App;
