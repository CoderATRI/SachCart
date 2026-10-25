"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import StageCards from "@/components/StageCards";
import ScoreDial from "@/components/ScoreDial";
import FindingCard from "@/components/FindingCard";
import { getAuditReport, toggleWatch, AuditReport } from "@/lib/api";

export default function AuditPage() {
  const routeParams = useParams();
  const id = routeParams?.id as string;
  const [report, setReport] = useState<AuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [streamingUrl, setStreamingUrl] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string | null>("Initializing checkout truth agent...");
  const [currentStage, setCurrentStage] = useState<string>("listing");
  const [copied, setCopied] = useState(false);
  const [watchActive, setWatchActive] = useState(false);

  const [reconnecting, setReconnecting] = useState(false);

  useEffect(() => {
    if (!id) return;
    let es: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;
    let active = true;

    async function checkStatus() {
      try {
        const data = await getAuditReport(id);
        if (!active) return false;
        setReport(data);
        setWatchActive(data.watch);
        if (data.streaming_url) {
          setStreamingUrl(data.streaming_url);
        }
        if (data.status === "done" || data.status === "failed") {
          setLoading(false);
          setReconnecting(false);
          if (pollInterval) clearInterval(pollInterval);
          if (es) {
            es.close();
            es = null;
          }
          return true;
        }
      } catch {}
      return false;
    }

    function connectSSE() {
      if (es) {
        es.close();
        es = null;
      }
      try {
        es = new EventSource(`/api/audits/${id}/events`);
        es.onopen = () => {
          if (active) setReconnecting(false);
        };
        es.onmessage = (event) => {
          if (!active) return;
          setReconnecting(false);
          try {
            const parsed = JSON.parse(event.data);
            if (parsed.type === "STREAMING_URL" && parsed.streaming_url) {
              setStreamingUrl(parsed.streaming_url);
            } else if (parsed.type === "PROGRESS" && parsed.purpose) {
              setProgressMessage(parsed.purpose);
              const p = parsed.purpose.toLowerCase();
              if (p.includes("cart") || p.includes("basket")) {
                setCurrentStage("cart");
              } else if (p.includes("checkout") || p.includes("guest") || p.includes("shipping")) {
                setCurrentStage("checkout");
              }
            } else if (parsed.type === "COMPLETE" || parsed.type === "AUDIT_FINISHED") {
              checkStatus();
            }
          } catch {}
        };
        es.onerror = async () => {
          if (!active) return;
          setReconnecting(true);
          const finished = await checkStatus();
          if (!finished && active) {
            setTimeout(() => {
              if (active) connectSSE();
            }, 3000);
          }
        };
      } catch {}
    }

    async function start() {
      const finished = await checkStatus();
      if (finished || !active) return;
      connectSSE();

      pollInterval = setInterval(async () => {
        const isDone = await checkStatus();
        if (isDone && pollInterval) {
          clearInterval(pollInterval);
        }
      }, 3000);
    }

    start();

    return () => {
      active = false;
      if (es) es.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [id]);

  const handleToggleWatch = async () => {
    try {
      const res = await toggleWatch(id);
      setWatchActive(res.watch);
    } catch {}
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getVerdict = (score: number) => {
    if (score >= 80) {
      return "Clean and honest checkout experience with minimal regulatory or price discrepancies.";
    }
    if (score >= 50) {
      return "Moderate dark patterns detected. Review add-ons, countdown urgency, and drip charges carefully.";
    }
    return "Severe dark patterns and price discrepancies identified under India CCPA 2023 Guidelines.";
  };

  if (!report || report.status === "queued" || report.status === "running") {
    return (
      <main className="container">
        <header className="header-bar">
          <a href="/" className="logo-wrap">
            <div className="logo-icon">S</div>
            <span className="logo-text">SachCart</span>
          </a>
          <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Audit #{typeof id === "string" ? id.slice(0, 8) : ""}
          </span>
        </header>

        <section className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
          <h2 style={{ fontSize: "24px", fontWeight: 700, color: "var(--headings)", marginBottom: "8px" }}>
            Autonomous Checkout Agent in Progress
          </h2>
          <p style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "24px" }}>
            Target: <span style={{ fontWeight: 600, color: "var(--text-main)" }}>{report?.url || "Fetching listing..."}</span>
          </p>

          <StageCards stage={currentStage} progressMessage={progressMessage} />

          {streamingUrl && (
            <div style={{ marginTop: "24px" }}>
              <a
                href={streamingUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "10px 18px",
                  borderRadius: "8px",
                  background: "var(--primary-light)",
                  color: "var(--primary)",
                  fontWeight: 600,
                  fontSize: "14px",
                }}
              >
                Watch Live Browser Session ↗
              </a>
            </div>
          )}

          {reconnecting && (
            <div
              style={{
                marginTop: "16px",
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 14px",
                borderRadius: "6px",
                background: "var(--warning-high-bg)",
                color: "var(--warning-high)",
                fontSize: "13px",
                fontWeight: 600,
              }}
            >
              ● Reconnecting to live stream...
            </div>
          )}
        </section>
      </main>
    );
  }

  if (!report || report.status === "failed") {
    const failureReason = report?.failure_reason || "The retailer blocked automated guest access or required user login to view cart.";
    return (
      <main className="container">
        <header className="header-bar">
          <a href="/" className="logo-wrap">
            <div className="logo-icon">S</div>
            <span className="logo-text">SachCart</span>
          </a>
        </header>
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <h2 style={{ color: "var(--warning-high)", fontSize: "22px", fontWeight: 700, marginBottom: "8px" }}>
            Audit Inconclusive or Failed
          </h2>
          <p style={{ color: "var(--text-main)", fontWeight: 500, fontSize: "15px", marginBottom: "20px" }}>
            {failureReason}
          </p>
          <a
            href="/"
            style={{
              padding: "10px 20px",
              background: "var(--primary)",
              color: "#FFF",
              borderRadius: "8px",
              fontWeight: 600,
              fontSize: "14px",
            }}
          >
            Audit Another Product
          </a>
        </div>
      </main>
    );
  }

  const score = report.score ?? 100;
  const whatsappText = `Checkout Truth Audit for ${report.domain}: Deal Integrity Score is ${score}/100. Findings: ${report.findings.length} dark patterns. View report: ${typeof window !== "undefined" ? window.location.href : ""}`;

  return (
    <main className="container">
      <header className="header-bar">
        <a href="/" className="logo-wrap">
          <div className="logo-icon">S</div>
          <span className="logo-text">SachCart</span>
        </a>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleCopyLink}
            style={{
              padding: "8px 14px",
              background: "#FFFFFF",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              color: "var(--text-main)",
            }}
          >
            {copied ? "Link Copied!" : "Copy Report Link"}
          </button>
          <a
            href={`https://wa.me/?text=${encodeURIComponent(whatsappText)}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: "8px 14px",
              background: "#25D366",
              color: "#FFFFFF",
              borderRadius: "8px",
              fontSize: "13px",
              fontWeight: 600,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            Share on WhatsApp
          </a>
        </div>
      </header>

      <section className="card" style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--primary)", textTransform: "uppercase" }}>
                {report.domain}
              </span>
              <span
                style={{
                  fontSize: "12px",
                  padding: "2px 8px",
                  borderRadius: "9999px",
                  background: "var(--primary-light)",
                  color: "var(--primary)",
                  fontWeight: 600,
                }}
              >
                Coverage: {report.reached_stage ? report.reached_stage.replace(/_/g, " ") : "Complete"}
              </span>
            </div>
            <h1 style={{ fontSize: "22px", fontWeight: 700, color: "var(--headings)", maxWidth: "700px" }}>
              {report.listing?.title || report.url}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={handleToggleWatch}
              style={{
                padding: "8px 14px",
                borderRadius: "8px",
                border: "1px solid var(--border)",
                background: watchActive ? "var(--primary-light)" : "#FFFFFF",
                color: watchActive ? "var(--primary)" : "var(--text-muted)",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {watchActive ? "✓ Watching Weekly" : "+ Watch Weekly"}
            </button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "24px", marginTop: "32px", alignItems: "center" }}>
          <ScoreDial score={score} />
          <div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--headings)", marginBottom: "8px" }}>
              Audit Verdict
            </h3>
            <p style={{ fontSize: "14px", color: "var(--text-main)", lineHeight: 1.6, marginBottom: "16px" }}>
              {getVerdict(score)}
            </p>

            {report.score_change !== null && report.score_change !== undefined && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  background: report.score_change >= 0 ? "var(--primary-light)" : "var(--warning-high-bg)",
                  color: report.score_change >= 0 ? "var(--primary)" : "var(--warning-high)",
                  fontSize: "12px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                Score change: {report.score_change >= 0 ? `+${report.score_change}` : report.score_change} pts vs last week
              </div>
            )}

            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", fontSize: "13px", color: "var(--text-muted)" }}>
              {report.listing?.sale_price && (
                <div>
                  <span style={{ display: "block", fontSize: "11px", textTransform: "uppercase" }}>Listed Sale Price</span>
                  <span style={{ fontWeight: 700, fontSize: "16px", color: "var(--headings)" }}>
                    {report.listing.currency || "₹"}{report.listing.sale_price}
                  </span>
                </div>
              )}
              {report.listing?.mrp && (
                <div>
                  <span style={{ display: "block", fontSize: "11px", textTransform: "uppercase" }}>Stated MRP</span>
                  <span style={{ textDecoration: "line-through", fontSize: "15px" }}>
                    {report.listing.currency || "₹"}{report.listing.mrp}
                  </span>
                </div>
              )}
              {report.listing?.discount_badge_text && (
                <div>
                  <span style={{ display: "block", fontSize: "11px", textTransform: "uppercase" }}>Badge Claim</span>
                  <span style={{ fontWeight: 600, color: "var(--warning-high)" }}>
                    {report.listing.discount_badge_text}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {report.competitor_prices && report.competitor_prices.length > 0 && (
        <section className="card" style={{ marginBottom: "24px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--headings)", marginBottom: "16px" }}>
            Cross-Retailer Price Comparison
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {report.listing?.sale_price && (
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ width: "120px", fontSize: "13px", fontWeight: 700, color: "var(--primary)" }}>
                  {report.domain} (Target)
                </span>
                <div style={{ flex: 1, background: "#EAEFEF", height: "18px", borderRadius: "9999px", overflow: "hidden" }}>
                  <div style={{ background: "var(--primary)", height: "100%", width: "100%" }} />
                </div>
                <span style={{ width: "80px", textAlign: "right", fontWeight: 700, fontSize: "13px" }}>
                  ₹{report.listing.sale_price}
                </span>
              </div>
            )}
            {report.competitor_prices.map((comp) => (
              <div key={comp.domain} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ width: "120px", fontSize: "13px", color: "var(--text-muted)" }}>
                  {comp.domain}
                </span>
                <div style={{ flex: 1, background: "#EAEFEF", height: "18px", borderRadius: "9999px", overflow: "hidden" }}>
                  <div
                    style={{
                      background: "#A3B8B5",
                      height: "100%",
                      width: report.listing?.sale_price
                        ? `${Math.min(100, Math.round((comp.price / report.listing.sale_price) * 100))}%`
                        : "70%",
                    }}
                  />
                </div>
                <span style={{ width: "80px", textAlign: "right", fontWeight: 600, fontSize: "13px", color: "var(--text-muted)" }}>
                  ₹{comp.price}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section style={{ marginBottom: "24px" }}>
        <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--headings)", marginBottom: "16px" }}>
          CCPA 2023 Dark Pattern Findings ({report.findings.length})
        </h3>
        {report.findings.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "32px", color: "var(--text-muted)" }}>
            No deceptive patterns or undisclosed fees detected in this checkout flow.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
            {report.findings.map((f, idx) => (
              <FindingCard key={f.id || idx} finding={f} />
            ))}
          </div>
        )}
      </section>

      {report.evidence && report.evidence.length > 0 && (
        <section className="card">
          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--headings)", marginBottom: "12px" }}>
            Captured Evidence ({report.evidence.length})
          </h3>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            {report.evidence.map((ev) => (
              <a
                key={ev.id}
                href={`/api/audits/${report.id}/evidence/${ev.id}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: "8px 14px",
                  borderRadius: "8px",
                  background: "var(--primary-light)",
                  color: "var(--primary)",
                  fontSize: "13px",
                  fontWeight: 600,
                  textDecoration: "none",
                }}
              >
                View {ev.kind === "video" ? "Session Recording" : "Screenshot"} ↗
              </a>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
