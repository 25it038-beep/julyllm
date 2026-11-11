"""
HS AI SOLUTIONS — CLIENT RATE LIMITING ENGINE
Layer: CLIENT RATE LIMITING & USAGE GOVERNANCE (july_distribution.client.rate_limiter)
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & GRAVITY LLM RUNTIME

Provides client-side and hybrid sliding-window rate limiting for July and Gravity models.
Supports:
1. Requests-per-minute (RPM) limits by user tier (Standard, Pro, Enterprise).
2. Tokens-per-minute (TPM) limits by user tier.
3. Daily quota request caps.
4. Persistent cross-session state (prevents bypass by CLI restart).
5. Dynamic retry-after cooldown calculation and informative UI messaging.
"""

from __future__ import annotations
import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from .config import get_default_july_dir


TIER_LIMITS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "title": "Standard / Free Tier",
        "rpm": 20,              # 20 requests per minute
        "tpm": 5000,            # 5,000 tokens per minute
        "daily_requests": 500,  # 500 requests per day
        "burst_allowance": 5,
    },
    "developer": {
        "title": "Developer / Pro Tier",
        "rpm": 60,              # 60 requests per minute
        "tpm": 30000,           # 30,000 tokens per minute
        "daily_requests": 5000, # 5,000 requests per day
        "burst_allowance": 15,
    },
    "pro": {
        "title": "Developer / Pro Tier",
        "rpm": 60,              # 60 requests per minute
        "tpm": 30000,           # 30,000 tokens per minute
        "daily_requests": 5000, # 5,000 requests per day
        "burst_allowance": 15,
    },
    "enterprise": {
        "title": "Enterprise Tier",
        "rpm": 180,             # 180 requests per minute
        "tpm": 100000,          # 100,000 tokens per minute
        "daily_requests": 50000,# 50,000 requests per day
        "burst_allowance": 30,
    },
    "creator": {
        "title": "Creator & Founder Account (HS AI Solutions)",
        "rpm": 100000,          # Unlimited
        "tpm": 100000000,       # Unlimited
        "daily_requests": 10000000, # Unlimited
        "burst_allowance": 10000,
        "unlimited": True,
    }
}


class RateLimitExceededError(Exception):
    """Raised when an inference operation violates active rate limits."""
    def __init__(self, message: str, retry_after: float, tier: str, limit_type: str):
        super().__init__(message)
        self.retry_after = retry_after
        self.tier = tier
        self.limit_type = limit_type


