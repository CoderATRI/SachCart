import re
from typing import Optional
from app.schemas import (
    ListingFacts,
    AgentWalkResult,
    FindingSchema,
    CompetitorPriceSchema,
    ClassifiedFinding,
)
from app.claude import classify_ambiguous_items

def extract_badge_percentage(badge_text: Optional[str]) -> Optional[int]:
    if not badge_text:
        return None
    match = re.search(r"(\d{1,2})\s*%", badge_text)
    if match:
        return int(match.group(1))
    return None

def calculate_median(prices: list[float]) -> Optional[float]:
    valid = sorted([p for p in prices if p > 0])
    if not valid:
        return None
    n = len(valid)
    mid = n // 2
    if n % 2 != 0:
        return valid[mid]
    return (valid[mid - 1] + valid[mid]) / 2.0

async def analyze_audit(
    audit_id: str,
    listing: ListingFacts,
    agent_result: AgentWalkResult,
    competitors: list[CompetitorPriceSchema],
) -> tuple[int, list[FindingSchema]]:
    findings: list[FindingSchema] = []

    if listing.mrp and listing.sale_price and listing.mrp > listing.sale_price > 0:
        real_pct = round(((listing.mrp - listing.sale_price) / listing.mrp) * 100)
        badge_pct = extract_badge_percentage(listing.discount_badge_text)
        if badge_pct is not None and abs(real_pct - badge_pct) > 2:
            findings.append(
                FindingSchema(
                    category="price_claim",
                    severity="high" if abs(real_pct - badge_pct) >= 10 else "medium",
                    title="Misleading Discount Percentage",
                    detail=f"Claimed discount of {badge_pct}% differs from actual calculated discount of {real_pct}%.",
                    quote=listing.discount_badge_text,
                )
            )

    comp_prices = [c.price for c in competitors if c.price > 0]
    median_comp = calculate_median(comp_prices)
    if listing.sale_price and median_comp and listing.sale_price > (1.1 * median_comp):
        diff = round(listing.sale_price - median_comp, 2)
        pct_diff = round(((listing.sale_price / median_comp) - 1.0) * 100)
        findings.append(
            FindingSchema(
                category="price_claim",
                severity="high",
                title="Inflated Listing Price vs Market",
                detail=f"Listing price is {pct_diff}% higher than competitor median of {round(median_comp, 2)}.",
                amount=diff,
            )
        )

    for charge in agent_result.charge_lines:
        if charge.amount > 0 and charge.shown_at_stage.lower() != "listing":
            if agent_result.reached_stage != "checkout" and charge.shown_at_stage.lower() == "checkout":
                continue
            findings.append(
                FindingSchema(
                    category="drip_pricing",
                    severity="high",
                    title=f"Drip Pricing Fee: {charge.label}",
                    detail=f"Undisclosed charge of {charge.amount} introduced at {charge.shown_at_stage} stage.",
                    amount=charge.amount,
                )
            )

    for addon in agent_result.preselected_addons:
        findings.append(
            FindingSchema(
                category="basket_sneaking",
                severity="high",
                title=f"Basket Sneaking: {addon.label}",
                detail=f"Pre-selected add-on automatically added to cart for {addon.amount}.",
                amount=addon.amount,
            )
        )

    for optin in agent_result.subscription_optins:
        findings.append(
            FindingSchema(
                category="subscription_trap",
                severity="high",
                title="Subscription Trap / Recurring Charge",
                detail="Recurring subscription or auto-renew pre-enabled during checkout.",
                quote=optin[:255],
            )
        )

    ambiguous_items = []
    for timer in agent_result.timers:
        ambiguous_items.append({"type": "timer", "text": timer})
    for urgency in agent_result.urgency_messages:
        ambiguous_items.append({"type": "urgency", "text": urgency})
    for text_val in listing.urgency_texts:
        ambiguous_items.append({"type": "urgency_text", "text": text_val})
    for text_val in listing.stock_texts:
        ambiguous_items.append({"type": "stock_scarcity", "text": text_val})

    if ambiguous_items:
        classified = await classify_ambiguous_items(ambiguous_items, audit_id)
        for cf in classified:
            findings.append(
                FindingSchema(
                    category=cf.category,
                    severity=cf.severity,
                    title=cf.title,
                    detail=cf.detail,
                    quote=cf.quote,
                )
            )

    if agent_result.reached_stage != "checkout":
        findings = [f for f in findings if not ("checkout" in f.title.lower() or "checkout" in f.detail.lower())]

    penalty_map = {"high": 20, "medium": 10, "low": 4}
    total_penalty = sum(penalty_map.get(f.severity.lower(), 4) for f in findings)
    score = max(0, min(100, 100 - total_penalty))

    return score, findings
