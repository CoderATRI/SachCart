"use client";

import React from "react";

interface StageCardsProps {
  stage?: string | null;
  progressMessage?: string | null;
}

export default function StageCards({ stage, progressMessage }: StageCardsProps) {
  const current = (stage || "listing").toLowerCase();

  const getStageStatus = (name: string) => {
    const order = ["listing", "cart", "checkout"];
    const targetIdx = order.indexOf(name);
    let activeIdx = order.indexOf(current);
    if (current === "blocked_by_login" || current === "failed") {
      activeIdx = 1;
    }
    if (activeIdx > targetIdx) return "completed";
    if (activeIdx === targetIdx) return "active";
    return "pending";
  };

  const stages = [
    { id: "listing", title: "1. Listing Stage", desc: "Extracting upfront price and badges" },
    { id: "cart", title: "2. Cart Stage", desc: "Checking pre-selected add-ons and stealth charges" },
    { id: "checkout", title: "3. Guest Checkout", desc: "Revealing drip pricing and subscription opt-ins" },
  ];

  return (
    <div style={{ margin: "24px 0" }}>
      <div className="stage-deck">
        {stages.map((s) => {
          const status = getStageStatus(s.id);
          const isActive = status === "active";
          const isDone = status === "completed";
          return (
            <div
              key={s.id}
              className={`stage-card ${isActive ? "active" : ""} ${isDone ? "completed" : ""}`}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontWeight: 600, fontSize: "15px", color: isActive ? "var(--primary)" : "var(--headings)" }}>
                  {s.title}
                </span>
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "2px 8px",
                    borderRadius: "9999px",
                    background: isDone ? "var(--primary-light)" : isActive ? "var(--primary)" : "#EBEFEF",
                    color: isDone ? "var(--primary)" : isActive ? "#FFF" : "var(--text-muted)",
                  }}
                >
                  {isDone ? "PASS" : isActive ? "IN PROGRESS" : "WAITING"}
                </span>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: 0 }}>{s.desc}</p>
            </div>
          );
        })}
      </div>
      {progressMessage && (
        <div
          style={{
            marginTop: "12px",
            padding: "10px 16px",
            background: "#FFFFFF",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            fontSize: "13px",
            color: "var(--text-muted)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: "var(--primary)" }} />
          <span>{progressMessage}</span>
        </div>
      )}
    </div>
  );
}