class ClientRateLimiter:
    """
    Thread-safe, sliding-window rate limiter for client-side model inference.
    Persists window events across CLI invocations to prevent subversion.
    """

    _instance: Optional["ClientRateLimiter"] = None
    _lock = threading.Lock()

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or (get_default_july_dir() / "rate_limit_state.json")
        self._mutex = threading.RLock()
        self.window_seconds: float = 60.0

    @classmethod
    def get_instance(cls) -> "ClientRateLimiter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load_state(self) -> Dict[str, Any]:
        default_state: Dict[str, Any] = {
            "window_requests": [],  # List of [timestamp, tokens]
            "daily_requests": 0,
            "day_key": time.strftime("%Y-%m-%d"),
            "last_request_time": 0.0
        }
        if not self.state_file.exists():
            return default_state

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                today = time.strftime("%Y-%m-%d")
                if data.get("day_key") != today:
                    data["day_key"] = today
                    data["daily_requests"] = 0
                return data
        except Exception:
            return default_state

    def _save_state(self, state: Dict[str, Any]):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            temp_file.replace(self.state_file)
        except Exception:
            pass

    def _clean_window(self, state: Dict[str, Any], now: float) -> List[List[float]]:
        cutoff = now - self.window_seconds
        valid = [
            req for req in state.get("window_requests", [])
            if isinstance(req, list) and len(req) >= 2 and req[0] > cutoff
        ]
        state["window_requests"] = valid
        return valid

    def get_tier_config(self, tier: str) -> Dict[str, Any]:
        tier_key = (tier or "standard").lower().strip()
        return TIER_LIMITS.get(tier_key, TIER_LIMITS["standard"])

    def check_limit(
        self,
        tier: str = "standard",
        estimated_tokens: int = 100
    ) -> Tuple[bool, float, str, Dict[str, Any]]:
        """
        Evaluates whether a new model request is permitted under current tier limits.

        Returns:
            (is_allowed, retry_after_seconds, violation_reason, metrics_dict)
        """
        with self._mutex:
            now = time.time()
            state = self._load_state()
            valid_requests = self._clean_window(state, now)
            cfg = self.get_tier_config(tier)

            # Bypass limits completely for Creator / Founder accounts
            if cfg.get("unlimited") or (tier and tier.lower() == "creator"):
                current_rpm = len(valid_requests)
                current_tpm = sum(int(r[1]) for r in valid_requests)
                today_count = state.get("daily_requests", 0)
                metrics = {
                    "tier": "creator",
                    "rpm_used": current_rpm,
                    "rpm_max": "Unlimited",
                    "tpm_used": current_tpm,
                    "tpm_max": "Unlimited",
                    "daily_used": today_count,
                    "daily_max": "Unlimited",
                    "retry_after": 0.0
                }
                return True, 0.0, "", metrics

            # 1. Daily Quota Check
            today_count = state.get("daily_requests", 0)
            max_daily = cfg["daily_requests"]
            if today_count >= max_daily:
                # Cooldown until midnight UTC/local
                midnight = now + (86400 - (now % 86400))
                retry_after = max(1.0, midnight - now)
                reason = f"Daily quota of {max_daily} requests reached for {cfg['title']}."
                metrics = {
                    "tier": tier,
                    "rpm_used": len(valid_requests),
                    "rpm_max": cfg["rpm"],
                    "daily_used": today_count,
                    "daily_max": max_daily,
                    "retry_after": retry_after
                }
                return False, retry_after, reason, metrics

            # 2. RPM (Requests Per Minute) Check
            current_rpm = len(valid_requests)
            max_rpm = cfg["rpm"]
            if current_rpm >= max_rpm:
                # Oldest timestamp in window will expire soonest
                oldest_ts = valid_requests[0][0]
                retry_after = max(1.0, (oldest_ts + self.window_seconds) - now)
                reason = f"Rate limit reached ({max_rpm} requests/min) for {cfg['title']}."
                metrics = {
                    "tier": tier,
                    "rpm_used": current_rpm,
                    "rpm_max": max_rpm,
                    "tpm_used": sum(int(r[1]) for r in valid_requests),
                    "tpm_max": cfg["tpm"],
                    "daily_used": today_count,
                    "daily_max": max_daily,
                    "retry_after": retry_after
                }
                return False, retry_after, reason, metrics

            # 3. TPM (Tokens Per Minute) Check
            current_tpm = sum(int(r[1]) for r in valid_requests)
            max_tpm = cfg["tpm"]
            if current_tpm + estimated_tokens > max_tpm:
                oldest_ts = valid_requests[0][0] if valid_requests else now
                retry_after = max(1.0, (oldest_ts + self.window_seconds) - now)
                reason = f"Token throughput limit reached ({max_tpm} tokens/min) for {cfg['title']}."
                metrics = {
                    "tier": tier,
                    "rpm_used": current_rpm,
                    "rpm_max": max_rpm,
                    "tpm_used": current_tpm,
                    "tpm_max": max_tpm,
                    "daily_used": today_count,
                    "daily_max": max_daily,
                    "retry_after": retry_after
                }
                return False, retry_after, reason, metrics

            # Allowed
            metrics = {
                "tier": tier,
                "rpm_used": current_rpm,
                "rpm_max": max_rpm,
                "tpm_used": current_tpm,
                "tpm_max": max_tpm,
                "daily_used": today_count,
                "daily_max": max_daily,
                "retry_after": 0.0
            }
            return True, 0.0, "", metrics

    def record_usage(self, tokens: int = 50):
        """Records a successful request and token consumption in the persistent sliding window."""
        with self._mutex:
            now = time.time()
            state = self._load_state()
            valid_requests = self._clean_window(state, now)
            valid_requests.append([now, max(1, tokens)])
            state["window_requests"] = valid_requests
            state["daily_requests"] = state.get("daily_requests", 0) + 1
            state["last_request_time"] = now
            self._save_state(state)

    def enforce_rate_limit(self, tier: str = "standard", estimated_tokens: int = 100):
        """
        Enforces rate limits. If exceeded, raises RateLimitExceededError.
        """
        allowed, retry_after, reason, metrics = self.check_limit(tier, estimated_tokens)
        if not allowed:
            raise RateLimitExceededError(
                message=reason,
                retry_after=retry_after,
                tier=tier,
                limit_type="rpm" if "requests/min" in reason else "tpm" if "tokens/min" in reason else "daily"
            )

    def get_metrics(self, tier: str = "standard") -> Dict[str, Any]:
        """Returns diagnostic usage snapshot for status dashboards."""
        with self._mutex:
            now = time.time()
            state = self._load_state()
            valid = self._clean_window(state, now)
            cfg = self.get_tier_config(tier)

            rpm_used = len(valid)
            tpm_used = sum(int(r[1]) for r in valid)
            daily_used = state.get("daily_requests", 0)

            if cfg.get("unlimited") or (tier and tier.lower() == "creator"):
                return {
                    "tier": "creator",
                    "tier_title": cfg["title"],
                    "rpm_used": rpm_used,
                    "rpm_max": "Unlimited",
                    "rpm_remaining": "Unlimited",
                    "tpm_used": tpm_used,
                    "tpm_max": "Unlimited",
                    "tpm_remaining": "Unlimited",
                    "daily_used": daily_used,
                    "daily_max": "Unlimited",
                    "daily_remaining": "Unlimited",
                    "window_seconds": self.window_seconds,
                }

            return {
                "tier": tier,
                "tier_title": cfg["title"],
                "rpm_used": rpm_used,
                "rpm_max": cfg["rpm"],
                "rpm_remaining": max(0, cfg["rpm"] - rpm_used),
                "tpm_used": tpm_used,
                "tpm_max": cfg["tpm"],
                "tpm_remaining": max(0, cfg["tpm"] - tpm_used),
                "daily_used": daily_used,
                "daily_max": cfg["daily_requests"],
                "daily_remaining": max(0, cfg["daily_requests"] - daily_used),
                "window_seconds": self.window_seconds,
            }

    def reset_limits(self):
        """Resets the rate limiter state."""
        with self._mutex:
            if self.state_file.exists():
                try:
                    self.state_file.unlink()
                except Exception:
                    pass
