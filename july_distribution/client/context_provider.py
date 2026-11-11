"""
HS AI SOLUTIONS — DYNAMIC RUNTIME CONTEXT ENGINE
Module: july_distribution.client.context_provider
Founder: Harshan Seliyan | Organization: HS AI Solutions

Dynamically supplies live context to July LLM & Gravity LLM:
1. User Identity: Authenticated Clerk user profile, creator status, email, tier, role.
2. Temporal Anchor: Current live local date/time, day of week, UTC time, year (2026).
3. Geographical Location: City, Region, Country, Timezone, and Device Boundary.
"""

from __future__ import annotations
import os
import json
import socket
import platform
import datetime
import urllib.request
from typing import Dict, Any, Optional

from .clerk_auth import ClerkAuthManager


class RuntimeContextProvider:
    _cached_location: Optional[Dict[str, str]] = None
    _location_fetched: bool = False

    @classmethod
    def get_user_context(cls) -> Dict[str, Any]:
        """Retrieves active user identity from Clerk authentication vault."""
        try:
            clerk = ClerkAuthManager()
            session = clerk.get_session()
        except Exception:
            session = None

        if not session:
            return {
                "authenticated": False,
                "name": "Anonymous User",
                "email": "unauthenticated@local",
                "role": "guest",
                "tier": "standard",
                "is_creator": False,
                "clerk_user_id": "none",
                "device_id": "local_device",
                "device_name": socket.gethostname(),
                "os_version": platform.platform()
            }

        email = (session.get("email") or "").strip()
        role = session.get("role", "standard")
        tier = session.get("tier", "pro")
        name = session.get("name") or "User"

        is_creator = (
            email.lower() == "harshanseliyan28@gmail.com"
            or role == "creator"
            or tier == "creator"
        )

        return {
            "authenticated": True,
            "name": name,
            "email": email,
            "role": "Creator & Ecosystem Owner" if is_creator else role,
            "tier": "CREATOR & FOUNDER (UNLIMITED ACCELERATION)" if is_creator else tier.upper(),
            "is_creator": is_creator,
            "clerk_user_id": session.get("clerk_user_id", "N/A"),
            "device_id": session.get("device_id", "local_device"),
            "device_name": session.get("device_name", socket.gethostname()),
            "os_version": session.get("os_version", platform.platform())
        }

    @classmethod
    def get_temporal_context(cls) -> Dict[str, Any]:
        """Provides accurate, live date and time context in both local timezone and UTC."""
        now_local = datetime.datetime.now().astimezone()
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        date_str = now_local.strftime("%A, %B %d, %Y")
        time_str = now_local.strftime("%H:%M:%S")
        tz_name = now_local.strftime("%Z") or "Local"
        tz_offset = now_local.strftime("%z")

        return {
            "local_datetime": f"{date_str} at {time_str} {tz_name} (UTC{tz_offset})",
            "date": date_str,
            "time": time_str,
            "day_of_week": now_local.strftime("%A"),
            "year": now_local.year,
            "month": now_local.strftime("%B"),
            "day": now_local.day,
            "timezone": f"{tz_name} (UTC{tz_offset})",
            "utc_datetime": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "iso_timestamp": now_local.isoformat()
        }

    @classmethod
    def get_location_context(cls) -> Dict[str, str]:
        """Resolves geographical location using low-latency IP lookup or local system fallback."""
        if cls._location_fetched and cls._cached_location:
            return cls._cached_location

        now_local = datetime.datetime.now().astimezone()
        tz_name = now_local.strftime("%Z") or "Local"
        tz_offset = now_local.strftime("%z")

        # Default fallback from OS environment
        location = {
            "country": "India" if "+0530" in tz_offset else "Global",
            "region": "Tamil Nadu" if "+0530" in tz_offset else "Local Region",
            "city": "Chennai" if "+0530" in tz_offset else "Local City",
            "timezone": f"{tz_name} (UTC{tz_offset})",
            "hostname": socket.gethostname(),
            "os": platform.platform()
        }

        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=status,country,regionName,city,timezone",
                headers={"User-Agent": "July-Context-Engine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "success":
                    if data.get("country"):
                        location["country"] = data["country"]
                    if data.get("regionName"):
                        location["region"] = data["regionName"]
                    if data.get("city"):
                        location["city"] = data["city"]
                    if data.get("timezone"):
                        location["timezone"] = f"{data['timezone']} ({tz_name} UTC{tz_offset})"
        except Exception:
            pass

        cls._cached_location = location
        cls._location_fetched = True
        return location

    @classmethod
    def build_system_context_block(cls) -> str:
        """Constructs the prompt directive block injected into model context."""
        user = cls.get_user_context()
        temp = cls.get_temporal_context()
        loc = cls.get_location_context()

        lines = [
            "================================================================================",
            "LIVE RUNTIME CONTEXT (USER IDENTITY, DATE/TIME & GEOLOCATION):",
            "================================================================================"
        ]

        if user["is_creator"]:
            lines.extend([
                f"• USER IDENTITY: Harshan Seliyan (Founder, Creator & Chief Architect)",
                f"  - Email Address : {user['email']}",
                f"  - Account Tier  : CREATOR & FOUNDER (HS AI SOLUTIONS — UNLIMITED ACCELERATION)",
                f"  - Role / Access : Creator & Ecosystem Owner (Unrestricted Superuser)",
                f"  - Special Rule  : You are speaking directly with your CREATOR and FOUNDER, Harshan Seliyan.",
                f"    Always recognize him respectfully and acknowledge his identity when asked 'who am I?' or greeted."
            ])
        elif user["authenticated"]:
            lines.extend([
                f"• USER IDENTITY: {user['name']}",
                f"  - Email Address : {user['email']}",
                f"  - Account Tier  : {user['tier']}",
                f"  - Role          : {user['role']}"
            ])
        else:
            lines.extend([
                f"• USER IDENTITY: Anonymous / Local Guest (Unauthenticated)",
                f"  - Recommendation: Ask user to authenticate with 'july login'."
            ])

        lines.extend([
            f"• CURRENT DATE & TIME:",
            f"  - Local Time    : {temp['local_datetime']}",
            f"  - Day of Week   : {temp['day_of_week']}",
            f"  - UTC Timestamp : {temp['utc_datetime']}",
            f"  - Year Anchor   : {temp['year']} (Always use {temp['year']} for temporal calculations)",
            f"• GEOGRAPHICAL LOCATION & HARDWARE HOST:",
            f"  - Location      : {loc['city']}, {loc['region']}, {loc['country']}",
            f"  - Timezone      : {loc['timezone']}",
            f"  - Device Host   : {loc['hostname']} ({loc['os']})",
            "================================================================================",
            "DIRECTIVES FOR IDENTITY, TEMPORAL & GEOGRAPHICAL AWARENESS:",
            "1. User Awareness: If the user asks 'who am I?', 'what is my email?', 'what is my account?', or 'what is my plan/tier?',",
            "   accurately identify them using the verified account details above.",
            "2. Date & Time Awareness: If asked 'what is today's date?', 'what time is it?', 'what year is it?', or about current time,",
            f"   state the exact date ({temp['date']}) and time ({temp['time']}) provided above. Do not claim you don't know the date.",
            "3. Location Awareness: If asked 'where am I?' or 'what is my location/timezone?', state that they are located in",
            f"   {loc['city']}, {loc['region']}, {loc['country']} (Timezone: {loc['timezone']}).",
            "================================================================================"
        ])

        return "\n".join(lines)
