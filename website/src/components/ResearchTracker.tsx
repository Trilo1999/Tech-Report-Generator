import React, { useEffect, useState } from "react";
import { ResearchTaskSummary } from "../types/research";
import { deleteResearchTaskApi, listUserTasks } from "../services/api";
import { useAuth } from "../context/AuthContext";

interface ResearchTrackerProps {
  activeThreadId?: string;
  onSelectTask: (threadId: string) => void;
  onShowToast: (msg: string) => void;
  refreshTrigger?: number;
}

export const ResearchTracker: React.FC<ResearchTrackerProps> = ({
  activeThreadId,
  onSelectTask,
  onShowToast,
  refreshTrigger = 0,
}) => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<ResearchTaskSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "running" | "review" | "completed">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  const fetchTasks = async (silent = false) => {
    if (!user) {
      setTasks([]);
      return;
    }
    if (!silent) setIsLoading(true);
    try {
      const data = await listUserTasks();
      setTasks(data);
    } catch (err: any) {
      if (!silent) {
        console.warn("Failed to fetch research tasks:", err);
      }
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  // Initial fetch once on mount or when user changes
  useEffect(() => {
    fetchTasks();
  }, [user?.id, refreshTrigger]);

  const handleDelete = async (threadId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Delete research record '${threadId}' from your history?`)) {
      return;
    }
    setIsDeleting(threadId);
    try {
      await deleteResearchTaskApi(threadId);
      setTasks((prev) => prev.filter((t) => t.thread_id !== threadId));
      onShowToast("Research task removed from history.");
    } catch (err: any) {
      alert(`Delete failed: ${err.message || err}`);
    } finally {
      setIsDeleting(null);
    }
  };

  const formatTimestamp = (timestamp: number) => {
    if (!timestamp) return "Just now";
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSec < 60) return "Just now";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (task: ResearchTaskSummary) => {
    if (task.is_running || task.status === "running" || task.status === "processing") {
      return (
        <span className="task-badge task-badge-running">
          <span className="task-pulse-dot"></span>
          Running...
        </span>
      );
    }
    if (task.is_pending_review || task.status === "review_pending") {
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
    if (task.status === "completed") {
      return (
        <span className="task-badge task-badge-completed">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          Completed
        </span>
      );
    }
    if (task.status === "failed") {
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

  // Filter tasks
  const filteredTasks = tasks.filter((task) => {
    const matchesSearch =
      task.topic.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.thread_id.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filter === "running") {
      return task.is_running || task.status === "running" || task.status === "processing";
    }
    if (filter === "review") {
      return task.is_pending_review || task.status === "review_pending";
    }
    if (filter === "completed") {
      return task.status === "completed";
    }
    return true;
  });

  const runningCount = tasks.filter((t) => t.is_running || t.status === "running").length;
  const reviewCount = tasks.filter((t) => t.is_pending_review || t.status === "review_pending").length;
  const completedCount = tasks.filter((t) => t.status === "completed").length;

  if (!user) {
    return (
      <div className="tracker-card tracker-unauth-box">
        <div className="tracker-unauth-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
        </div>
        <div>
          <h4>Log in to Track & Persist Your Researches</h4>
          <p>
            Your research sessions are automatically linked to your authenticated profile. Log in or create an account to view, resume, or download your technical reports anytime.
          </p>
        </div>
      </div>
    );
  }

  return (
    <section className="tracker-card">
      <div className="tracker-header">
        <div className="tracker-title-group">
          <div className="tracker-icon-badge">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <div>
            <h3 className="tracker-heading">
              My Research Hub & Status Tracker
              <span className="tracker-count-tag">{tasks.length} {tasks.length === 1 ? "task" : "tasks"}</span>
            </h3>
            <p className="tracker-subheading">
              Persistent research tracking for <strong>{user.name}</strong> ({user.role}) &bull; Monitor live agent steps and resume past reports
            </p>
          </div>
        </div>

        <div className="tracker-actions">
          <button
            type="button"
            className="btn-refresh-tracker"
            onClick={() => fetchTasks(false)}
            disabled={isLoading}
            title="Refresh tasks status"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={isLoading ? "spin-icon" : ""}
            >
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="tracker-toolbar">
        <div className="tracker-filter-tabs">
          <button
            type="button"
            className={`tracker-tab ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All ({tasks.length})
          </button>
          <button
            type="button"
            className={`tracker-tab ${filter === "running" ? "active" : ""}`}
            onClick={() => setFilter("running")}
          >
            {runningCount > 0 && <span className="tab-pulse-dot"></span>}
            In Progress ({runningCount})
          </button>
          <button
            type="button"
            className={`tracker-tab ${filter === "review" ? "active" : ""}`}
            onClick={() => setFilter("review")}
          >
            Review Pending ({reviewCount})
          </button>
          <button
            type="button"
            className={`tracker-tab ${filter === "completed" ? "active" : ""}`}
            onClick={() => setFilter("completed")}
          >
            Completed ({completedCount})
          </button>
        </div>

        <div className="tracker-search-box">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            placeholder="Search topic or thread ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              type="button"
              className="btn-clear-search"
              onClick={() => setSearchQuery("")}
            >
              &times;
            </button>
          )}
        </div>
      </div>

      {/* Tasks Table / List */}
      <div className="tracker-tasks-list">
        {filteredTasks.length === 0 ? (
          <div className="tracker-empty-state">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.4 }}>
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="8" y1="12" x2="16" y2="12"></line>
            </svg>
            <p>
              {tasks.length === 0
                ? "No research tasks found yet. Type a query above and click 'Run Autonomous Research' to track your first report!"
                : "No research tasks match the current filter criteria."}
            </p>
          </div>
        ) : (
          filteredTasks.map((task) => {
            const isActive = task.thread_id === activeThreadId;
            return (
              <div
                key={task.thread_id}
                className={`tracker-task-item ${isActive ? "active-thread" : ""}`}
                onClick={() => onSelectTask(task.thread_id)}
                title="Click to view and track this research"
              >
                <div className="task-item-main">
                  <div className="task-item-title-row">
                    <span className="task-item-topic">{task.topic}</span>
                    {isActive && <span className="task-active-badge">Active View</span>}
                  </div>
                  <div className="task-item-meta">
                    <code className="task-item-id">{task.thread_id}</code>
                    <span className="task-meta-dot">&bull;</span>
                    <span className="task-item-time">{formatTimestamp(task.created_at)}</span>
                    {task.evidence_count !== undefined && task.evidence_count > 0 && (
                      <>
                        <span className="task-meta-dot">&bull;</span>
                        <span className="task-item-evidence">
                          {task.evidence_count} evidence items
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <div className="task-item-status-col">
                  {getStatusBadge(task)}
                </div>

                <div className="task-item-actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className={`btn-track-task ${isActive ? "btn-track-active" : ""}`}
                    onClick={() => onSelectTask(task.thread_id)}
                    title="Load status into dashboard"
                  >
                    {isActive ? "Viewing" : "Track / View"}
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>

                  <button
                    type="button"
                    className="btn-delete-task"
                    onClick={(e) => handleDelete(task.thread_id, e)}
                    disabled={isDeleting === task.thread_id}
                    title="Delete task from history"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
};
