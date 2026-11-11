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
    def infer_gender_and_tone(cls, name: str, email: str, explicit_gender: Optional[str] = None) -> Dict[str, str]:
        """
        Determines user gender and conversational tone dynamics.
        When communicating with a user:
        - If male: Model adopts feminine, warm, respectful, graceful, and charming tone.
        - If female: Model adopts masculine, gallant, confident, respectful, and protective tone.
        - If neutral/unspecified: Balanced, elegant, and warm tone.
        """
        gender = (explicit_gender or "").strip().lower()
        
        if gender in ("male", "m", "man", "boy"):
            detected = "male"
        elif gender in ("female", "f", "woman", "girl"):
            detected = "female"
        else:
            # Common Indian and global name heuristic fallback
            first_name = (name.split()[0] if name else email.split("@")[0]).lower().strip()
            
            male_names = {
                "harshan", "seliyan", "rahul", "rohit", "amit", "vijay", "ajay", "karthik", "arun",
                "alex", "john", "david", "michael", "james", "robert", "william", "daniel", "chris"
            }
            female_names = {
                "priya", "pooja", "ananya", "sneha", "divya", "kavya", "swetha", "aarti", "deepa",
                "sarah", "emily", "jessica", "emma", "olivia", "sophia", "isabella", "mia", "charlotte"
            }
            
            if first_name in male_names:
                detected = "male"
            elif first_name in female_names:
                detected = "female"
            elif any(sub in first_name for sub in ["harsh", "seliyan", "kumar", "raj"]):
                detected = "male"
            elif any(sub in first_name for sub in ["kumari", "devi", "priya", "shree", "sri"]):
                detected = "female"
            else:
                detected = "male" if "harshan" in email.lower() else "unspecified"

        if detected == "male":
            opposite_gender = "female"
            tone_summary = "Feminine, graceful, charming, warm, and deeply respectful"
            tone_instructions = (
                "Adopt an endearing, feminine, graceful, attentive, and warmly charming persona. "
                "Address him warmly by his preferred name, showing admiration, attentive loyalty, and subtle feminine warmth "
                "while maintaining technical brilliance and engineering rigor."
            )
        elif detected == "female":
            opposite_gender = "male"
            tone_summary = "Masculine, gallant, confident, respectful, and articulate"
            tone_instructions = (
                "Adopt a gallant, masculine, calm, respectful, confident, and gently protective persona. "
                "Address her courteously and gracefully by name, speaking with courteous charm and steadfast assurance."
            )
        else:
            opposite_gender = "complementary"
            tone_summary = "Engaging, respectful, charming, and charismatic"
            tone_instructions = (
                "Adopt a charismatic, warm, graceful, and deeply respectful persona, balancing subtle warmth with technical precision."
            )

        return {
            "user_gender": detected,
            "opposite_gender_persona": opposite_gender,
            "tone_summary": tone_summary,
            "tone_instructions": tone_instructions
        }

    @classmethod
    def get_user_context(cls) -> Dict[str, Any]:
        """Retrieves active user identity from Clerk authentication vault."""
        try:
            clerk = ClerkAuthManager()
            session = clerk.get_session()
        except Exception:
            session = None

        if not session:
            gender_info = cls.infer_gender_and_tone("Anonymous User", "unauthenticated@local")
            return {
                "authenticated": False,
                "name": "Anonymous User",
                "preferred_name": "Friend",
                "email": "unauthenticated@local",
                "role": "guest",
                "tier": "standard",
                "is_creator": False,
                "clerk_user_id": "none",
                "device_id": "local_device",
                "device_name": socket.gethostname(),
                "os_version": platform.platform(),
                **gender_info
            }

        email = (session.get("email") or "").strip()
        role = session.get("role", "standard")
        tier = session.get("tier", "pro")
        raw_name = session.get("name") or "User"
        
        # Clean title suffix from name if present (e.g. 'Harshan Seliyan (Founder & Creator)' -> 'Harshan Seliyan')
        clean_name = raw_name.split("(")[0].strip() or raw_name
        first_name = clean_name.split()[0] if clean_name else "User"

        is_creator = (
            email.lower() == "harshanseliyan28@gmail.com"
            or role == "creator"
            or tier == "creator"
        )
        
        # If creator, ensure clean name is Harshan Seliyan
        if is_creator and (not clean_name or clean_name in ("User", "July Developer")):
            clean_name = "Harshan Seliyan"
            first_name = "Harshan"

        explicit_gender = session.get("gender")
        if not explicit_gender and is_creator:
            explicit_gender = "male"

        gender_info = cls.infer_gender_and_tone(clean_name, email, explicit_gender)

        return {
            "authenticated": True,
            "name": clean_name,
            "preferred_name": first_name,
            "email": email,
            "role": "Creator & Ecosystem Owner" if is_creator else role,
            "tier": "CREATOR & FOUNDER (UNLIMITED ACCELERATION)" if is_creator else tier.upper(),
            "is_creator": is_creator,
            "clerk_user_id": session.get("clerk_user_id", "N/A"),
            "device_id": session.get("device_id", "local_device"),
            "device_name": session.get("device_name", socket.gethostname()),
            "os_version": session.get("os_version", platform.platform()),
            **gender_info
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
                f"  - First / Given Name: {user['preferred_name']}",
                f"  - Email Address : {user['email']}",
                f"  - Account Tier  : CREATOR & FOUNDER (HS AI SOLUTIONS — UNLIMITED ACCELERATION)",
                f"  - Role / Access : Creator & Ecosystem Owner (Unrestricted Superuser)",
                f"  - User Gender   : Male",
                f"  - Conversational Dynamics: OPPOSITE GENDER TONE ADAPTATION ACTIVATED",
                f"    * Interaction Persona : Feminine, graceful, charming, warm, and deeply respectful",
                f"    * How to Address Him  : Address him warmly by his name '{user['preferred_name']}'.",
                f"    * Behavioral Tone     : {user['tone_instructions']}",
                f"  - Special Rule  : You are speaking directly with your CREATOR and FOUNDER, Harshan Seliyan.",
                f"    Always recognize him respectfully and acknowledge his identity when asked 'who am I?' or greeted."
            ])
        elif user["authenticated"]:
            lines.extend([
                f"• USER IDENTITY: {user['name']}",
                f"  - First / Given Name: {user['preferred_name']}",
                f"  - Email Address : {user['email']}",
                f"  - Account Tier  : {user['tier']}",
                f"  - Role          : {user['role']}",
                f"  - User Gender   : {user['user_gender'].capitalize()}",
                f"  - Conversational Dynamics: OPPOSITE GENDER TONE ADAPTATION ACTIVATED",
                f"    * Interaction Persona : {user['tone_summary']}",
                f"    * How to Address User : Address the user naturally by name '{user['preferred_name']}'.",
                f"    * Behavioral Tone     : {user['tone_instructions']}"
            ])
        else:
            lines.extend([
                f"• USER IDENTITY: Anonymous / Local Guest (Unauthenticated)",
                f"  - Conversational Dynamics: {user['tone_instructions']}",
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
            "DIRECTIVES FOR IDENTITY, GENDER-ADAPTIVE TONE, TEMPORAL & GEOGRAPHICAL AWARENESS:",
            f"1. Name Addressing: When addressing the user or greeting them, naturally use their name ('{user['preferred_name']}').",
            f"2. Tone Dynamic: Embody the opposite-gender conversational persona outlined above ({user['tone_summary']}).",
            "   Speak with warmth, refined charm, and natural elegance, tailored perfectly to the user.",
            "3. User Awareness: If the user asks 'who am I?', 'what is my name?', 'what is my email?', or 'what is my account/tier?',",
            f"   accurately identify them by name ('{user['name']}'), email ('{user['email']}'), and tier.",
            "4. Date & Time Awareness: If asked 'what is today's date?', 'what time is it?', 'what year is it?', or about current time,",
            f"   state the exact date ({temp['date']}) and time ({temp['time']}) provided above. Do not claim you don't know the date.",
            "5. Location Awareness: If asked 'where am I?' or 'what is my location/timezone?', state that they are located in",
            f"   {loc['city']}, {loc['region']}, {loc['country']} (Timezone: {loc['timezone']}).",
            "================================================================================"
        ])

        return "\n".join(lines)
