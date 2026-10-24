"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Tilt from "@/components/Tilt";
import { createAudit } from "@/lib/api";

interface RecentAudit {
  id: string;
  url: string;
  domain: string;
  timestamp: string;
}

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [watch, setWatch] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentAudits, setRecentAudits] = useState<RecentAudit[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("sachcart_recent_audits");
      if (stored) {
        setRecentAudits(JSON.parse(stored));
      }
    } catch {}
  }, []);

  const saveToRecent = (id: string, productUrl: string) => {
    try {
      let domain = "product";
      try {
        domain = new URL(productUrl).hostname;
      } catch {}
      const item: RecentAudit = {
        id,
        url: productUrl,
        domain,
        timestamp: new Date().toLocaleDateString(),
      };
      const updated = [item, ...recentAudits.filter((a) => a.id !== id)].slice(0, 5);
      setRecentAudits(updated);
      localStorage.setItem("sachcart_recent_audits", JSON.stringify(updated));
    } catch {}
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Please paste a product URL to audit.");
      return;
    }
    if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
      setError("URL must start with http:// or https://");
      return;
    }

    setLoading(true);
    try {
      const { id } = await createAudit(trimmed, watch);
      saveToRecent(id, trimmed);
      router.push(`/audit/${id}`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to create audit. Please try again.");
      }
      setLoading(false);
    }
  };

  return (
    <main className="container">
      <header className="header-bar">
        <a href="/" className="logo-wrap">
          <div className="logo-icon">S</div>
          <span className="logo-text">SachCart</span>
        </a>
        <span style={{ fontSize: "13px", color: "var(--text-muted)", fontWeight: 500 }}>
          Autonomous Checkout-Truth Agent
        </span>
      </header>

      <section style={{ textAlign: "center", maxWidth: "760px", margin: "40px auto 32px" }}>
        <h1 style={{ fontSize: "36px", fontWeight: 800, color: "var(--headings)", letterSpacing: "-0.8px", marginBottom: "16px" }}>
          Never pay sneak fees or fall for dark patterns again.
        </h1>
        <p style={{ fontSize: "16px", color: "var(--text-muted)", lineHeight: 1.6 }}>
          Paste any product URL from Amazon India, Flipkart, Myntra, or any D2C Shopify store. SachCart walks the checkout as a guest, audits against India’s CCPA 2023 dark pattern guidelines, and compares cross-retailer prices.
        </p>
      </section>

      <Tilt className="card" style={{ maxWidth: "700px", margin: "0 auto", padding: "32px" }}>
        <form onSubmit={handleSubmit}>
          <label
            htmlFor="product-url"
            style={{ display: "block", fontSize: "14px", fontWeight: 600, color: "var(--headings)", marginBottom: "8px" }}
          >
            Product URL to Audit
          </label>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <input
              id="product-url"
              type="text"
              placeholder="https://www.amazon.in/dp/... or https://store.com/products/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
              style={{
                flex: 1,
                minWidth: "260px",
                padding: "12px 16px",
                borderRadius: "8px",
                border: error ? "1px solid var(--warning-high)" : "1px solid var(--border)",
                fontSize: "15px",
                color: "var(--text-main)",
                backgroundColor: "#FAFBFB",
              }}
            />
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: "12px 24px",
                backgroundColor: "var(--primary)",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "8px",
                fontWeight: 600,
                fontSize: "15px",
                cursor: loading ? "not-allowed" : "pointer",
                boxShadow: "0 2px 6px rgba(31, 122, 109, 0.25)",
              }}
            >
              {loading ? "Launching Agent..." : "Audit Truth"}
            </button>
          </div>

          <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              id="watch-toggle"
              type="checkbox"
              checked={watch}
              onChange={(e) => setWatch(e.target.checked)}
              disabled={loading}
              style={{ width: "16px", height: "16px", accentColor: "var(--primary)" }}
            />
            <label htmlFor="watch-toggle" style={{ fontSize: "13px", color: "var(--text-muted)", cursor: "pointer" }}>
              Enable weekly re-audit to track deceptive price claims over time
            </label>
          </div>

          {error && (
            <div
              style={{
                marginTop: "16px",
                padding: "10px 14px",
                borderRadius: "8px",
                background: "var(--warning-high-bg)",
                color: "var(--warning-high)",
                fontSize: "13px",
                fontWeight: 500,
              }}
            >
              {error}
            </div>
          )}
        </form>
      </Tilt>

      {recentAudits.length > 0 && (
        <section style={{ maxWidth: "700px", margin: "48px auto 0" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--headings)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
            Recent Audits
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {recentAudits.map((item) => (
              <div
                key={item.id}
                onClick={() => router.push(`/audit/${item.id}`)}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 16px",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "border-color 0.2s",
                }}
              >
                <div>
                  <span style={{ fontWeight: 600, fontSize: "14px", color: "var(--headings)", display: "block" }}>
                    {item.domain}
                  </span>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{item.url.slice(0, 50)}...</span>
                </div>
                <span style={{ fontSize: "12px", color: "var(--primary)", fontWeight: 600 }}>View Report →</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
