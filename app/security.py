"""
HS AI SOLUTIONS - JULY CLOUD AI SECURITY
Authentication, Authorization, Rate Limiting, & Request Sanitization
Founder: Harshan Seliyan
"""

import time
import hmac
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fastapi import Request, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class RateLimiter:
    """
    Sliding window in-memory rate limiter per IP/client key.
    Enforces maximum requests per minute (RPM).
    """

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - 60.0

        # Prune old timestamps
        timestamps = [t for t in self.requests[client_id] if t > window_start]
        self.requests[client_id] = timestamps

        if len(timestamps) >= self.rpm:
            retry_after = int(60.0 - (now - timestamps[0])) + 1
            return False, retry_after

        self.requests[client_id].append(now)
        return True, 0


rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_RPM)


def _safe_str_cmp(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


async def verify_api_key(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    header_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Verifies that the incoming request provides a valid API key
    either via 'Authorization: Bearer <token>' or 'X-API-Key: <token>'.
    """
    # Rate limit check first
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_RPM} requests per minute. Retry in {retry_after}s.",
            headers={"Retry-After": str(retry_after)}
        )

    # If server has no API key set (or is set to empty), allow dev requests
    if not settings.API_KEY:
        return "open-dev-access"

    token = None
    if auth and auth.credentials:
        token = auth.credentials
    elif header_key:
        token = header_key

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials. Provide 'Authorization: Bearer <key>' or 'X-API-Key: <key>' header.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not _safe_str_cmp(token, settings.API_KEY) and not _safe_str_cmp(token, settings.ADMIN_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key. Access denied."
        )

    return token


async def verify_admin_key(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    header_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Protects administrative operations (model reload, unload, hardware purge).
    Requires explicit ADMIN_KEY.
    """
    token = None
    if auth and auth.credentials:
        token = auth.credentials
    elif header_key:
        token = header_key

    if not token or not _safe_str_cmp(token, settings.ADMIN_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required. Provide valid ADMIN_KEY."
        )

    return token


def sanitize_input(text: str) -> str:
    """Enforces prompt size limits and strips hazardous null bytes."""
    if not text:
        return ""
    clean = text.replace("\x00", "")
    if len(clean) > settings.MAX_PROMPT_CHARS:
        clean = clean[:settings.MAX_PROMPT_CHARS]
    return clean
