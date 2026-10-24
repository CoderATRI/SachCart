import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Numeric,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=True)
    url = Column(String(2048), nullable=False)
    domain = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="queued")
    reached_stage = Column(String(64), nullable=True)
    score = Column(Integer, nullable=True)
    tinyfish_run_id = Column(String(128), nullable=True)
    listing = Column(JSONB, nullable=True)
    agent_result = Column(JSONB, nullable=True)
    watch = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    findings = relationship("Finding", back_populates="audit", cascade="all, delete-orphan")
    competitor_prices = relationship("CompetitorPrice", back_populates="audit", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="audit", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False)
    title = Column(String(255), nullable=False)
    detail = Column(String(1024), nullable=False)
    amount = Column(Numeric(12, 2), nullable=True)
    quote = Column(String(1024), nullable=True)

    audit = relationship("Audit", back_populates="findings")

class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    domain = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)

    audit = relationship("Audit", back_populates="competitor_prices")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(32), nullable=False)
    object_key = Column(String(512), nullable=False)

    audit = relationship("Audit", back_populates="evidence")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
