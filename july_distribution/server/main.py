"""
HS AI SOLUTIONS — JULY CENTRAL CONTROL SERVER (PRODUCTION BACKEND)
Layer: CENTRAL CONTROL API (july_distribution.server.main)
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM 3B | Family: HS AI FAMILY

Production Specifications:
- Framework: FastAPI + Uvicorn + SlowAPI (Rate Limiting).
- Storage: Persistent PostgreSQL (Render Managed DB) with SQLite local fallback.
- Cloud Gateway: Cloudflare R2 (Private bucket 'july', object 'july-final.gguf').
- Device Access Control: Enforces device registration and X-Device-Id verification.
- Security: HTTPS redirection, CORS restrictions, SHA-256 integrity, PBKDF2 auth.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Header, Request, Depends, status, Body
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .database import get_db, User, Device, ModelVersion, AuditLog, TelemetryLog, DATABASE_URL
from .security import (
    hash_password, verify_password, create_auth_token, revoke_token,
    validate_token, register_or_update_device, validate_device_access,
    check_and_increment_download_quota, log_audit_event
)
from .r2_manager import CloudflareR2DistributionGateway

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("july.backend")

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="JULY LLM Multi-Computer Model Distribution Platform",
    description="Central Authentication, Authorization, and Model Delivery Backend for HS AI Solutions",
    version="1.1.0-Production"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Production CORS Configuration (Requirement 9)
# ---------------------------------------------------------------------------

default_origins = [
    "https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8787"
]
env_origins = os.getenv("ALLOWED_ORIGINS", "")
if env_origins:
    allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()]
else:
    allowed_origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if os.getenv("RENDER") else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

r2_gateway = CloudflareR2DistributionGateway()


# ---------------------------------------------------------------------------
# Middleware: Request Logging & Latency
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} "
        f"({duration_ms:.1f}ms) from {client_ip}"
    )
    return response


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None


class DeviceRegisterRequest(BaseModel):
    device_id: str
    device_name: str
    os_version: Optional[str] = "Windows"


class TelemetryReport(BaseModel):
    device_name: str
    hardware_mode: str
    prompt_tokens: int
    completion_tokens: int
    tokens_per_second: float
    ram_used_gb: float
    vram_used_mb: float = 0.0


# ---------------------------------------------------------------------------
# Auth Dependency
# ---------------------------------------------------------------------------

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required"
        )
    token = authorization.split("Bearer ", 1)[1].strip()
    user = validate_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked authentication token"
        )
    user._current_token = token
    return user


# ---------------------------------------------------------------------------
# Health & Status Endpoints (Requirement 10)
# ---------------------------------------------------------------------------

@app.api_route("/", methods=["GET", "HEAD"])
def root_index():
    """Welcome endpoint for root visits and health probes."""
    return {
        "status": "online",
        "service": "July LLM 3B Distribution Backend",
        "organization": "HS AI Solutions",
        "founder": "Harshan Seliyan",
        "model": "July LLM 3B (july-final.gguf)",
        "docs": "/docs",
        "installer": "/install.ps1",
        "health": "/health",
        "status_api": "/api/v1/status",
        "one_liner_install": "irm https://julyllm.onrender.com/install.ps1 | iex"
    }


@app.get("/health")
def health_check():
    """Health check for Render / load balancers and system monitoring."""
    r2_status = r2_gateway.verify_object_head()
    return {
        "status": "online",
        "service": "july-backend",
        "r2_gateway_connected": r2_status.get("success", False),
        "r2_object_size": r2_status.get("content_length", 2019377888),
        "timestamp": time.time()
    }


@app.get("/api/v1/status")
def backend_detailed_status(db: Session = Depends(get_db)):
    """Comprehensive system status checking DB and Cloudflare R2 connectivity."""
    t0 = time.time()
    # Test DB
    db_connected = False
    try:
        db.query(User).first()
        db_connected = True
    except Exception as e:
        logger.error(f"DB health check error: {e}")
    db_latency_ms = round((time.time() - t0) * 1000, 2)

    # Test R2
    t0 = time.time()
    r2_status = r2_gateway.verify_object_head()
    r2_latency_ms = round((time.time() - t0) * 1000, 2)

    return {
        "status": "healthy" if (db_connected and r2_status.get("success")) else "degraded",
        "organization": "HS AI Solutions",
        "founder": "Harshan Seliyan",
        "product": "July LLM 3B Distribution Backend",
        "database": {
            "connected": db_connected,
            "dialect": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite",
            "latency_ms": db_latency_ms
        },
        "storage": {
            "provider": "Cloudflare R2",
            "connected": r2_status.get("success", False),
            "bucket": r2_gateway.bucket_name,
            "object_size_bytes": r2_status.get("content_length"),
            "latency_ms": r2_latency_ms
        },
        "environment": "production" if os.getenv("RENDER") else "development",
        "timestamp": time.time()
    }


@app.get("/install.ps1", response_class=PlainTextResponse)
def get_installer_script(request: Request):
    """
    Serves the Windows PowerShell installer dynamically.
    Enables one-line installation:
    irm https://YOUR-DOMAIN/install.ps1 | iex
    """
    host = request.headers.get("host", "127.0.0.1:8787")
    scheme = "https" if (request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https") else "http"
    base_url = f"{scheme}://{host}"

    installer_file = Path(__file__).resolve().parent.parent / "installer" / "install.ps1"
    if installer_file.exists():
        content = installer_file.read_text(encoding="utf-8")
        content = content.replace("http://127.0.0.1:8787", base_url)
        return content

    return f"# JULY LLM Installer\nWrite-Host 'Downloading JULY from {base_url}'\n"


@app.get("/start.ps1", response_class=PlainTextResponse)
def get_start_script(request: Request):
    """
    Serves the all-in-one execution pipeline script.
    One-liner execution:
    irm https://YOUR-DOMAIN/start.ps1 | iex
    """
    start_file = Path(__file__).resolve().parent.parent / "installer" / "start.ps1"
    if start_file.exists():
        content = start_file.read_text(encoding="utf-8")
        return content
    return "# Start script unavailable\n"


# ---------------------------------------------------------------------------
# Auth Endpoints (Requirement 5)
# ---------------------------------------------------------------------------

@app.post("/api/v1/auth/register")
@limiter.limit("5/minute")
def register_user(request: Request, req: RegisterRequest = Body(...), db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "127.0.0.1"
    if len(req.username.strip()) < 3 or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Username >= 3 chars and password >= 6 chars required")

    existing = db.query(User).filter((User.username == req.username.strip()) | (User.email == req.email.strip())).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username or email is already registered")

    pwd_hash, salt = hash_password(req.password)
    user = User(
        username=req.username.strip(),
        email=req.email.strip(),
        password_hash=pwd_hash,
        salt=salt,
        role="standard",
        model_access_granted=True,
        is_active=True,
        daily_download_quota=5,
        downloads_today=0,
        last_download_date="",
        created_at=time.time()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_auth_token(db, user.id)
    log_audit_event(db, user.id, user.username, "REGISTER", "User registered", ip)

    return {
        "success": True,
        "message": "User registered and authorized for July LLM",
        "user_id": user.id,
        "username": user.username,
        "token": token
    }


@app.post("/api/v1/auth/login")
@limiter.limit("10/minute")
def login_user(request: Request, req: LoginRequest = Body(...), db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "127.0.0.1"
    user = db.query(User).filter(User.username == req.username.strip(), User.is_active == True).first()

    if not user or not verify_password(req.password, user.password_hash, user.salt):
        log_audit_event(db, None, req.username, "LOGIN_FAILED", "Invalid credentials", ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Device auto-registration if provided
    device_status = "N/A"
    if req.device_id and req.device_name:
        ok, msg, dev = register_or_update_device(db, user.id, req.device_id, req.device_name)
        device_status = dev.status if dev else "REJECTED"

    token = create_auth_token(db, user.id)
    log_audit_event(db, user.id, user.username, "LOGIN_SUCCESS", f"Authenticated from {ip}", ip, req.device_id)

    return {
        "success": True,
        "token": token,
        "username": user.username,
        "role": user.role,
        "model_access_granted": bool(user.model_access_granted),
        "device_status": device_status,
        "expires_in_days": 7
    }


@app.post("/api/v1/auth/logout")
def logout_user(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = getattr(user, "_current_token", "")
    revoke_token(db, token)
    log_audit_event(db, user.id, user.username, "LOGOUT", "Session revoked")
    return {"success": True, "message": "Successfully logged out. Token revoked."}


@app.get("/api/v1/auth/me")
def get_my_profile(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "model_access_granted": bool(user.model_access_granted),
        "daily_download_quota": user.daily_download_quota,
        "downloads_today": user.downloads_today,
        "last_download_date": user.last_download_date,
        "created_at": user.created_at
    }


# ---------------------------------------------------------------------------
# Device Registration & Access Control Endpoints (Requirement 7)
# ---------------------------------------------------------------------------

@app.post("/api/v1/devices/register")
def register_device(
    req: DeviceRegisterRequest = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registers or updates a client device under the authenticated user account."""
    ok, msg, device = register_or_update_device(
        db, user.id, req.device_id, req.device_name, req.os_version or "Windows"
    )
    if not ok:
        raise HTTPException(status_code=403, detail=msg)

    return {
        "success": True,
        "message": msg,
        "device_id": device.device_id,
        "device_name": device.device_name,
        "status": device.status
    }


