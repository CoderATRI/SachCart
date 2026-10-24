from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, HttpUrl, Field

CCPA_CATEGORIES = (
    "false_urgency",
    "basket_sneaking",
    "confirm_shaming",
    "forced_action",
    "subscription_trap",
    "interface_interference",
    "bait_and_switch",
    "drip_pricing",
    "disguised_advertisement",
    "nagging",
    "trick_question",
    "saas_billing",
    "rogue_malwares",
    "price_claim",
)

FindingCategory = Literal[
    "false_urgency",
    "basket_sneaking",
    "confirm_shaming",
    "forced_action",
    "subscription_trap",
    "interface_interference",
    "bait_and_switch",
    "drip_pricing",
    "disguised_advertisement",
    "nagging",
    "trick_question",
    "saas_billing",
    "rogue_malwares",
    "price_claim",
]

class AuditCreateRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    watch: bool = False

class AuditCreateResponse(BaseModel):
    id: str

class ListingFacts(BaseModel):
    title: Optional[str] = None
    sale_price: Optional[float] = None
    mrp: Optional[float] = None
    currency: Optional[str] = None
    discount_badge_text: Optional[str] = None
    urgency_texts: list[str] = Field(default_factory=list)
    stock_texts: list[str] = Field(default_factory=list)
    preselected_options: list[str] = Field(default_factory=list)

class ChargeLine(BaseModel):
    label: str
    amount: float
    shown_at_stage: str

class PreselectedAddon(BaseModel):
    label: str
    amount: float

class AgentWalkResult(BaseModel):
    reached_stage: Literal["listing", "cart", "checkout", "blocked_by_login", "failed"] = "failed"
    charge_lines: list[ChargeLine] = Field(default_factory=list)
    preselected_addons: list[PreselectedAddon] = Field(default_factory=list)
    timers: list[str] = Field(default_factory=list)
    urgency_messages: list[str] = Field(default_factory=list)
    subscription_optins: list[str] = Field(default_factory=list)
    total: Optional[float] = None

class ClassifiedFinding(BaseModel):
    category: str
    severity: Literal["low", "medium", "high"]
    title: str
    detail: str
    quote: Optional[str] = None

class ClassifiedFindingsResponse(BaseModel):
    findings: list[ClassifiedFinding] = Field(default_factory=list)

class FindingSchema(BaseModel):
    id: Optional[str] = None
    category: str
    severity: str
    title: str
    detail: str
    amount: Optional[float] = None
    quote: Optional[str] = None

class CompetitorPriceSchema(BaseModel):
    id: Optional[str] = None
    domain: str
    url: str
    price: float

class EvidenceSchema(BaseModel):
    id: str
    kind: str
    object_key: str
    url: Optional[str] = None

class AuditReportResponse(BaseModel):
    id: str
    parent_id: Optional[str] = None
    url: str
    domain: str
    status: str
    reached_stage: Optional[str] = None
    score: Optional[int] = None
    score_change: Optional[int] = None
    tinyfish_run_id: Optional[str] = None
    streaming_url: Optional[str] = None
    listing: Optional[dict] = None
    agent_result: Optional[dict] = None
    watch: bool = False
    created_at: datetime
    finished_at: Optional[datetime] = None
    findings: list[FindingSchema] = Field(default_factory=list)
    competitor_prices: list[CompetitorPriceSchema] = Field(default_factory=list)
    evidence: list[EvidenceSchema] = Field(default_factory=list)
