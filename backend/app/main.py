import json
import uuid
from urllib.parse import urlparse
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.db import init_db, get_db, engine, Audit, Finding, CompetitorPrice, Evidence
from app.schemas import (
    AuditCreateRequest,
    AuditCreateResponse,
    AuditReportResponse,
    FindingSchema,
    CompetitorPriceSchema,
    EvidenceSchema,
)
from app.security import (
    validate_target_url,
    check_rate_limits,
    increment_running,
    redis_client,
)
import boto3
from botocore.client import Config
from app.storage import generate_presigned_url
from app.telemetry import setup_telemetry

app = FastAPI(title="SachCart API", docs_url="/docs", redoc_url="/redoc")
setup_telemetry(app)

@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception:
        pass

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    if "text/event-stream" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "no-cache, no-transform"
        response.headers["Connection"] = "keep-alive"
        response.headers["X-Accel-Buffering"] = "no"
    else:
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/")
def root():
    return {
        "service": "SachCart API",
        "status": "online",
        "health": "/api/health",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "health": "GET /api/health",
            "create_audit": "POST /api/audits",
            "get_audit": "GET /api/audits/{id}",
            "audit_events": "GET /api/audits/{id}/events",
            "toggle_watch": "POST /api/audits/{id}/watch",
            "evidence": "GET /evidence/{audit_id}/{uuid}",
        },
    }

@app.get("/api/health")
def health(response: Response):
    statuses = {
        "postgres": "down",
        "redis": "down",
        "minio": "down",
        "worker": "down",
    }
    try:
        import socket
        with socket.create_connection(("127.0.0.1", 5432), timeout=2):
            pass
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        statuses["postgres"] = "up"
    except Exception:
        statuses["postgres"] = "down"

    try:
        import socket
        with socket.create_connection(("127.0.0.1", 6379), timeout=2):
            pass
        if redis_client.ping():
            statuses["redis"] = "up"
            hb = redis_client.get("worker:heartbeat")
            statuses["worker"] = "up" if hb else "down"
    except Exception:
        statuses["redis"] = "down"
        statuses["worker"] = "down"

    try:
        import socket
        with socket.create_connection(("127.0.0.1", 9000), timeout=2):
            pass
        endpoint = settings.MINIO_PUBLIC_URL if settings.MINIO_PUBLIC_URL.startswith("http") else f"http://{settings.MINIO_ENDPOINT}"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4", connect_timeout=2, read_timeout=2),
            region_name="us-east-1",
        )
        s3.list_buckets()
        statuses["minio"] = "up"
    except Exception:
        statuses["minio"] = "down"

    if statuses["postgres"] != "up" or statuses["redis"] != "up" or statuses["minio"] != "up":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        response.status_code = status.HTTP_200_OK

    return statuses

@app.post("/api/audits", status_code=status.HTTP_202_ACCEPTED, response_model=AuditCreateResponse)
def create_audit(
    payload: AuditCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    validated_url = validate_target_url(payload.url)
    client_ip = check_rate_limits(request)

    domain = urlparse(validated_url).netloc.lower()
    audit_id = uuid.uuid4()
    audit = Audit(
        id=audit_id,
        url=validated_url,
        domain=domain,
        status="queued",
        watch=payload.watch,
    )
    db.add(audit)
    db.commit()

    increment_running(client_ip)
    redis_client.lpush(
        "audit_queue",
        json.dumps({"audit_id": str(audit_id), "client_ip": client_ip}),
    )

    return AuditCreateResponse(id=str(audit_id))

@app.get("/api/audits/{audit_id}", response_model=AuditReportResponse)
def get_audit(audit_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = db.query(Audit).filter(Audit.id == uid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    score_change = None
    if audit.parent_id and audit.score is not None:
        parent = db.query(Audit).filter(Audit.id == audit.parent_id).first()
        if parent and parent.score is not None:
            score_change = audit.score - parent.score

    findings_list = [
        FindingSchema(
            id=str(f.id),
            category=f.category,
            severity=f.severity,
            title=f.title,
            detail=f.detail,
            amount=float(f.amount) if f.amount is not None else None,
            quote=f.quote,
        )
        for f in audit.findings
    ]

    competitors_list = [
        CompetitorPriceSchema(
            id=str(c.id),
            domain=c.domain,
            url=c.url,
            price=float(c.price),
        )
        for c in audit.competitor_prices
    ]

    evidence_list = [
        EvidenceSchema(
            id=str(e.id),
            kind=e.kind,
            object_key=e.object_key,
        )
        for e in audit.evidence
    ]

    return AuditReportResponse(
        id=str(audit.id),
        parent_id=str(audit.parent_id) if audit.parent_id else None,
        url=audit.url,
        domain=audit.domain,
        status=audit.status,
        reached_stage=audit.reached_stage,
        score=audit.score,
        score_change=score_change,
        tinyfish_run_id=audit.tinyfish_run_id,
        listing=audit.listing,
        agent_result=audit.agent_result,
        watch=audit.watch,
        created_at=audit.created_at,
        finished_at=audit.finished_at,
        failure_reason=audit.failure_reason,
        findings=findings_list,
        competitor_prices=competitors_list,
        evidence=evidence_list,
    )

@app.get("/api/audits/{audit_id}/events")
async def get_audit_events(audit_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = db.query(Audit).filter(Audit.id == uid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    async def event_generator():
        if audit.status in ("done", "failed"):
            final_data = {
                "type": "AUDIT_FINISHED",
                "status": audit.status,
                "score": audit.score,
                "reached_stage": audit.reached_stage,
                "failure_reason": audit.failure_reason,
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            return

        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"audit:{audit_id}")

        loop = asyncio.get_running_loop()
        try:
            while True:
                msg = await loop.run_in_executor(None, pubsub.get_message, True, 1.0)
                if msg and msg.get("type") == "message":
                    raw = msg.get("data")
                    yield f"data: {raw}\n\n"
                    try:
                        parsed = json.loads(raw)
                        if parsed.get("type") == "AUDIT_FINISHED":
                            break
                    except Exception:
                        pass
                await asyncio.sleep(0.5)
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/api/audits/{audit_id}/evidence/{evidence_id}")
def get_evidence(audit_id: str, evidence_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid.UUID(audit_id)
        eid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ID")

    evidence = (
        db.query(Evidence)
        .filter(Evidence.id == eid, Evidence.audit_id == uid)
        .first()
    )
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    presigned_url = generate_presigned_url(evidence.object_key, 600)
    return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.post("/api/audits/{audit_id}/watch")
def toggle_watch(audit_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = db.query(Audit).filter(Audit.id == uid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit.watch = not audit.watch
    db.commit()
    return {"id": str(audit.id), "watch": audit.watch}
