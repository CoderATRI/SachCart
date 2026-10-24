import sys
import json
import asyncio

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse
import redis
from sqlalchemy.orm import Session
from app.config import settings
from app.db import SessionLocal, Audit, Finding, CompetitorPrice, Evidence, init_db
from app.schemas import (
    ListingFacts,
    AgentWalkResult,
    CompetitorPriceSchema,
    ChargeLine,
    PreselectedAddon,
)
from app.tinyfish import (
    fetch_page_text,
    fetch_multiple_pages,
    search_competitors,
    stream_agent_walk,
)
from app.claude import extract_listing_facts, extract_competitor_price
from app.analyzer import analyze_audit
from app.storage import store_evidence_from_url
from app.security import decrement_running

if not settings.TINYFISH_API_KEY.strip() or not settings.ANTHROPIC_API_KEY.strip():
    sys.exit("Worker startup halted: TINYFISH_API_KEY and ANTHROPIC_API_KEY must both be set in .env")

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
semaphore = asyncio.Semaphore(settings.MAX_PARALLEL_AUDITS)

async def run_read_step(url: str, audit_id: str) -> tuple[ListingFacts, str]:
    page_text = await fetch_page_text(url, audit_id)
    listing = await extract_listing_facts(page_text, audit_id)
    return listing, page_text

async def run_compare_step(title: str, target_domain: str, audit_id: str) -> list[CompetitorPriceSchema]:
    if not title:
        return []
    raw_results = await search_competitors(title, audit_id)
    competitor_urls = []
    competitor_domains = {}
    for r in raw_results:
        u = r.get("url")
        if not u:
            continue
        try:
            d = urlparse(u).netloc.lower()
            if d and d != target_domain and d not in competitor_domains:
                competitor_domains[d] = u
                competitor_urls.append(u)
        except Exception:
            continue
        if len(competitor_urls) >= 5:
            break

    if not competitor_urls:
        return []

    pages_map = await fetch_multiple_pages(competitor_urls, audit_id)
    competitors: list[CompetitorPriceSchema] = []
    for d, u in competitor_domains.items():
        text = pages_map.get(u, "")
        if text:
            price = await extract_competitor_price(text, audit_id)
            if price is not None and price > 0:
                competitors.append(CompetitorPriceSchema(domain=d, url=u, price=price))
    return competitors

async def run_walk_step(url: str, audit_id: str, retry_count: int = 0) -> tuple[AgentWalkResult, dict]:
    walk_result = AgentWalkResult()
    extra_data = {"tinyfish_run_id": None, "streaming_url": None, "evidence_urls": []}
    terminal_event = None

    try:
        async for event in stream_agent_walk(url, audit_id, capture_evidence=settings.CAPTURE_EVIDENCE):
            redis_client.publish(f"audit:{audit_id}", json.dumps(event))
            etype = event.get("type")
            if event.get("run_id"):
                extra_data["tinyfish_run_id"] = event["run_id"]
            if etype == "STREAMING_URL":
                extra_data["streaming_url"] = event.get("streaming_url")
            elif etype == "COMPLETE":
                terminal_event = event

        if terminal_event:
            status = terminal_event.get("status")
            error = terminal_event.get("error") or {}
            err_code = (error.get("code") or "").upper()
            if (status == "FAILED" or err_code in ("SITE_BLOCKED", "TIMEOUT")) and retry_count < 1:
                return await run_walk_step(url, audit_id, retry_count=retry_count + 1)

            res = terminal_event.get("result") or {}
            walk_result.reached_stage = res.get("reached_stage", "failed" if status == "FAILED" else "inconclusive")
            for cl in res.get("charge_lines", []):
                walk_result.charge_lines.append(
                    ChargeLine(
                        label=cl.get("label", "Charge"),
                        amount=float(cl.get("amount", 0)),
                        shown_at_stage=cl.get("shown_at_stage", "cart"),
                    )
                )
            for pa in res.get("preselected_addons", []):
                walk_result.preselected_addons.append(
                    PreselectedAddon(label=pa.get("label", "Addon"), amount=float(pa.get("amount", 0)))
                )
            walk_result.timers = res.get("timers", [])
            walk_result.urgency_messages = res.get("urgency_messages", [])
            walk_result.subscription_optins = res.get("subscription_optins", [])
            walk_result.total = float(res["total"]) if res.get("total") is not None else None

            if settings.CAPTURE_EVIDENCE:
                video_url = terminal_event.get("video_url")
                if video_url:
                    extra_data["evidence_urls"].append(("video", video_url))
                for step in terminal_event.get("steps", []):
                    ss = step.get("screenshot_url")
                    if ss:
                        extra_data["evidence_urls"].append(("screenshot", ss))
    except Exception as e:
        if retry_count < 1:
            return await run_walk_step(url, audit_id, retry_count=retry_count + 1)
        walk_result.reached_stage = "failed"

    return walk_result, extra_data

