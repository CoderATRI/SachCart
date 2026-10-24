"use client";

import React from "react";
import { Finding } from "@/lib/api";

interface FindingCardProps {
  finding: Finding;
}

export default function FindingCard({ finding }: FindingCardProps) {
  const sev = finding.severity.toLowerCase();
  const badgeClass =
    sev === "high" ? "badge-high" : sev === "medium" ? "badge-medium" : "badge-low";

  return (
    <div className="flip-card" tabIndex={0} role="article" aria-label={finding.title}>
      <div className="flip-card-inner">
        <div className="flip-front">
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span className={`badge ${badgeClass}`}>{finding.severity} severity</span>
              {finding.amount !== undefined && finding.amount !== null && (
                <span style={{ fontWeight: 700, color: "var(--warning-high)", fontSize: "14px" }}>
                  +{finding.amount}
                </span>
              )}
            </div>
            <h4 style={{ fontSize: "16px", fontWeight: 700, color: "var(--headings)", marginTop: "8px" }}>
              {finding.title}
            </h4>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", color: "var(--text-muted)" }}>
            <span>Category: {finding.category.replace(/_/g, " ")}</span>
            <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--primary)" }}>Hover or Focus to flip ↺</span>
          </div>
        </div>

        <div className="flip-back">
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--primary)" }}>
                CCPA Rule: {finding.category.replace(/_/g, " ")}
              </span>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-main)", margin: "8px 0" }}>
              {finding.detail}
            </p>
            {finding.quote && (
              <blockquote
                style={{
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  fontStyle: "italic",
                  borderLeft: "2px solid var(--primary)",
                  paddingLeft: "8px",
                  marginTop: "6px",
                }}
              >
                &ldquo;{finding.quote}&rdquo;
              </blockquote>
            )}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            Penalty: {sev === "high" ? "-20 pts" : sev === "medium" ? "-10 pts" : "-4 pts"}
          </div>
        </div>
      </div>
    </div>
  );
}
