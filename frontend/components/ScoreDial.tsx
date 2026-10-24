"use client";

import React, { useEffect, useState } from "react";

interface ScoreDialProps {
  score: number;
  size?: number;
}

export default function ScoreDial({ score, size = 180 }: ScoreDialProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    let start = 0;
    const duration = 1000;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(easeOut * score));
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [score]);

  const getColor = (s: number) => {
    if (s >= 80) return "#1F7A6D";
    if (s >= 50) return "#F2B134";
    return "#D9480F";
  };

  const dialColor = getColor(score);
  const degrees = (animatedScore / 100) * 360;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
    >
      <div
        style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: "50%",
          background: `conic-gradient(${dialColor} ${degrees}deg, #E6EFEB ${degrees}deg 360deg)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 8px 24px rgba(18, 32, 31, 0.08), inset 0 2px 6px rgba(0, 0, 0, 0.04)",
          position: "relative",
          transition: "box-shadow 0.3s ease",
        }}
      >
        <div
          style={{
            width: `${size - 32}px`,
            height: `${size - 32}px`,
            borderRadius: "50%",
            background: "#FFFFFF",
            boxShadow: "inset 0 1px 3px rgba(18, 32, 31, 0.08)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ fontSize: "38px", fontWeight: 800, color: dialColor, lineHeight: 1 }}>
            {animatedScore}
          </span>
          <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600, marginTop: "4px" }}>
            OUT OF 100
          </span>
        </div>
      </div>
      <div style={{ marginTop: "12px", textAlign: "center" }}>
        <h4 style={{ fontSize: "16px", color: "var(--headings)", fontWeight: 700 }}>
          {score >= 80 ? "Clean Checkout" : score >= 50 ? "Caution Advised" : "High Risk Checkout"}
        </h4>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>Deal Integrity Score</p>
      </div>
    </div>
  );
}