async def process_audit(audit_id: str, client_ip: str):
    async with semaphore:
        db: Session = SessionLocal()
        try:
            audit = db.query(Audit).filter(Audit.id == audit_id).first()
            if not audit:
                return
            audit.status = "running"
            db.commit()

            redis_client.publish(
                f"audit:{audit_id}",
                json.dumps({"type": "STATUS_CHANGE", "status": "running"}),
            )

            async def read_and_compare():
                listing, page_text = await run_read_step(audit.url, audit_id)
                competitors = []
                if listing.title:
                    competitors = await run_compare_step(listing.title, audit.domain, audit_id)
                return listing, competitors

            read_task = asyncio.create_task(read_and_compare())
            walk_task = asyncio.create_task(run_walk_step(audit.url, audit_id))

            (listing, competitors), (walk_result, extra_data) = await asyncio.gather(
                read_task, walk_task
            )

            score, findings = await analyze_audit(audit_id, listing, walk_result, competitors)

            audit.status = "done"
            audit.reached_stage = walk_result.reached_stage
            audit.score = score
            audit.tinyfish_run_id = extra_data.get("tinyfish_run_id")
            audit.listing = listing.model_dump()
            audit.agent_result = walk_result.model_dump()
            audit.finished_at = datetime.utcnow()

            for c in competitors:
                db.add(
                    CompetitorPrice(
                        audit_id=audit.id,
                        domain=c.domain,
                        url=c.url,
                        price=c.price,
                    )
                )

            for f in findings:
                db.add(
                    Finding(
                        audit_id=audit.id,
                        category=f.category,
                        severity=f.severity,
                        title=f.title,
                        detail=f.detail,
                        amount=f.amount,
                        quote=f.quote,
                    )
                )

            for kind, ev_url in extra_data.get("evidence_urls", []):
                try:
                    obj_key = f"evidence/{audit_id}/{uuid.uuid4()}"
                    await store_evidence_from_url(ev_url, obj_key)
                    db.add(Evidence(audit_id=audit.id, kind=kind, object_key=obj_key))
                except Exception:
                    pass

            db.commit()

            redis_client.publish(
                f"audit:{audit_id}",
                json.dumps(
                    {
                        "type": "AUDIT_FINISHED",
                        "status": "done",
                        "score": score,
                        "reached_stage": walk_result.reached_stage,
                    }
                ),
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            audit = db.query(Audit).filter(Audit.id == audit_id).first()
            if audit:
                audit.status = "failed"
                audit.finished_at = datetime.utcnow()
                db.commit()
            redis_client.publish(
                f"audit:{audit_id}",
                json.dumps({"type": "AUDIT_FINISHED", "status": "failed", "error": str(e)}),
            )
        finally:
            decrement_running(client_ip)
            db.close()

async def hourly_watch_scheduler():
    while True:
        await asyncio.sleep(3600)
        db: Session = SessionLocal()
        try:
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            watched_audits = db.query(Audit).filter(Audit.watch == True).all()
            for parent in watched_audits:
                recent_child = (
                    db.query(Audit)
                    .filter(Audit.parent_id == parent.id, Audit.created_at >= seven_days_ago)
                    .first()
                )
                if not recent_child:
                    child_id = uuid.uuid4()
                    new_audit = Audit(
                        id=child_id,
                        parent_id=parent.id,
                        url=parent.url,
                        domain=parent.domain,
                        status="queued",
                        watch=True,
                    )
                    db.add(new_audit)
                    db.commit()
                    redis_client.lpush(
                        "audit_queue",
                        json.dumps({"audit_id": str(child_id), "client_ip": "127.0.0.1"}),
                    )
        except Exception:
            pass
        finally:
            db.close()

async def main():
    init_db()
    asyncio.create_task(hourly_watch_scheduler())
    while True:
        loop = asyncio.get_running_loop()
        item = await loop.run_in_executor(None, redis_client.brpop, "audit_queue", 2)
        if item:
            _, raw_payload = item
            data = json.loads(raw_payload)
            audit_id = data.get("audit_id")
            client_ip = data.get("client_ip", "127.0.0.1")
            if audit_id:
                asyncio.create_task(process_audit(audit_id, client_ip))

if __name__ == "__main__":
    asyncio.run(main())
