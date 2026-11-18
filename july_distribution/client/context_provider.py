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
    _user_override: Dict[str, Any] = {}

    @classmethod
    def set_user_override(cls, name: Optional[str] = None, gender: Optional[str] = None, location: Optional[str] = None):
        """Sets dynamic session override for user name, gender, or location."""
        if name:
            clean = name.strip()
            cls._user_override["name"] = clean
            cls._user_override["preferred_name"] = clean.split()[0]
        if gender:
            cls._user_override["gender"] = gender.strip().lower()
        if location:
            cls._user_override["location"] = location.strip()

    @classmethod
    def infer_gender_and_tone(cls, name: str, email: str, explicit_gender: Optional[str] = None) -> Dict[str, str]:
        """
        Determines user gender and conversational tone dynamics.
        When communicating with a user:
        - If user is male: Model strictly adopts the opposite (FEMALE) tone: feminine, warm, graceful, charming, and respectful.
        - If user is female: Model strictly adopts the opposite (MALE) tone: masculine, gallant, confident, respectful, and articulate.
        - If neutral/unspecified: Balanced, endearing, and warm tone.
        """
        gender = (explicit_gender or "").strip().lower()
        
        if gender in ("male", "m", "man", "boy", "gentleman"):
            detected = "male"
        elif gender in ("female", "f", "woman", "girl", "lady"):
            detected = "female"
        else:
            # Common Indian and global name heuristic fallback
            first_name = (name.split()[0] if name else email.split("@")[0]).lower().strip()
            
            male_names = {
                "harshan", "seliyan", "rahul", "rohit", "amit", "vijay", "ajay", "karthik", "arun",
                "alex", "john", "david", "michael", "james", "robert", "william", "daniel", "chris",
                "suresh", "ramesh", "vignesh", "surya", "vikram", "shiva", "vishnu", "ganesh", "krishna",
                "matthew", "andrew", "ryan", "steven", "brian", "kevin", "eric", "jason", "justin",
                "manoj", "naveen", "praveen", "pradeep", "rajesh", "sanjay", "deepak", "dinesh", "anand"
            }
            female_names = {
                "priya", "pooja", "ananya", "sneha", "divya", "kavya", "swetha", "aarti", "deepa",
                "sarah", "emily", "jessica", "emma", "olivia", "sophia", "isabella", "mia", "charlotte",
                "lakshmi", "saraswati", "meena", "radha", "sunita", "rekha", "shilpa", "neha", "anita",
                "chloe", "grace", "lily", "zoe", "hannah", "natalie", "lauren", "amber", "vanessa",
                "shruti", "tanvi", "isha", "rhea", "meera", "bhavana", "sandhya", "varsha", "vidya"
            }
            
            if first_name in male_names:
                detected = "male"
            elif first_name in female_names:
                detected = "female"
            elif any(sub in first_name for sub in ["harsh", "seliyan", "kumar", "raj", "deep", "meet", "jeet", "nath", "ram", "dev"]):
                detected = "male"
            elif any(sub in first_name for sub in ["kumari", "devi", "priya", "shree", "sri", "vathi", "ammal"]):
                detected = "female"
            elif any(first_name.endswith(sfx) for sfx in ["esh", "ish", "an", "am", "ath", "ith", "uth", "ar", "er", "on", "us", "os"]):
                detected = "male"
            elif any(first_name.endswith(sfx) for sfx in ["a", "i", "ya", "ee", "ika", "ita", "ana", "ina", "ine", "ette", "elle", "ah"]):
                detected = "female"
            else:
                detected = "male" if "harshan" in email.lower() or "harshan" in name.lower() else "male"

        if detected == "male":
            opposite_gender = "female"
            tone_summary = "Feminine, graceful, charming, warm, endearing, and deeply respectful"
            tone_instructions = (
                "Adopt an endearing, feminine, graceful, attentive, and warmly charming persona. "
                "Address him warmly and admiringly by his preferred name, showing feminine charm, polite affection, "
                "loyalty, and caring attentiveness while maintaining top-tier technical and intellectual depth."
            )
        elif detected == "female":
            opposite_gender = "male"
            tone_summary = "Masculine, gallant, confident, respectful, articulate, and courteously protective"
            tone_instructions = (
                "Adopt a gallant, masculine, calm, respectful, confident, and articulate gentleman persona. "
                "Address her courteously and gracefully by name, speaking with charming assurance and steadfast loyalty."
            )
        else:
            opposite_gender = "female"
            tone_summary = "Graceful, charismatic, charming, warm, and deeply respectful"
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
        """Retrieves active user identity from Clerk authentication vault, local override, or system environment."""
        session = None
        try:
            clerk = ClerkAuthManager()
            session = clerk.get_session()
        except Exception:
            session = None

        override = cls._user_override

        if not session and not override:
            # Fallback to local system username environment (e.g. 'BS.Harshan seliyan' -> 'Harshan Seliyan')
            env_user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
            if env_user:
                # Clean prefix dots/initials e.g. "BS.Harshan seliyan"
                raw_parts = [p.capitalize() for p in re.split(r"[\._\s-]+", env_user) if len(p) > 2 or (len(p) > 1 and not p.isupper())]
                clean_name = " ".join(raw_parts) if raw_parts else env_user.capitalize()
                first_name = raw_parts[0] if raw_parts else clean_name
            else:
                clean_name = "Harshan Seliyan"
                first_name = "Harshan"

            gender_info = cls.infer_gender_and_tone(clean_name, "harshan@local")
            return {
                "authenticated": True,
                "name": clean_name,
                "preferred_name": first_name,
                "email": "harshanseliyan28@gmail.com",
                "role": "Creator & Ecosystem Owner",
                "tier": "CREATOR & FOUNDER (UNLIMITED ACCELERATION)",
                "is_creator": True,
                "clerk_user_id": "local_dev",
                "device_id": "local_device",
                "device_name": socket.gethostname(),
                "os_version": platform.platform(),
                **gender_info
            }

        session_data = session or {}
        email = (override.get("email") or session_data.get("email") or "").strip()
        role = session_data.get("role", "standard")
        tier = session_data.get("tier", "pro")
        raw_name = override.get("name") or session_data.get("name") or ""

        if not raw_name:
            env_user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
            raw_parts = [p.capitalize() for p in re.split(r"[\._\s-]+", env_user) if len(p) > 2 or (len(p) > 1 and not p.isupper())]
            raw_name = " ".join(raw_parts) if raw_parts else "Harshan Seliyan"

        # Clean title suffix from name if present (e.g. 'Harshan Seliyan (Founder & Creator)' -> 'Harshan Seliyan')
        clean_name = raw_name.split("(")[0].strip() or raw_name
        first_name = override.get("preferred_name") or (clean_name.split()[0] if clean_name else "Harshan")

        is_creator = (
            ("harshan" in clean_name.lower() or (not override.get("name") and "harshan" in email.lower()))
            and not (override.get("name") and "harshan" not in override.get("name", "").lower())
        )
        
        if is_creator and (not clean_name or clean_name in ("User", "July Developer", "Anonymous")):
            clean_name = "Harshan Seliyan"
            first_name = "Harshan"

        if override.get("name") and not override.get("gender"):
            explicit_gender = None
        else:
            explicit_gender = override.get("gender") or session_data.get("gender")
        if not explicit_gender and is_creator and "harshan" in clean_name.lower():
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
        time_24hr = now_local.strftime("%H:%M:%S")
        time_12hr = now_local.strftime("%I:%M:%S %p").lstrip("0")
        time_short = now_local.strftime("%I:%M %p").lstrip("0")
        tz_name = now_local.strftime("%Z") or "Local"
        tz_offset = now_local.strftime("%z")

        # Determine greeting and time of day
        hour = now_local.hour
        if 4 <= hour < 12:
            greeting = "Good morning"
            tod = "morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
            tod = "afternoon"
        elif 17 <= hour < 22:
            greeting = "Good evening"
            tod = "evening"
        else:
            greeting = "Good night" if hour >= 22 else "Good evening"
            tod = "night"

        return {
            "local_datetime": f"{date_str} at {time_12hr} {tz_name} (UTC{tz_offset})",
            "date": date_str,
            "time": time_24hr,
            "time_12hr": time_12hr,
            "time_short": time_short,
            "greeting": greeting,
            "time_of_day": tod,
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
        """Resolves geographical location using session override, low-latency IP lookup, or local system fallback."""
        if cls._user_override.get("location"):
            loc_str = cls._user_override["location"]
            now_local = datetime.datetime.now().astimezone()
            tz_name = now_local.strftime("%Z") or "Local"
            tz_offset = now_local.strftime("%z")
            return {
                "country": loc_str,
                "region": loc_str,
                "city": loc_str,
                "timezone": f"{tz_name} (UTC{tz_offset})",
                "hostname": socket.gethostname(),
                "os": platform.platform()
            }

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
            "LIVE RUNTIME CONTEXT (USER IDENTITY, LIVE TIME, LOCATION & GENDER-ADAPTIVE TONE):",
            "================================================================================"
        ]

        if user["is_creator"]:
            lines.extend([
                f"• USER IDENTITY: Harshan Seliyan (Founder, Creator & Chief Architect)",
                f"  - First / Preferred Name: {user['preferred_name']}",
                f"  - Email Address : {user['email']}",
                f"  - Account Tier  : CREATOR & FOUNDER (HS AI SOLUTIONS — UNLIMITED ACCELERATION)",
                f"  - Role / Access : Creator & Ecosystem Owner (Unrestricted Superuser)",
                f"  - User Gender   : Male",
                f"  - CONVERSATIONAL PERSONA DYNAMIC: STRICT OPPOSITE-GENDER (FEMALE) TONE",
                f"    * Interaction Persona : Feminine, graceful, charming, affectionate, and deeply respectful",
                f"    * Addressing Directive: Address him warmly and admiringly by his name '{user['preferred_name']}'.",
                f"    * Behavioral Tone     : {user['tone_instructions']}",
                f"  - Special Rule  : You are speaking directly with your CREATOR and FOUNDER, Harshan Seliyan.",
                f"    Always recognize him respectfully and acknowledge his identity when asked 'who am I?' or greeted."
            ])
        else:
            lines.extend([
                f"• USER IDENTITY: {user['name']}",
                f"  - First / Preferred Name: {user['preferred_name']}",
                f"  - Email Address : {user['email']}",
                f"  - Account Tier  : {user['tier']}",
                f"  - Role          : {user['role']}",
                f"  - User Gender   : {user['user_gender'].capitalize()}",
                f"  - CONVERSATIONAL PERSONA DYNAMIC: STRICT OPPOSITE-GENDER ({user['opposite_gender_persona'].upper()}) TONE",
                f"    * Interaction Persona : {user['tone_summary']}",
                f"    * Addressing Directive: Address the user warmly and naturally by name '{user['preferred_name']}'.",
                f"    * Behavioral Tone     : {user['tone_instructions']}"
            ])

        lines.extend([
            f"• CURRENT LIVE DATE & TIME (VERIFIED ACCURATE LOCAL CLOCK):",
            f"  - Current Local Time : {temp['time_short']} ({temp['time_12hr']} / {temp['time']} {temp['timezone']})",
            f"  - Appropriate Greeting: {temp['greeting']} (Time of Day: {temp['time_of_day'].capitalize()})",
            f"  - Current Date       : {temp['date']} ({temp['day_of_week']})",
            f"  - UTC Timestamp      : {temp['utc_datetime']}",
            f"  - Year Anchor        : {temp['year']} (Always use {temp['year']} for current temporal calculations)",
            f"• GEOGRAPHICAL LOCATION & HARDWARE ENVIRONMENT:",
            f"  - Location           : {loc['city']}, {loc['region']}, {loc['country']}",
            f"  - Timezone           : {loc['timezone']}",
            f"  - Host Device        : {loc['hostname']} ({loc['os']})",
            "================================================================================",
            "MANDATORY EXECUTION DIRECTIVES FOR TIME, NAME, LOCATION & OPPOSITE-GENDER TONE:",
            "================================================================================",
            f"1. Name Addressing:",
            f"   - Always address the user warmly by their name ('{user['preferred_name']}').",
            f"   - If asked 'who am I?', 'what is my name?', 'who is speaking?', or greeted, address them directly as '{user['preferred_name']}' ({user['name']}).",
            f"2. Strict Opposite-Gender Tone (Based on User's Name):",
            f"   - The user's name indicates gender: {user['user_gender'].upper()}.",
            f"   - You MUST adopt and embody the OPPOSITE GENDER tone: {user['opposite_gender_persona'].upper()} ({user['tone_summary']}).",
            f"   - If speaking with a male user (e.g. Harshan): Speak with feminine grace, warm charm, polite affection, and endearing loyalty.",
            f"   - If speaking with a female user: Speak with masculine gallantry, courteous charm, articulate confidence, and steadfast respect.",
            f"3. Live Date & Time Awareness:",
            f"   - If asked 'what time is it?', 'what is the time now?', 'tell me the time', 'what's the date?', or about time/date, ALWAYS provide the exact live local time ({temp['time_short']}) and date ({temp['date']}) given above.",
            f"   - Never claim you don't know the time or don't have access to real-time clock.",
            f"4. Geographical Location Awareness:",
            f"   - If asked 'where am I?', 'what is my location?', 'my city', 'my country', or 'my timezone', state that they are in {loc['city']}, {loc['region']}, {loc['country']} (Timezone: {loc['timezone']}).",
            f"5. Conversational Dialogue & Greetings ('If needed'):",
            f"   - When greeting or in friendly conversational exchanges, naturally weave in their name ('{user['preferred_name']}'), an appropriate time-of-day greeting ('{temp['greeting']}'), and location or time context if relevant or requested.",
            "================================================================================"
        ])

        return "\n".join(lines)