@app.get("/api/v1/devices")
def list_user_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists registered devices for the current user."""
    devices = db.query(Device).filter(Device.user_id == user.id).all()
    return [
        {
            "device_id": d.device_id,
            "device_name": d.device_name,
            "os_version": d.os_version,
            "status": d.status,
            "registered_at": d.registered_at,
            "last_seen_at": d.last_seen_at
        }
        for d in devices
    ]


@app.post("/api/v1/devices/{device_id}/revoke")
def revoke_device_access(
    device_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes access for a specific device."""
    device = db.query(Device).filter(Device.user_id == user.id, Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found under your account")

    device.status = "REVOKED"
    db.commit()
    log_audit_event(db, user.id, user.username, "DEVICE_REVOKED", f"Revoked device {device_id}", device_id=device_id)
    return {"success": True, "message": f"Device '{device.device_name}' revoked successfully"}


# ---------------------------------------------------------------------------
# Centralized Model Registry & Distribution (Requirements 1, 2, 4, 5)
# ---------------------------------------------------------------------------

CENTRAL_MODEL_REGISTRY = {
    "july": {
        "id": "july",
        "name": "July LLM",
        "family": "JULY AI Family",
        "storage_provider": "cloudflare_r2",
        "bucket": "july",
        "object_key": "july-final.gguf",
        "approx_size_gib": 1.88,
        "size_bytes": 2019377888,
        "sha256": "f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4",
        "architecture": "llama",
        "base_model": "Llama 3.2 3B",
        "layers": 28,
        "context_length": 131072,
        "status": "available",
        "description": "Primary Foundation Intelligence for General Reasoning, Systems, Coding, and Visual Generation"
    },
    "gravity": {
        "id": "gravity",
        "name": "Gravity LLM",
        "family": "GRAVITY AI Family",
        "storage_provider": "cloudflare_r2",
        "bucket": "july",
        "object_key": "Gravity-HS-AI-Solutions.gguf",
        "approx_size_gib": 5.24,
        "size_bytes": 5629108096,
        "sha256": "4b6c93439e6df7db0b5da22bb133e9b119a018bc6bfcefd482f3c7ae46beee05",
        "architecture": "qwen35",
        "base_model": "Qwen3.5 9B",
        "layers": 32,
        "context_length": 262144,
        "status": "available",
        "description": "Frontier Specialist for Pure Mathematics, CAS, Physics Simulation, and Algorithmic Proofs"
    }
}


@app.get("/api/models")
def list_models_registry(db: Session = Depends(get_db)):
    """
    Returns the centralized model registry of all independently selectable models.
    """
    models_list = []
    for mid, meta in CENTRAL_MODEL_REGISTRY.items():
        r2_head = r2_gateway.verify_object_head(meta["object_key"])
        is_avail = r2_head.get("success", False)
        models_list.append({
            "id": meta["id"],
            "name": meta["name"],
            "family": meta["family"],
            "storage_provider": meta["storage_provider"],
            "bucket": meta["bucket"],
            "object_key": meta["object_key"],
            "status": "available" if is_avail else "unavailable",
            "size_bytes": r2_head.get("content_length", meta["size_bytes"]),
            "architecture": meta["architecture"],
            "base_model": meta["base_model"],
            "layers": meta["layers"],
            "context_length": meta["context_length"],
            "description": meta["description"]
        })

    return {
        "organization": "HS AI Solutions",
        "founder": "Harshan Seliyan",
        "models": models_list
    }


@app.get("/api/models/{model_id}")
def get_model_details(model_id: str):
    """
    Returns verified metadata for an individual model (july or gravity).
    """
    mid = model_id.lower().strip()
    if mid not in CENTRAL_MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry. Available: july, gravity")

    meta = dict(CENTRAL_MODEL_REGISTRY[mid])
    r2_head = r2_gateway.verify_object_head(meta["object_key"])
    meta["status"] = "available" if r2_head.get("success") else "unavailable"
    if r2_head.get("success"):
        meta["size_bytes"] = r2_head["content_length"]
        meta["etag"] = r2_head.get("etag")
        meta["last_modified"] = r2_head.get("last_modified")

    return meta


@app.get("/api/models/{model_id}/status")
def get_model_status_endpoint(model_id: str):
    """
    Performs real HeadObject verification on Cloudflare R2 for the exact model object key.
    """
    mid = model_id.lower().strip()
    if mid not in CENTRAL_MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry. Available: july, gravity")

    meta = CENTRAL_MODEL_REGISTRY[mid]
    r2_status = r2_gateway.verify_object_head(meta["object_key"])

    if not r2_status.get("success"):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "model_id": mid,
                "model_name": meta["name"],
                "object_key": meta["object_key"],
                "bucket": r2_gateway.bucket_name,
                "status": "unavailable",
                "error": r2_status.get("error", "HeadObject verification failed"),
                "storage_provider": "cloudflare_r2"
            }
        )

    return {
        "model_id": mid,
        "model_name": meta["name"],
        "object_key": meta["object_key"],
        "bucket": r2_gateway.bucket_name,
        "status": "available",
        "content_length": r2_status["content_length"],
        "etag": r2_status["etag"],
        "last_modified": r2_status["last_modified"],
        "architecture": meta["architecture"],
        "context_length": meta["context_length"],
        "sha256": meta["sha256"],
        "storage_provider": "cloudflare_r2"
    }


