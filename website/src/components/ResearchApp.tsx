import React, { useEffect, useRef, useState } from "react";
import { Navbar } from "./Navbar";
import { Hero } from "./Hero";
import { TopicInput } from "./TopicInput";
import { ResearchTracker } from "./ResearchTracker";
import { ResearchDetailsPage } from "./ResearchDetailsPage";
import { Toast } from "./Toast";
import { AuthModal } from "./AuthModal";
import { ProfileModal } from "./ProfileModal";
import { startResearch } from "../services/api";
import { useAuth } from "../context/AuthContext";

function getInitialRoute(): { view: "home" | "details"; threadId: string | null } {
  if (typeof window === "undefined") {
    return { view: "home", threadId: null };
  }
  const path = window.location.pathname;
  if (path.startsWith("/research/")) {
    const id = path.replace("/research/", "").trim();
    if (id) return { view: "details", threadId: id };
  }
  const hash = window.location.hash;
  if (hash.startsWith("#/research/") || hash.startsWith("#research/")) {
    const id = hash.replace(/^#\/?research\//, "").trim();
    if (id) return { view: "details", threadId: id };
  }
  return { view: "home", threadId: null };
}

export const App: React.FC = () => {
  const { user } = useAuth();
  const [topic, setTopic] = useState("python vs java Architecture Evaluation on llm integration");
  const [view, setView] = useState<"home" | "details">(() => getInitialRoute().view);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(() => getInitialRoute().threadId);

  const [isLaunching, setIsLaunching] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<"login" | "register">("login");
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [refreshTrackerTrigger, setRefreshTrackerTrigger] = useState(0);

  const trackerRef = useRef<HTMLDivElement | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const openAuth = (mode: "login" | "register") => {
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  const scrollToTracker = () => {
    if (view !== "home") {
      navigateToHome();
      setTimeout(() => {
        trackerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } else {
      trackerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // Browser Navigation / Popstate Listener
  useEffect(() => {
    const handlePopState = () => {
      const route = getInitialRoute();
      setView(route.view);
      setSelectedThreadId(route.threadId);
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigateToDetails = (threadId: string) => {
    setSelectedThreadId(threadId);
    setView("details");
    if (typeof window !== "undefined") {
      localStorage.setItem("active_research_thread_id", threadId);
      window.history.pushState({ view: "details", threadId }, "", `/#research/${threadId}`);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const navigateToHome = () => {
    setSelectedThreadId(null);
    setView("home");
    if (typeof window !== "undefined") {
      window.history.pushState({ view: "home" }, "", "/");
      window.scrollTo({ top: 0, behavior: "smooth" });
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
      const initialTaskState = await startResearch(targetTopic);
      setRefreshTrackerTrigger((prev) => prev + 1);
      showToast("Research started! Opening research details...");
      // Immediately navigate to the newly created research details page
      navigateToDetails(initialTaskState.thread_id);
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

  const handleSelectTask = (threadId: string) => {
    navigateToDetails(threadId);
  };

  return (
    <div className="container">
      <Navbar
        threadId={selectedThreadId || undefined}
        onOpenAuthModal={openAuth}
        onOpenProfileModal={() => setIsProfileModalOpen(true)}
        onShowToast={showToast}
        onScrollToTracker={scrollToTracker}
        onNavigateHome={navigateToHome}
      />

      {view === "home" ? (
        <>
          <Hero />

          <TopicInput
            topic={topic}
            setTopic={setTopic}
            onLaunch={handleLaunchResearch}
            isLoading={isLaunching}
            onOpenAuthModal={() => openAuth("login")}
          />

          {/* Persistent Research Hub & Status Tracker */}
          <div ref={trackerRef}>
            <ResearchTracker
              activeThreadId={selectedThreadId || undefined}
              onSelectTask={handleSelectTask}
              onShowToast={showToast}
              refreshTrigger={refreshTrackerTrigger}
            />
          </div>
        </>
      ) : (
        selectedThreadId && (
          <ResearchDetailsPage
            threadId={selectedThreadId}
            onBack={navigateToHome}
            onShowToast={showToast}
            onOpenAuthModal={openAuth}
          />
        )
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
