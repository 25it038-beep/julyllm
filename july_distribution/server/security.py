"""
HS AI SOLUTIONS â€” JULY CONTROL SERVER SECURITY & ACCESS CONTROL
Layer: SECURITY & TOKEN CONTROLLER (july_distribution.server.security)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Implements:
- PBKDF2-HMAC-SHA256 password hashing.
- Bearer token lifecycle (issuance, validation, revocation).
- Device Registration & Access Control (Requirement 7).
- Daily quota tracking and rate enforcement.
- Security audit logging with client IP and device tracking.
"""

from __future__ import annotations
import hmac
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from .database import User, Token, Device, AuditLog


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes password with PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies password hash in constant time."""
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, password_hash)


def create_auth_token(db: Session, user_id: int, expiry_days: int = 7) -> str:
    """Generates and stores a secure bearer authentication token."""
    token = f"july_tok_{secrets.token_hex(32)}"
    now = time.time()
    expires_at = now + (expiry_days * 86400)

    token_record = Token(
        token=token,
        user_id=user_id,
        created_at=now,
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(token_record)
    db.commit()
    return token


def revoke_token(db: Session, token: str) -> bool:
    """Revokes a token upon logout."""
    token_record = db.query(Token).filter(Token.token == token).first()
    if token_record:
        token_record.is_revoked = True
        db.commit()
        return True
    return False


def validate_token(db: Session, token: str) -> Optional[User]:
    """Validates bearer token and returns active User."""
    if not token or not token.startswith("july_tok_"):
        return None

    now = time.time()
    token_record = (
        db.query(Token)
        .filter(
            Token.token == token,
            Token.is_revoked == False,
            Token.expires_at > now
        )
        .first()
    )

    if not token_record:
        return None

    user = db.query(User).filter(User.id == token_record.user_id, User.is_active == True).first()
    return user


def register_or_update_device(
    db: Session,
    user_id: int,
    device_id: str,
    device_name: str,
    os_version: str = "Windows",
    max_devices_per_user: int = 3
) -> Tuple[bool, str, Device]:
    """
    Registers or updates a client device under the authenticated user account.
    Enforces maximum device quota per user account.
    """
    now = time.time()
    device = db.query(Device).filter(Device.user_id == user_id, Device.device_id == device_id).first()

    if device:
        # Update last seen
        device.device_name = device_name
        device.os_version = os_version
        device.last_seen_at = now
        db.commit()
        if device.status == "REVOKED":
            return False, "This device has been revoked by an administrator", device
        return True, "Device access active", device

    # Check device count limit
    count = db.query(Device).filter(Device.user_id == user_id).count()
    if count >= max_devices_per_user:
        return False, f"Maximum registered devices limit reached ({count}/{max_devices_per_user})", None

    new_device = Device(
        user_id=user_id,
        device_id=device_id,
        device_name=device_name,
        os_version=os_version,
        status="APPROVED",
        registered_at=now,
        last_seen_at=now
    )
    db.add(new_device)
    db.commit()
    return True, "Device registered and authorized", new_device


def validate_device_access(db: Session, user_id: int, device_id: Optional[str]) -> Tuple[bool, str]:
    """
    Verifies that the requesting device is registered and has APPROVED status.
    """
    if not device_id:
        return False, "Device identification (X-Device-Id) is required for model retrieval"

    device = db.query(Device).filter(Device.user_id == user_id, Device.device_id == device_id).first()
    if not device:
        return False, f"Device '{device_id}' is not registered under this account. Please register first."

    if device.status != "APPROVED":
        return False, f"Access denied: Device '{device.device_name}' status is {device.status}"

    # Update last seen
    device.last_seen_at = time.time()
    db.commit()
    return True, f"Device '{device.device_name}' authorized"


def check_and_increment_download_quota(db: Session, user_id: int) -> Tuple[bool, str]:
    """Checks user daily download quota and increments count if permitted."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return False, "User not found"

    if not user.model_access_granted:
        return False, "Model access permission has not been granted for this account"

    # Reset quota if a new UTC day has started
    if user.last_download_date != today_str:
        user.downloads_today = 0
        user.last_download_date = today_str

    if user.downloads_today >= user.daily_download_quota:
        return False, f"Daily download limit reached ({user.downloads_today}/{user.daily_download_quota}). Quota resets at 00:00 UTC."

    user.downloads_today += 1
    user.last_download_date = today_str
    db.commit()

    return True, f"Authorized ({user.downloads_today}/{user.daily_download_quota} downloads used today)"


def log_audit_event(
    db: Session,
    user_id: Optional[int],
    username: Optional[str],
    event_type: str,
    details: str,
    ip_address: str = "127.0.0.1",
    device_id: Optional[str] = None
):
    """Appends an event to the security audit log."""
    try:
        log = AuditLog(
            user_id=user_id,
            username=username,
            device_id=device_id,
            event_type=event_type,
            details=details,
            ip_address=ip_address,
            timestamp=time.time()
        )
        db.add(log)
        db.commit()
    except Exception:
        pass

