import React from "react";
import { useAuth } from "../context/AuthContext";

interface TopicInputProps {
  topic: string;
  setTopic: (topic: string) => void;
  onLaunch: (customTopic?: string) => void;
  isLoading: boolean;
  onOpenAuthModal: () => void;
}

const PRESET_TOPICS = [
  { label: "🐍 Python vs ☕ Java (LLM Integration)", value: "python vs java Architecture Evaluation on llm integration" },
  { label: "🐘 Postgres vs 🍃 MongoDB", value: "PostgreSQL vs MongoDB Architecture Evaluation" },
  { label: "⚛️ React vs 🅰️ Angular", value: "React vs Angular Enterprise Performance Benchmark" },
  { label: "☁️ AWS vs 🔷 Azure TCO", value: "AWS vs Azure Cloud TCO & Infrastructure Evaluation" },
  { label: "☁️ AWS vs 🌐 GCP TCO", value: "AWS vs GCP Cloud TCO & Microservices" },
];

export const TopicInput: React.FC<TopicInputProps> = ({
  topic,
  setTopic,
  onLaunch,
  isLoading,
  onOpenAuthModal,
}) => {
  const { user, hasRole } = useAuth();
  const canStartResearch = hasRole(["admin", "researcher"]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) {
      onOpenAuthModal();
      return;
    }
    if (canStartResearch && topic.trim() && !isLoading) {
      onLaunch();
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          Research Scope & Topic
        </div>

        {/* Role permission status badge */}
        {user && !canStartResearch && (
          <div className="rbac-warning-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
            <span>Role '{user.role}' is read-only for new research launches</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="input-wrapper">
        <div className="search-bar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. React vs Angular architecture, PostgreSQL vs MongoDB, AWS vs Azure TCO..."
            disabled={isLoading || (!!user && !canStartResearch)}
          />
        </div>

        {!user ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={onOpenAuthModal}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
              <polyline points="10 17 15 12 10 7"></polyline>
              <line x1="15" y1="12" x2="3" y2="12"></line>
            </svg>
            Sign In to Launch
          </button>
        ) : (
          <button
            type="submit"
            className={`btn ${canStartResearch ? "btn-primary" : "btn-disabled"}`}
            disabled={isLoading || !topic.trim() || !canStartResearch}
            title={!canStartResearch ? "Restricted: Only Admin and Researcher roles can launch research" : ""}
          >
            {isLoading ? (
              <>
                <div className="spinner"></div> Researching...
              </>
            ) : !canStartResearch ? (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                Launch Restricted ({user.role})
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Launch Autonomous Research
              </>
            )}
          </button>
        )}
      </form>

      <div className="preset-topics">
        <span style={{ fontSize: "12px", color: "var(--text-muted)", marginRight: "4px" }}>
          Suggested Scopes:
        </span>
        {PRESET_TOPICS.map((p) => (
          <button
            key={p.label}
            className="preset-btn"
            disabled={isLoading || (!!user && !canStartResearch)}
            onClick={() => {
              setTopic(p.value);
              if (canStartResearch) onLaunch(p.value);
            }}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
};
