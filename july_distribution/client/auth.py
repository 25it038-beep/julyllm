"""
HS AI SOLUTIONS â€” JULY CLIENT AUTHENTICATION
Layer: CLIENT AUTH & SESSION (july_distribution.client.auth)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Manages per-computer user authentication and active bearer token storage.
"""

from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional

from .config import get_default_july_dir, ClientConfig


class ClientAuthManager:
    """Manages local token caching and server communication."""

    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig.load()
        self.session_file = get_default_july_dir() / "session.json"

    def get_session(self) -> Optional[Dict[str, Any]]:
        # 1. Check Clerk secure credential vault
        try:
            from .clerk_auth import ClerkAuthManager
            clerk_mgr = ClerkAuthManager()
            clerk_sess = clerk_mgr.get_session()
            if clerk_sess:
                return clerk_sess
        except Exception:
            pass

        # 2. Check legacy session file
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_token(self) -> Optional[str]:
        session = self.get_session()
        if session:
            return session.get("token")
        return None

    def is_authenticated(self) -> bool:
        try:
            from .clerk_auth import ClerkAuthManager
            clerk_mgr = ClerkAuthManager()
            if clerk_mgr.is_authenticated():
                return True
        except Exception:
            pass
        return bool(self.get_token())

    def login(self, username: str, password: str, server_url: Optional[str] = None) -> Dict[str, Any]:
        from .hardware import get_device_identity
        dev_info = get_device_identity()

        url = (server_url or self.config.server_url).rstrip("/") + "/api/v1/auth/login"
        payload = json.dumps({
            "username": username,
            "password": password,
            "device_id": dev_info["device_id"],
            "device_name": dev_info["device_name"]
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_msg)
                raise ConnectionError(err_json.get("detail", str(e)))
            except Exception:
                raise ConnectionError(f"Login failed (HTTP {e.code}): {err_msg}")
        except Exception as e:
            raise ConnectionError(f"Could not reach control server at {url}: {e}")

        # Store session
        session_data = {
            "token": data["token"],
            "username": data["username"],
            "role": data.get("role", "standard"),
            "model_access_granted": data.get("model_access_granted", True),
            "device_id": dev_info["device_id"],
            "device_name": dev_info["device_name"],
            "device_status": data.get("device_status", "APPROVED"),
            "server_url": server_url or self.config.server_url
        }
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)

        return session_data

    def register(self, username: str, email: str, password: str, server_url: Optional[str] = None) -> Dict[str, Any]:
        url = (server_url or self.config.server_url).rstrip("/") + "/api/v1/auth/register"
        payload = json.dumps({"username": username, "email": email, "password": password}).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_msg)
                raise ConnectionError(err_json.get("detail", str(e)))
            except Exception:
                raise ConnectionError(f"Registration failed: {err_msg}")
        except Exception as e:
            raise ConnectionError(f"Could not reach control server: {e}")

        session_data = {
            "token": data["token"],
            "username": data["username"],
            "role": "standard",
            "model_access_granted": True,
            "server_url": server_url or self.config.server_url
        }
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)

        return session_data

    def logout(self) -> bool:
        try:
            from .clerk_auth import ClerkAuthManager
            ClerkAuthManager().logout()
        except Exception:
            pass

        token = self.get_token()
        session = self.get_session()
        server_url = (session.get("server_url") if session else self.config.server_url).rstrip("/")

        if token:
            try:
                req = urllib.request.Request(
                    f"{server_url}/api/v1/auth/logout",
                    headers={"Authorization": f"Bearer {token}"},
                    data=b""
                )
                with urllib.request.urlopen(req, timeout=5):
                    pass
            except Exception:
                pass

        if self.session_file.exists():
            self.session_file.unlink(missing_ok=True)
        return True

