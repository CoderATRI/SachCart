"use client";

import React, { useEffect, useState } from "react";
import { getHealth, HealthStatus } from "@/lib/api";

export default function HealthBanner() {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function check() {
      const res = await getHealth();
      if (!mounted) return;
      if (!res.ok) {
        if (res.status && res.status.postgres === "down") {
          setErrorMsg("Postgres is down: Backend not reachable");
        } else if (res.status && res.status.redis === "down") {
          setErrorMsg("Redis is down: Backend not reachable");
        } else if (res.status && res.status.minio === "down") {
          setErrorMsg("MinIO is down: Backend not reachable");
        } else {
          setErrorMsg("Backend not reachable");
        }
      } else if (res.status && res.status.worker === "down") {
        setErrorMsg("Worker is not running: run start.ps1");
      } else {
        setErrorMsg(null);
      }
    }

    check();
    const interval = setInterval(check, 4000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (!errorMsg) return null;

  const isWorkerOnly = errorMsg.includes("Worker");

  return (
    <div
      role="alert"
      style={{
        width: "100%",
        padding: "10px 16px",
        backgroundColor: isWorkerOnly ? "#FFFBEB" : "#FEF2F2",
        color: isWorkerOnly ? "#92400E" : "#991B1B",
        borderBottom: `1px solid ${isWorkerOnly ? "#FDE68A" : "#FCA5A5"}`,
        fontSize: "13px",
        fontWeight: 600,
        textAlign: "center",
        position: "sticky",
        top: 0,
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px",
      }}
    >
      <span>⚠️</span>
      <span>{errorMsg}</span>
    </div>
  );
}
