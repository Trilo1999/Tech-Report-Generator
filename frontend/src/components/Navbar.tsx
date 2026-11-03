import React from "react";
import { useAuth } from "../context/AuthContext";
import { RoleType } from "../types/auth";

interface NavbarProps {
  threadId?: string;
  onOpenAuthModal: (mode: "login" | "register") => void;
  onOpenProfileModal: () => void;
  onShowToast: (msg: string) => void;
  onScrollToTracker?: () => void;
  onNavigateHome?: () => void;
  taskCount?: number;
  runningCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  threadId,
  onOpenAuthModal,
  onOpenProfileModal,
  onShowToast,
  onScrollToTracker,
  onNavigateHome,
  taskCount,
  runningCount,
}) => {
  const { user, logout, loginAsDemo } = useAuth();

  const handleRoleQuickSwitch = async (role: RoleType) => {
    try {
      await loginAsDemo(role);
      onShowToast(`Switched active persona to ${role.toUpperCase()}`);
    } catch (err: any) {
      alert(`Role switch failed: ${err.message || err}`);
    }
  };

  const getRoleBadgeClass = (role: RoleType) => {
    switch (role) {
      case "admin":
        return "badge-admin";
      case "researcher":
        return "badge-researcher";
      case "reviewer":
        return "badge-reviewer";
      case "viewer":
        return "badge-viewer";
      default:
        return "";
    }
  };

  return (
    <nav>
      <div
        className="brand"
        onClick={onNavigateHome}
        style={{ cursor: onNavigateHome ? "pointer" : "default" }}
        title={onNavigateHome ? "Go to Research Hub" : undefined}
      >
        <div className="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span>Antigravity AI</span>
        <span className="brand-badge">2.0 Engine</span>
      </div>

      <div className="nav-controls">
        {/* Quick Persona Switcher */}
        <div className="role-quick-bar">
          <span className="quick-bar-label">Role:</span>
          {(["admin", "researcher", "reviewer", "viewer"] as RoleType[]).map((r) => (
            <button
              key={r}
              type="button"
              className={`role-pill-btn ${user?.role === r ? "active" : ""} ${getRoleBadgeClass(r)}`}
              onClick={() => handleRoleQuickSwitch(r)}
              title={`Instantly test RBAC as ${r}`}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>

        {/* User Identity or Auth Action Buttons */}
        {user ? (
          <div className="nav-user-actions">
            {onScrollToTracker && (
              <button
                type="button"
                className="btn-nav-tracker"
                onClick={onScrollToTracker}
                title="Jump to My Research Hub & Status Tracker"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
                <span>My Researches</span>
                {taskCount !== undefined && taskCount > 0 && (
                  <span className={`nav-task-badge ${runningCount && runningCount > 0 ? "badge-pulsing" : ""}`}>
                    {runningCount && runningCount > 0 ? `${runningCount} active` : taskCount}
                  </span>
                )}
              </button>
            )}

            <button
              type="button"
              className="user-profile-badge-btn"
              onClick={onOpenProfileModal}
              title="Click to view full user profile & permissions"
            >
              <div className="user-avatar" title={user.email}>
                {user.name.slice(0, 2).toUpperCase()}
              </div>
              <div className="user-info">
                <span className="user-name">{user.name}</span>
                <span className={`user-role-tag ${getRoleBadgeClass(user.role)}`}>
                  {user.role}
                </span>
              </div>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.6, marginLeft: 2 }}>
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>

            <button
              type="button"
              className="btn-profile-shortcut"
              onClick={onOpenProfileModal}
              title="Open Profile Modal"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              Profile
            </button>

            <button
              type="button"
              className="btn-icon-signout"
              onClick={() => {
                logout();
                onShowToast("Logged out successfully.");
              }}
              title="Sign Out"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
            </button>
          </div>
        ) : (
          <div className="auth-buttons-group">
            <button
              type="button"
              className="btn btn-outline-login"
              onClick={() => onOpenAuthModal("login")}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
                <polyline points="10 17 15 12 10 7"></polyline>
                <line x1="15" y1="12" x2="3" y2="12"></line>
              </svg>
              Log In
            </button>

            <button
              type="button"
              className="btn btn-primary-signup"
              onClick={() => onOpenAuthModal("register")}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="8.5" cy="7" r="4"></circle>
                <line x1="20" y1="8" x2="20" y2="14"></line>
                <line x1="23" y1="11" x2="17" y2="11"></line>
              </svg>
              Sign Up
            </button>
          </div>
        )}

        {/* Live System Indicator */}
        <div className="nav-status">
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span className="live-dot"></span> Qdrant
          </span>
          {threadId && (
            <>
              <span style={{ opacity: 0.3 }}>|</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                {threadId}
              </span>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};
