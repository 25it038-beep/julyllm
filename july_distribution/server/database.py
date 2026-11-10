"""
HS AI SOLUTIONS — JULY MULTI-COMPUTER DISTRIBUTION PLATFORM
Layer: CENTRAL CONTROL SERVER DATABASE (july_distribution.server.database)
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM 3B | Family: HS AI FAMILY

Production Database Architecture:
- Dialect Agnostic: Supports Persistent PostgreSQL (Render / Cloud) & Local SQLite.
- Connection pooling with health verification (pool_pre_ping=True).
- Manages User Accounts, Bearer Tokens, Device Access Control, Model Versions,
  Security Audit Logs, and Client Hardware Telemetry.
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Text, BigInteger,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(32), default="standard")
    model_access_granted = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    daily_download_quota = Column(Integer, default=5)
    downloads_today = Column(Integer, default=0)
    last_download_date = Column(String(32), default="")
    created_at = Column(Float, nullable=False)


class Token(Base):
    __tablename__ = "tokens"
    token = Column(String(128), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(Float, nullable=False)
    expires_at = Column(Float, nullable=False)
    is_revoked = Column(Boolean, default=False)


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(128), nullable=False, index=True)
    device_name = Column(String(128), nullable=False)
    os_version = Column(String(128), default="Windows")
    status = Column(String(32), default="APPROVED")  # APPROVED, REVOKED, PENDING
    registered_at = Column(Float, nullable=False)
    last_seen_at = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_user_device"),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"
    version_tag = Column(String(32), primary_key=True)
    model_name = Column(String(128), nullable=False)
    bucket_name = Column(String(64), nullable=False)
    object_key = Column(String(128), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False)
    release_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(Float, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(64), nullable=True)
    device_id = Column(String(128), nullable=True)
    event_type = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    timestamp = Column(Float, nullable=False)


class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(64), nullable=True)
    device_name = Column(String(128), nullable=True)
    hardware_mode = Column(String(32), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    tokens_per_second = Column(Float, default=0.0)
    ram_used_gb = Column(Float, default=0.0)
    vram_used_mb = Column(Float, default=0.0)
    timestamp = Column(Float, nullable=False)


# ---------------------------------------------------------------------------
# Database Connection Factory
# ---------------------------------------------------------------------------

DB_DIR = Path(__file__).resolve().parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE_PATH = DB_DIR / "distribution.db"


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        # Render provides postgres:// which must be normalized to postgresql:// for SQLAlchemy
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    return f"sqlite:///{DEFAULT_SQLITE_PATH}"


DATABASE_URL = get_database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL configuration with connection pooling for Render
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initializes tables and seeds the active model version."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if model version exists
        existing_model = db.query(ModelVersion).filter(ModelVersion.version_tag == "v1.1.0").first()
        if not existing_model:
            model_record = ModelVersion(
                version_tag="v1.1.0",
                model_name="July LLM 3B (HS AI Solutions)",
                bucket_name="july",
                object_key="july-final.gguf",
                size_bytes=2019377888,
                sha256="f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4",
                release_notes="Official production release of July LLM 3B. High-speed GQA, SwiGLU, and robust reasoning.",
                is_active=True,
                created_at=time.time()
            )
            db.add(model_record)
            db.commit()

        # Seed Gravity LLM
        existing_gravity = db.query(ModelVersion).filter(ModelVersion.version_tag == "gravity-v1.0.0").first()
        if not existing_gravity:
            gravity_record = ModelVersion(
                version_tag="gravity-v1.0.0",
                model_name="Gravity LLM (HS AI Solutions)",
                bucket_name="july",
                object_key="Gravity-HS-AI-Solutions.gguf",
                size_bytes=5629108096,
                sha256="4b6c93439e6df7db0b5da22bb133e9b119a018bc6bfcefd482f3c7ae46beee05",
                release_notes="Official release of Gravity LLM from private Cloudflare R2 bucket. Frontier specialist for mathematics, CAS, and algorithmic proofs.",
                is_active=True,
                created_at=time.time()
            )
            db.add(gravity_record)
            db.commit()
    finally:
        db.close()


# Ensure tables exist
init_database()
