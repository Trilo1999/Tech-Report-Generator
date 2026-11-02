import React from "react";

interface TopicInputProps {
  topic: string;
  setTopic: (topic: string) => void;
  onLaunch: (customTopic?: string) => void;
  isLoading: boolean;
}

const PRESET_TOPICS = [
  { label: "🐍 Python vs ☕ Java (LLM Integration)", value: "python vs java Architecture Evaluation on llm integration" },
  { label: "🐘 Postgres vs 🍃 MongoDB", value: "PostgreSQL vs MongoDB Architecture Evaluation" },
  { label: "⚛️ React vs 🅰️ Angular", value: "React vs Angular Enterprise Performance Benchmark" },
  { label: "☁️ AWS vs GCP TCO", value: "AWS vs GCP Cloud TCO & Microservices" },
];

export const TopicInput: React.FC<TopicInputProps> = ({ topic, setTopic, onLaunch, isLoading }) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (topic.trim() && !isLoading) {
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
            placeholder="e.g. React vs Angular architecture, PostgreSQL vs MongoDB..."
            disabled={isLoading}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={isLoading || !topic.trim()}>
          {isLoading ? (
            <>
              <div className="spinner"></div> Researching...
            </>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              Launch Research
            </>
          )}
        </button>
      </form>

      <div className="presets-container">
        <span className="presets-label">Preset Topics:</span>
        {PRESET_TOPICS.map((preset) => (
          <button
            key={preset.value}
            type="button"
            className="preset-pill"
            onClick={() => {
              setTopic(preset.value);
              onLaunch(preset.value);
            }}
            disabled={isLoading}
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
};