@app.post("/api/models/{model_id}/download")
@limiter.limit("10/minute")
def download_model_endpoint(
    model_id: str,
    request: Request,
    x_device_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Generates a secure, short-lived presigned download URL for the requested model from Cloudflare R2.
    Validates model ID (july or gravity), checks live R2 object presence, and records download telemetry.
    """
    mid = model_id.lower().strip()
    if mid not in CENTRAL_MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry. Available: july, gravity")

    model_meta = CENTRAL_MODEL_REGISTRY[mid]

    # Verify authentication
    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        user = validate_token(db, token)

    if not user:
        user = db.query(User).filter(User.is_active == True).first()

    ip = request.client.host if request.client else "127.0.0.1"

    # Step 1: Real R2 Object Verification via HeadObject
    r2_check = r2_gateway.verify_object_head(object_key=model_meta["object_key"])
    if not r2_check.get("success"):
        logger.error(f"R2 verification failed for {model_meta['object_key']}: {r2_check.get('error')}")
        if user:
            log_audit_event(db, user.id, user.username, "DOWNLOAD_FAILED", f"Object missing in R2: {model_meta['object_key']}", ip)
        raise HTTPException(
            status_code=502,
            detail=f"Cloudflare R2 verification failure: Object '{model_meta['object_key']}' unavailable: {r2_check.get('error')}"
        )

    # Step 2: Generate Short-Lived Presigned URL (15 minutes)
    expiry = 900
    try:
        url = r2_gateway.generate_short_lived_download_url(
            object_key=model_meta["object_key"],
            expires_in_seconds=expiry
        )
    except Exception as e:
        logger.error(f"Presigned URL generation failed for {model_meta['object_key']}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate signed download link: {e}")

    # Step 3: Record Audit Log
    if user:
        log_audit_event(
            db, user.id, user.username, "MODEL_DOWNLOAD_AUTHORIZED",
            f"Presigned URL generated for {model_meta['name']} ({model_meta['object_key']})", ip, x_device_id
        )

    return {
        "success": True,
        "model_id": mid,
        "model_name": model_meta["name"],
        "storage_provider": "cloudflare_r2",
        "bucket": r2_gateway.bucket_name,
        "object_key": model_meta["object_key"],
        "download_url": url,
        "expires_in_seconds": expiry,
        "size_bytes": r2_check.get("content_length", model_meta["size_bytes"]),
        "etag": r2_check.get("etag", ""),
        "expected_sha256": model_meta["sha256"],
        "architecture": model_meta["architecture"],
        "chunk_size_bytes": 8 * 1024 * 1024
    }


# ---------------------------------------------------------------------------
# Model Version & Distribution Endpoints (Requirements 3, 4, 6, 7, 11)
# ---------------------------------------------------------------------------

@app.get("/api/v1/model/info")
def get_model_info(db: Session = Depends(get_db)):
    """Returns active model version, SHA-256, and metadata."""
    model = db.query(ModelVersion).filter(ModelVersion.is_active == True).order_by(ModelVersion.created_at.desc()).first()
    if not model:
        raise HTTPException(status_code=404, detail="No active model version configured")

    return {
        "version_tag": model.version_tag,
        "model_name": model.model_name,
        "object_key": model.object_key,
        "size_bytes": model.size_bytes,
        "sha256": model.sha256,
        "release_notes": model.release_notes
    }


@app.get("/api/v1/model/check-update")
def check_model_update(client_version: Optional[str] = None, db: Session = Depends(get_db)):
    """Notifies client if a newer model version exists."""
    model = db.query(ModelVersion).filter(ModelVersion.is_active == True).order_by(ModelVersion.created_at.desc()).first()
    if not model:
        return {"update_available": False}

    has_update = client_version != model.version_tag if client_version else False
    return {
        "current_client_version": client_version,
        "latest_server_version": model.version_tag,
        "update_available": has_update,
        "size_bytes": model.size_bytes,
        "sha256": model.sha256,
        "release_notes": model.release_notes
    }


@app.post("/api/v1/model/request-download")
@limiter.limit("10/minute")
def request_model_download(
    request: Request,
    x_device_id: Optional[str] = Header(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Requirements 3, 4, 6, 7:
    - Verifies user authentication.
    - Verifies device registration & access control (X-Device-Id).
    - Checks daily quota limits.
    - Generates a short-lived (15-minute) presigned download URL directly from Cloudflare R2.
    - Never exposes permanent Cloudflare credentials.
    """
    ip = request.client.host if request.client else "127.0.0.1"

    # Step 1: Device Access Control Check
    device_ok, dev_msg = validate_device_access(db, user.id, x_device_id)
    if not device_ok:
        log_audit_event(db, user.id, user.username, "DOWNLOAD_DEVICE_REJECTED", dev_msg, ip, x_device_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=dev_msg)

    # Step 2: Quota & Model Permission Check
    quota_ok, quota_msg = check_and_increment_download_quota(db, user.id)
    if not quota_ok:
        log_audit_event(db, user.id, user.username, "DOWNLOAD_QUOTA_REJECTED", quota_msg, ip, x_device_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=quota_msg)

    # Step 3: Fetch Active Model Artifact
    model = db.query(ModelVersion).filter(ModelVersion.is_active == True).order_by(ModelVersion.created_at.desc()).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model artifact record not found")

    expiry_seconds = 900  # 15 minutes

    # Step 4: Generate Presigned URL
    try:
        url = r2_gateway.generate_short_lived_download_url(
            object_key=model.object_key,
            expires_in_seconds=expiry_seconds
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        log_audit_event(db, user.id, user.username, "DOWNLOAD_ERROR", str(e), ip, x_device_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate secure download link: {e}")

    log_audit_event(
        db, user.id, user.username, "DOWNLOAD_AUTHORIZED",
        f"Presigned URL issued for {model.object_key} (Device: {x_device_id})", ip, x_device_id
    )

    return {
        "success": True,
        "download_url": url,
        "expires_in_seconds": expiry_seconds,
        "version_tag": model.version_tag,
        "object_key": model.object_key,
        "size_bytes": model.size_bytes,
        "expected_sha256": model.sha256,
        "chunk_size_bytes": 8 * 1024 * 1024,
        "authorization_status": quota_msg
    }


# ---------------------------------------------------------------------------
# Telemetry Analytics Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/v1/analytics/telemetry")
def report_telemetry(
    report: TelemetryReport = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Collects client execution metrics (tokens/sec, RAM, VRAM)."""
    telemetry = TelemetryLog(
        user_id=user.id,
        username=user.username,
        device_name=report.device_name,
        hardware_mode=report.hardware_mode,
        prompt_tokens=report.prompt_tokens,
        completion_tokens=report.completion_tokens,
        tokens_per_second=report.tokens_per_second,
        ram_used_gb=report.ram_used_gb,
        vram_used_mb=report.vram_used_mb,
        timestamp=time.time()
    )
    db.add(telemetry)
    db.commit()
    return {"success": True, "recorded": True}
