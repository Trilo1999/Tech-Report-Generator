import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { RoleType } from "../types/auth";

interface AuthModalProps {
  isOpen: boolean;
  initialMode?: "login" | "register";
  onClose: () => void;
  onSuccess: (msg: string) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  initialMode = "login",
  onClose,
  onSuccess,
}) => {
  const { login, register, loginAsDemo } = useAuth();
  const [tab, setTab] = useState<"login" | "register">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<RoleType>("researcher");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setTab(initialMode);
      setError(null);
    }
  }, [isOpen, initialMode]);

  if (!isOpen) return null;

  const handleDemoClick = async (targetRole: RoleType) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await loginAsDemo(targetRole);
      onSuccess(`Signed in as Demo ${targetRole.toUpperCase()}`);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to sign in with demo credentials");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (tab === "login") {
        await login(email, password);
        onSuccess("Welcome back! Signed in successfully.");
      } else {
        await register(email, name, password, role);
        onSuccess("Account created and signed in successfully!");
      }
      onClose();
    } catch (err: any) {
      setError(err.message || "Authentication failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <div className="brand-icon" style={{ width: 28, height: 28, borderRadius: 8 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
            </div>
            <div>
              <h3>{tab === "login" ? "Sign In to Your Account" : "Create New Account"}</h3>
              <p className="modal-subtitle">Authenticate for RBAC protected research workflows</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        {/* Quick Demo Switcher */}
        <div className="demo-login-box">
          <div className="demo-box-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            <span>One-Click Role Testing (Pre-seeded Accounts)</span>
          </div>
          <div className="demo-grid">
            <button
              type="button"
              className="demo-btn role-admin"
              disabled={isSubmitting}
              onClick={() => handleDemoClick("admin")}
            >
              <span className="demo-role-badge badge-admin">ADMIN</span>
              <span className="demo-role-desc">Full System Privileges</span>
            </button>
            <button
              type="button"
              className="demo-btn role-researcher"
              disabled={isSubmitting}
              onClick={() => handleDemoClick("researcher")}
            >
              <span className="demo-role-badge badge-researcher">RESEARCHER</span>
              <span className="demo-role-desc">Launch & Request Revisions</span>
            </button>
            <button
              type="button"
              className="demo-btn role-reviewer"
              disabled={isSubmitting}
              onClick={() => handleDemoClick("reviewer")}
            >
              <span className="demo-role-badge badge-reviewer">REVIEWER</span>
              <span className="demo-role-desc">Approve / Reject Verdicts</span>
            </button>
            <button
              type="button"
              className="demo-btn role-viewer"
              disabled={isSubmitting}
              onClick={() => handleDemoClick("viewer")}
            >
              <span className="demo-role-badge badge-viewer">VIEWER</span>
              <span className="demo-role-desc">Read-Only & PDF Download</span>
            </button>
          </div>
        </div>

        <div className="divider-text">
          <span>Or {tab === "login" ? "enter your email & password" : "fill out your registration details"}</span>
        </div>

        {/* Modal Tabs */}
        <div className="modal-tabs">
          <button
            type="button"
            className={`modal-tab ${tab === "login" ? "active" : ""}`}
            onClick={() => { setTab("login"); setError(null); }}
          >
            Log In
          </button>
          <button
            type="button"
            className={`modal-tab ${tab === "register" ? "active" : ""}`}
            onClick={() => { setTab("register"); setError(null); }}
          >
            Sign Up
          </button>
        </div>

        {error && <div className="auth-error-banner">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {tab === "register" && (
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Alex Rivera"
                disabled={isSubmitting}
              />
            </div>
          )}

          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex@antigravity.ai"
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              disabled={isSubmitting}
            />
          </div>

          {tab === "register" && (
            <div className="form-group">
              <label>Assign Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as RoleType)}
                disabled={isSubmitting}
              >
                <option value="researcher">Researcher (Launch tasks & revise drafts)</option>
                <option value="reviewer">Reviewer (Approve / reject & feedback)</option>
                <option value="viewer">Viewer (Read-only observation & exports)</option>
              </select>
            </div>
          )}

          <button type="submit" className="btn btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <div className="spinner"></div> Authenticating...
              </>
            ) : tab === "login" ? (
              "Log In to Session"
            ) : (
              "Create Account & Sign In"
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
