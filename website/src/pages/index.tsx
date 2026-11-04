import React, { ReactNode } from "react";
import LayoutProvider from "@theme/Layout/Provider";
import { PageMetadata } from "@docusaurus/theme-common";
import BrowserOnly from "@docusaurus/BrowserOnly";
import { AuthProvider } from "@site/src/context/AuthContext";
import ResearchApp from "@site/src/components/ResearchApp";

export default function Home(): ReactNode {
  return (
    <LayoutProvider>
      <PageMetadata
        title="AI Technical Research & Decision Report Agent"
        description="Autonomous multi-agent research, empirical benchmarking, and executive technical decision reports."
      />
      <BrowserOnly
        fallback={
          <div
            style={{
              padding: "80px 20px",
              textAlign: "center",
              minHeight: "70vh",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                border: "3px solid rgba(56, 189, 248, 0.2)",
                borderTopColor: "#38BDF8",
                animation: "spin 1s linear infinite",
                marginBottom: "20px",
              }}
            />
            <h2 style={{ color: "#F8FAFC", marginBottom: "8px" }}>
              Loading AI Research Agent...
            </h2>
            <p style={{ color: "#94A3B8", fontSize: "14px" }}>
              Initializing multi-agent workflow & executive research dashboard
            </p>
          </div>
        }
      >
        {() => (
          <AuthProvider>
            <main style={{ minHeight: "100vh" }}>
              <ResearchApp />
            </main>
          </AuthProvider>
        )}
      </BrowserOnly>
    </LayoutProvider>
  );
}
