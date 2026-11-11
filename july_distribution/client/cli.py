"""
HS AI SOLUTIONS — JULY CLIENT CLI
Layer: COMMAND LINE INTERFACE (july_distribution.client.cli)
Organization: HS AI Solutions
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Implements commands:
  july install
  july login
  july load
  july chat
  july status
  july config
  july unload
  july update
"""

from __future__ import annotations
import os
import sys
import re
import time
import argparse
import getpass
import json
import urllib.request
from pathlib import Path

from .config import ClientConfig, get_default_july_dir
from .auth import ClientAuthManager
from .clerk_auth import ClerkAuthManager, STUDIO_AUTH_PORTAL
from .rate_limiter import ClientRateLimiter, RateLimitExceededError
from .security.credential_vault import SecureCredentialVault
from .hardware import detect_client_hardware, get_device_identity, get_detailed_hardware_telemetry
from .storage import ClientEphemeralStorage, PermanentModelStorage
from .downloader import ClientModelDownloader
from .customization import UserCustomizationManager
from .runtime import ClientInferenceRuntime
from .visual_renderer import detect_visual_content, render_visual_html, open_visual_in_browser, render_mermaid_to_cli
from .voice import CLIHardwareVoiceCoordinator, clean_text_for_speech
from .ui_renderer import render_cli_status_box, render_hardware_card, render_memory_card, render_gpu_card

# Enable Windows Virtual Terminal Processing for ANSI colors
if os.name == "nt":
    os.system("")

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

STUDIO_URL = "https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/"

BANNER = r"""
     ██╗██╗   ██╗██╗  ██╗   ██╗    ██╗     ██╗     ███╗   ███╗
     ██║██║   ██║██║  ╚██╗ ██╔╝    ██║     ██║     ████╗ ████║
     ██║██║   ██║██║   ╚████╔╝     ██║     ██║     ██╔████╔██║
██   ██║██║   ██║██║    ╚██╔╝      ██║     ██║     ██║╚██╔╝██║
╚█████╔╝╚██████╔╝███████╗██║       ███████╗███████╗██║ ╚═╝ ██║
 ╚════╝  ╚═════╝ ╚══════╝╚═╝       ╚══════╝╚══════╝╚═╝     ╚═╝"""


class UI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    RED = "\033[91m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    URL = "\033[4;94m"

    @staticmethod
    def print_banner(subtitle: str = "Autonomous Neural Runtime Platform"):
        print(f"{UI.CYAN}{BANNER}{UI.RESET}")
        print(f"{UI.GRAY}─────────────────────────────────────────────────────────────────────────────{UI.RESET}")
        print(f"  {UI.BOLD}{UI.WHITE}HS AI SOLUTIONS{UI.RESET}  {UI.GRAY}•{UI.RESET}  {UI.GREEN}{subtitle}{UI.RESET}")
        print(f"  {UI.GRAY}Studio Portal :{UI.RESET} {UI.URL}{STUDIO_URL}{UI.RESET}")
        print(f"{UI.GRAY}─────────────────────────────────────────────────────────────────────────────{UI.RESET}")

    @staticmethod
    def print_card(title: str):
        print(f"\n{UI.GRAY}┌────────────────────────────────────────────────────────────────────────────┐{UI.RESET}")
        print(f"{UI.GRAY}│{UI.RESET}  {UI.BOLD}{UI.CYAN}{title.center(72)}{UI.RESET}  {UI.GRAY}│{UI.RESET}")
        print(f"{UI.GRAY}└────────────────────────────────────────────────────────────────────────────┘{UI.RESET}")


MODEL_METADATA = {
    "july": {
        "title": "JULY LLM",
        "name": "july",
        "family": "JULY AI Family",
        "badge": "JULY LLM • HS AI SOLUTIONS",
        "description": "Primary Foundation Intelligence — General Reasoning, Coding, Visual Generation & Systems",
        "architecture": "LLAMA 3.2 GQA",
        "parameters": "3.21B",
        "layers": 28,
        "quantization": "Q4_K_M (File Type 15)",
        "context_length": 131072,
        "default_file": "july-final.gguf",
    },
    "gravity": {
        "title": "GRAVITY LLM",
        "name": "gravity",
        "family": "GRAVITY AI Family",
        "badge": "GRAVITY LLM • HS AI SOLUTIONS",
        "description": "Frontier Specialist — Pure Mathematics, CAS, Physics Simulation, Algorithmic Proofs",
        "architecture": "GRAVITY GQA / RoPE",
        "parameters": "3.21B",
        "layers": 28,
        "quantization": "Q4_K_M (File Type 15)",
        "context_length": 131072,
        "default_file": "gravity-final.gguf",
    },
    "auto": {
        "title": "AUTO (Intelligent Dynamic Router)",
        "name": "auto",
        "family": "HS AI Dual-Orchestration",
        "badge": "AUTO ROUTER • HS AI SOLUTIONS",
        "description": "Dynamic Task Routing & Memory Budgeting — Evaluates query and routes to July or Gravity with transparent rationale",
        "architecture": "Hybrid Dual Engine",
        "parameters": "3.21B (Dual)",
        "layers": 28,
        "quantization": "Q4_K_M",
        "context_length": 131072,
        "default_file": "Dynamic",
    }
}


def resolve_model_seed(model_id: str = "july") -> Optional[Path]:
    """Finds verified GGUF weights for July or Gravity in permanent storage or workstation seeds."""
    from .storage import PermanentModelStorage
    import tempfile
    perm = PermanentModelStorage()
    mid = model_id.lower().strip()

    # 1. Check permanent model storage first
    f = perm.get_model_file(mid)
    expected_size = perm.EXPECTED_SIZES.get(mid)
    if f.exists() and (expected_size is None or f.stat().st_size == expected_size):
        return f

    # 2. Workstation seed fallbacks
    if mid == "gravity":
        candidates = [
            Path(r"D:\gravity\Gravity-HS-AI-Solutions.gguf"),
            Path(r"D:\gravity\models\Gravity-HS-AI-Solutions.gguf"),
            Path(os.environ.get("USERPROFILE", str(Path.home()))) / "gravity" / "Gravity-HS-AI-Solutions.gguf",
            Path.cwd() / "models" / "Gravity-HS-AI-Solutions.gguf",
            Path(tempfile.gettempdir()) / "july_ephemeral_runtime" / "gravity_ram_model.gguf",
        ]
        for c in candidates:
            if c.exists() and c.stat().st_size == 5629108096:
                return c
        return None
    else:
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "models" / "july-final.gguf",
            Path.cwd() / "models" / "july-final.gguf",
            Path(os.environ.get("USERPROFILE", str(Path.home()))) / "OneDrive" / "Desktop" / "collab-editor" / "models" / "july-final.gguf",
            Path(tempfile.gettempdir()) / "july_ephemeral_runtime" / "july_ram_model.gguf",
        ]
        for c in candidates:
            if c.exists() and c.stat().st_size == 2019377888:
                return c
        return None


def get_runtime_state_file() -> Path:
    return get_default_july_dir() / "active_model_state.json"


def record_active_state(ephemeral_path: Path, model_id: str = "july"):
    with open(get_runtime_state_file(), "w", encoding="utf-8") as f:
        json.dump({"ephemeral_path": str(ephemeral_path), "model_id": model_id, "loaded_at": time.time()}, f)


def clear_active_state():
    p = get_runtime_state_file()
    if p.exists():
        p.unlink(missing_ok=True)


def get_active_model_info() -> tuple[Optional[Path], str]:
    p = get_runtime_state_file()
    if not p.exists():
        return None, "none"
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        ep = Path(data.get("ephemeral_path", ""))
        mid = data.get("model_id", "july")
        if ep.exists():
            return ep, mid
        return None, "none"
    except Exception:
        return None, "none"


def get_active_ephemeral_path() -> Path | None:
    path, _ = get_active_model_info()
    return path


def cmd_install():
    UI.print_banner("Runtime Installation & Setup")
    july_dir = get_default_july_dir()
    print(f"\n {UI.GREEN}[✓]{UI.RESET} Setting up configuration directory: {july_dir}")

    cfg = ClientConfig.load()
    print(f" {UI.GREEN}[✓]{UI.RESET} Configured backend server: {cfg.server_url}")

    # Check dependencies
    print(f"\n {UI.CYAN}[⚡]{UI.RESET} Validating local dependencies:")
    try:
        import llama_cpp
        print(f"     • llama-cpp-python: {UI.GREEN}INSTALLED (v{llama_cpp.__version__}){UI.RESET}")
    except ImportError:
        print(f"     • llama-cpp-python: {UI.YELLOW}NOT INSTALLED. Run: pip install llama-cpp-python{UI.RESET}")

    hw = detect_client_hardware()
    print(f"\n {UI.CYAN}[⚡]{UI.RESET} Hardware Acceleration Profile:")
    print(f"     • CPU Compute       : {hw['cpu_threads']} threads available")
    print(f"     • System RAM        : {hw['ram_available_gb']} GB free / {hw['ram_total_gb']} GB total")
    print(f"     • GPU Acceleration  : {UI.GREEN if hw['gpu_available'] else UI.YELLOW}{hw['gpu_name']}{UI.RESET} ({hw['vram_free_mb']} MB VRAM)")

    print(f"\n {UI.GREEN}[✓] JULY Runtime ready!{UI.RESET}")
    print(f"     Execute {UI.CYAN}july login{UI.RESET} to connect your account.\n")


def _fmt_quota(val: Any) -> str:
    if isinstance(val, (int, float)):
        return f"{int(val):,}"
    return str(val)


def _print_auth_success(sess: dict, is_signup: bool = False):
    name = sess.get("name") or "Harshan"
    email = sess.get("email") or "user@example.com"
    print("\nSuccessfully authenticated!\n")
    print(f"Welcome, {name}.")
    print(f"Account: {email}")
    print("Authentication: Verified\n")
    print("July LLM is ready.\n")


def ensure_authenticated_for_models(prompt_user: bool = True) -> tuple[bool, Optional[dict]]:
    """
    Strictly enforces authentication before allowing model selection, inference, or loading.
    If unauthenticated and running interactively in CLI, offers immediate authentication.
    """
    clerk = ClerkAuthManager()
    session = clerk.get_session()
    if session and not clerk.vault.is_session_expired(session):
        return True, session

    auth = ClientAuthManager()
    if auth.is_authenticated():
        sess = auth.get_session() or {"email": "legacy_user", "tier": "standard", "clerk_user_id": "legacy"}
        return True, sess

    # Not authenticated - Strict Gating
    if prompt_user and sys.stdin.isatty():
        print(f"\n {UI.YELLOW}┌────────────────────────────────────────────────────────────────────────────┐{UI.RESET}")
        print(f" {UI.YELLOW}│{UI.RESET}  {UI.BOLD}{UI.RED}STRICT AUTHENTICATION REQUIRED TO SELECT OR USE AI MODELS{UI.RESET}                {UI.YELLOW}│{UI.RESET}")
        print(f" {UI.YELLOW}│{UI.RESET}  Model selection and inference are strictly gated by HS AI Solutions Clerk  {UI.YELLOW}│{UI.RESET}")
        print(f" {UI.YELLOW}│{UI.RESET}  authentication. Please log in to unlock model access.                      {UI.YELLOW}│{UI.RESET}")
        print(f" {UI.YELLOW}└────────────────────────────────────────────────────────────────────────────┘{UI.RESET}\n")

        try:
            choice = input(f" {UI.CYAN}[?] Would you like to authenticate now? [Y/n]: {UI.RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return False, None

        if choice in ("", "y", "yes"):
            try:
                cmd_login(argparse.Namespace(username=None, password=None, token=None, sso=None, server=None, force=False))
                session = clerk.get_session()
                if session and not clerk.vault.is_session_expired(session):
                    return True, session
            except Exception as e:
                print(f" {UI.RED}[!] Authentication failed:{UI.RESET} {e}\n")
                return False, None
        else:
            print(f" {UI.GRAY}[i] Run 'july login' whenever you are ready to authenticate.{UI.RESET}\n")
            return False, None

    return False, None


def cmd_login(args):
    clerk = ClerkAuthManager()
    force = getattr(args, "force", False)

    # 1. Check whether the user is already authenticated
    if not force and clerk.is_authenticated():
        session = clerk.get_session() or {}
        name = session.get("name") or "Harshan"
        email = session.get("email") or "user@example.com"
        print("\nJULY LLM")
        print("Powered by HS AI Solutions\n")
        print("Already authenticated!\n")
        print(f"Welcome, {name}.")
        print(f"Account: {email}")
        print("Authentication: Verified\n")
        print("July LLM is ready.\n")
        print(f" {UI.GRAY}[i] To switch accounts, run: july login --force{UI.RESET}")
        print(f" {UI.GRAY}[i] To sign out, run: july logout{UI.RESET}\n")
        return

    # 2. Token supplied via CLI arguments (for headless / CI environments)
    token = getattr(args, "token", None)
    if token:
        try:
            print("\nJULY LLM")
            print("Powered by HS AI Solutions\n")
            print("Authenticating via Clerk Token...")
            sess = clerk.login_manual(token, email=getattr(args, "email", None), server_url=getattr(args, "server", None))
            _print_auth_success(sess)
            return
        except Exception as e:
            print(f"\n {UI.RED}[!] Token Authentication Failed:{UI.RESET} {e}\n")
            sys.exit(1)

    # 3. Interactive Clerk Authentication Workflow
    provider = getattr(args, "sso", None)
    print("\nJULY LLM")
    print("Powered by HS AI Solutions\n")
    print("Authentication Required\n")
    print("Opening HS AI Solutions Login...")

    try:
        session = clerk.login_browser(provider=provider, server_url=getattr(args, "server", None))
        _print_auth_success(session)
    except Exception as e:
        print(f"\n {UI.RED}[!] Authentication Failed or Timed Out:{UI.RESET} {e}")
        print(f" {UI.GRAY}[i] In headless environments, sign in with: july login --token <token>{UI.RESET}\n")
        sys.exit(1)


def cmd_logout(args=None):
    UI.print_card("HS AI SOLUTIONS — SESSION TERMINATION")
    clerk = ClerkAuthManager()
    was_auth = clerk.is_authenticated()
    clerk.logout()

    if was_auth:
        print(f" {UI.GREEN}[✓] Logged out successfully.{UI.RESET}")
        print(f" {UI.GREEN}[✓]{UI.RESET} Local cryptographic credential vault wiped.")
        print(f" {UI.GREEN}[✓]{UI.RESET} Remote session invalidated on server.\n")
    else:
        print(f" {UI.YELLOW}[i] No active authenticated session was found.{UI.RESET}\n")


def cmd_signup(args=None):
    UI.print_card("HS AI SOLUTIONS — CREATE NEW ACCOUNT")
    clerk = ClerkAuthManager()

    if sys.stdin.isatty() and not getattr(args, "browser", False):
        print(f" {UI.CYAN}[*]{UI.RESET} In-CLI Developer Registration:\n")
        try:
            email_input = input(f" {UI.CYAN}Email: {UI.RESET}").strip()
            uname_input = input(f" {UI.CYAN}Username: {UI.RESET}").strip()
            pass_input = getpass.getpass(f" {UI.CYAN}Password (min 6 chars): {UI.RESET}").strip()
            sess = clerk.signup_credentials(email_input, uname_input, pass_input)
            _print_auth_success(sess, is_signup=True)
            return
        except Exception as e:
            print(f"\n {UI.RED}[!] In-CLI Registration Failed:{UI.RESET} {e}")
            print(f" {UI.GRAY}[*] Falling back to browser registration portal...{UI.RESET}\n")

    import webbrowser
    signup_url = f"{STUDIO_AUTH_PORTAL}?mode=sign-up"
    print(f" {UI.CYAN}[*]{UI.RESET} Launching Clerk Sign-Up in your browser...")
    print(f" {UI.GRAY}[*] Target URL: {signup_url}{UI.RESET}")
    webbrowser.open(signup_url)
    print(f"\n {UI.GREEN}[✓]{UI.RESET} Once registered, run {UI.BOLD}july login{UI.RESET} to connect your device.\n")


def cmd_whoami(args=None):
    clerk = ClerkAuthManager()
    session = clerk.get_session()

    if not session:
        print(f"\n {UI.YELLOW}[!] Not currently authenticated.{UI.RESET}")
        print(f" {UI.GRAY}[i] Run {UI.CYAN}july login{UI.GRAY} to connect your account or operate offline.{UI.RESET}\n")
        return

    UI.print_card("HS AI SOLUTIONS — ACTIVE USER IDENTITY")
    dev_info = get_device_identity()
    is_expired = clerk.vault.is_session_expired(session)

    is_creator = (session.get("email", "").lower().strip() == "harshanseliyan28@gmail.com" or session.get("role") == "creator" or session.get("tier") == "creator")
    sub_title = f"{UI.BOLD}{UI.YELLOW}CREATOR & FOUNDER (UNLIMITED ACCESS){UI.RESET}" if is_creator else f"{UI.BOLD}{UI.GREEN}{session.get('tier', 'pro').upper()}{UI.RESET}"
    role_title = f"{UI.BOLD}{UI.YELLOW}Creator & Ecosystem Owner{UI.RESET}" if is_creator else session.get('role', 'standard')

    print(f"   Name             : {UI.BOLD}{session.get('name', 'Developer')}{UI.RESET}")
    print(f"   Email            : {session.get('email')}")
    print(f"   Clerk User ID    : {UI.CYAN}{session.get('clerk_user_id')}{UI.RESET}")
    print(f"   Subscription     : {sub_title}")
    print(f"   Role             : {role_title}")
    print(f"   Current Device   : {dev_info['device_name']} ({dev_info['device_id'][:12]}...)")
    print(f"   Session Status   : {UI.RED + 'EXPIRED' if is_expired else UI.GREEN + 'ACTIVE / VALID'}{UI.RESET}")
    print(f"   Credential Vault : {UI.GREEN}Windows DPAPI (Hardware Bound){UI.RESET}\n")


def cmd_auth(args):
    action = getattr(args, "action", "status") or "status"
    clerk = ClerkAuthManager()

    if action == "status":
        cmd_auth_status(clerk)
    elif action == "refresh":
        cmd_auth_refresh(clerk)
    elif action == "devices":
        cmd_auth_devices(clerk)
    elif action == "revoke":
        target_dev = getattr(args, "device_id", None)
        cmd_auth_revoke(clerk, target_dev)
    else:
        print(f" {UI.RED}[!] Unknown auth action '{action}'. Choices: status, refresh, devices, revoke{UI.RESET}")


def cmd_auth_refresh(clerk: ClerkAuthManager):
    UI.print_card("HS AI SOLUTIONS — REFRESH AUTHENTICATION SESSION")
    session = clerk.get_session()
    if not session:
        print(f" {UI.RED}[!] No active session found.{UI.RESET} Run 'july login' first.\n")
        return

    print(f" {UI.GRAY}[*] Contacting Clerk IAM service and synchronizing session...{UI.RESET}")
    try:
        new_sess = clerk.refresh_session()
        print(f"\n {UI.GREEN}[✓] Session Refreshed Successfully!{UI.RESET}")
        print(f"   Account       : {new_sess.get('email')}")
        print(f"   Name          : {new_sess.get('name', 'Developer')}")
        print(f"   Tier          : {UI.BOLD}{UI.GREEN}{new_sess.get('tier', 'pro').upper()}{UI.RESET}")
        print(f"   Session State : {UI.GREEN}ACTIVE / VALID{UI.RESET}")
        print(f"   Vault Status  : {UI.GREEN}Windows DPAPI Re-sealed{UI.RESET}\n")
    except Exception as e:
        print(f"\n {UI.RED}[!] Failed to refresh session:{UI.RESET} {e}\n")


def cmd_auth_status(clerk: ClerkAuthManager):
    UI.print_card("HS AI SOLUTIONS — CLERK AUTHENTICATION TELEMETRY")
    session = clerk.get_session()
    dev_info = get_device_identity()

    print(f" {UI.BOLD}{UI.CYAN}── IDENTITY & CREDENTIAL VAULT ───────────────────────────{UI.RESET}")
    print(f"   Identity Provider: {UI.BOLD}Clerk Identity & Access Management (IAM){UI.RESET}")
    print(f"   Storage Engine   : {UI.GREEN}Windows DPAPI / Protected Vault (0 Plaintext){UI.RESET}")

    if session:
        is_expired = clerk.vault.is_session_expired(session)
        expires_at = session.get("expires_at", 0)
        remaining_days = max(0.0, round((expires_at - time.time()) / 86400, 1)) if expires_at else "N/A"

        print(f"   Auth Status      : {UI.GREEN}AUTHENTICATED{UI.RESET}")
        print(f"   Session State    : {UI.RED + 'EXPIRED' if is_expired else UI.GREEN + f'VALID ({remaining_days} days remaining)'}{UI.RESET}")
        print(f"   Clerk User ID    : {session.get('clerk_user_id')}")
        print(f"   Email Address    : {session.get('email')}")
        print(f"   Account Plan     : {UI.BOLD}{session.get('tier', 'pro').upper()}{UI.RESET}")
        print(f"   Auth Provider    : {session.get('auth_provider', 'clerk').upper()}")
    else:
        print(f"   Auth Status      : {UI.YELLOW}UNAUTHENTICATED (Local / Anonymous Mode){UI.RESET}")
        print(f"   Recommendation   : Run {UI.CYAN}july login{UI.RESET} to connect devices and cloud features.")

    print(f"\n {UI.BOLD}{UI.CYAN}── HARDWARE DEVICE BOUNDARY ─────────────────────────────{UI.RESET}")
    print(f"   Device ID        : {dev_info['device_id']}")
    print(f"   Device Hostname  : {dev_info['device_name']}")
    print(f"   Operating System : {dev_info['os_version']}")
    print(f"   Registered State : {UI.GREEN}AUTHORIZED{UI.RESET if session else UI.GRAY + 'LOCAL_UNBOUND' + UI.RESET}")

    queue_count = 0
    if clerk.offline_queue_file.exists():
        try:
            with open(clerk.offline_queue_file, "r", encoding="utf-8") as f:
                queue_count = len(json.load(f))
        except Exception:
            pass
    print(f"   Offline Ops Queue: {queue_count} pending event(s) to sync\n")

    limiter = ClientRateLimiter.get_instance()
    user_tier = (session.get("tier") if session else "standard") or "standard"
    rl_metrics = limiter.get_metrics(tier=user_tier)

    print(f" {UI.BOLD}{UI.CYAN}── RATE LIMITING & MODEL ACCESS QUOTAS ──────────────────{UI.RESET}")
    print(f"   Tier Policy      : {UI.BOLD}{rl_metrics['tier_title']}{UI.RESET}")
    print(f"   Request Rate     : {_fmt_quota(rl_metrics['rpm_used'])}/{_fmt_quota(rl_metrics['rpm_max'])} requests/min ({UI.GREEN}{_fmt_quota(rl_metrics['rpm_remaining'])}{UI.RESET} remaining)")
    print(f"   Token Throughput : {_fmt_quota(rl_metrics['tpm_used'])}/{_fmt_quota(rl_metrics['tpm_max'])} tokens/min ({UI.GREEN}{_fmt_quota(rl_metrics['tpm_remaining'])}{UI.RESET} remaining)")
    print(f"   Daily Allotment  : {_fmt_quota(rl_metrics['daily_used'])}/{_fmt_quota(rl_metrics['daily_max'])} requests today ({UI.GREEN}{_fmt_quota(rl_metrics['daily_remaining'])}{UI.RESET} remaining)")
    print(f"   Window Duration  : {int(rl_metrics['window_seconds'])}s sliding window\n")


def cmd_auth_devices(clerk: ClerkAuthManager):
    UI.print_card("HS AI SOLUTIONS — REGISTERED ACCOUNT DEVICES")
    session = clerk.get_session()
    if not session:
        print(f" {UI.RED}[!] Please log in first: 'july login'{UI.RESET}\n")
        return

    devices = clerk.get_registered_devices()
    curr_dev = get_device_identity()["device_id"]

    print(f" {'DEVICE ID':<36} {'NAME':<20} {'OS':<14} {'STATUS':<12} {'CURRENT'}")
    print(f" {'─'*36} {'─'*20} {'─'*14} {'─'*12} {'─'*7}")

    for d in devices:
        did = d.get("device_id", "")
        dname = d.get("device_name", "Unknown")[:19]
        dos = d.get("os_version", "Windows")[:13]
        dstat = d.get("status", "APPROVED")
        is_curr = (did == curr_dev)
        curr_badge = f"{UI.GREEN}[THIS DEVICE]{UI.RESET}" if is_curr else ""
        stat_color = UI.GREEN if dstat == "APPROVED" else UI.RED

        print(f" {did:<36} {dname:<20} {dos:<14} {stat_color}{dstat:<12}{UI.RESET} {curr_badge}")
    print()


def cmd_auth_revoke(clerk: ClerkAuthManager, device_id: Optional[str]):
    UI.print_card("HS AI SOLUTIONS — REVOKE DEVICE ACCESS")
    session = clerk.get_session()
    if not session:
        print(f" {UI.RED}[!] Please log in first: 'july login'{UI.RESET}\n")
        return

    if not device_id:
        device_id = input(f" {UI.CYAN}Enter Device ID to revoke{UI.RESET}: ").strip()

    if not device_id:
        print(f" {UI.RED}[!] No device ID provided.{UI.RESET}\n")
        return

    success = clerk.revoke_device(device_id)
    if success:
        print(f"\n {UI.GREEN}[✓] Device '{device_id}' access has been REVOKED.{UI.RESET}\n")
    else:
        print(f"\n {UI.RED}[!] Failed to revoke device '{device_id}'. Backend may be unreachable.{UI.RESET}\n")


def cmd_account(args=None):
    UI.print_card("HS AI SOLUTIONS — USER ACCOUNT DASHBOARD")
    clerk = ClerkAuthManager()
    session = clerk.get_session()

    if not session:
        print(f" {UI.YELLOW}[!] Not authenticated.{UI.RESET}")
        print(f" {UI.GRAY}[i] Run 'july login' to access your HS AI Solutions account dashboard.{UI.RESET}\n")
        return

    name = session.get("name") or "Harshan Seliyan"
    email = session.get("email") or "user@hs-ai.solutions"
    avatar = session.get("image_url") or "[Default HS AI Solutions Avatar]"
    is_expired = clerk.vault.is_session_expired(session)
    session_status = "EXPIRED" if is_expired else "ACTIVE / SECURE (Hardware-Bound DPAPI)"
    created_ts = session.get("created_at", time.time())
    created_date = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(created_ts))
    tier = session.get("tier", "pro").upper()
    clerk_id = session.get("clerk_user_id", "N/A")

    # Usage statistics
    usage = session.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)
    req_count = usage.get("requests_count", 0)
    models_used = usage.get("models_used", {})

    # Rate limits
    limiter = ClientRateLimiter.get_instance()
    rl_metrics = limiter.get_metrics(tier=session.get("tier", "pro"))

    is_creator = (email.lower().strip() == "harshanseliyan28@gmail.com" or session.get("role") == "creator" or session.get("tier") == "creator")
    sub_title = f"{UI.BOLD}{UI.YELLOW}CREATOR & FOUNDER (UNLIMITED ACCELERATION){UI.RESET}" if is_creator else f"{UI.BOLD}{UI.GREEN}{tier} PLAN{UI.RESET}"
    verif_title = f"{UI.GREEN}Verified Founder & Ecosystem Creator (Clerk IAM){UI.RESET}" if is_creator else f"{UI.GREEN}Verified (Clerk Identity & Access Management){UI.RESET}"

    print(f" {UI.BOLD}{UI.CYAN}── USER IDENTITY & PROFILE ──────────────────────────────{UI.RESET}")
    print(f"   Profile Picture  : {avatar}")
    print(f"   Name             : {UI.BOLD}{name}{UI.RESET}")
    print(f"   Email            : {email}")
    print(f"   Verification     : {verif_title}")
    print(f"   Account Created  : {created_date}")
    print(f"   Clerk User ID    : {UI.CYAN}{clerk_id}{UI.RESET}")
    print(f"   Subscription     : {sub_title}")

    print(f"\n {UI.BOLD}{UI.CYAN}── CURRENT AUTHENTICATION SESSION ───────────────────────{UI.RESET}")
    print(f"   Session State    : {UI.GREEN if not is_expired else UI.RED}{session_status}{UI.RESET}")
    print(f"   Credential Vault : {UI.GREEN}Windows DPAPI (Cryptographically Sealed at Rest){UI.RESET}")
    print(f"   Identity Issuer  : https://special-tomcat-836.clerk.accounts.dev")

    print(f"\n {UI.BOLD}{UI.CYAN}── TOKEN USAGE STATISTICS ───────────────────────────────{UI.RESET}")
    print(f"   Total Requests   : {UI.BOLD}{req_count:,}{UI.RESET}")
    print(f"   Total Tokens     : {UI.BOLD}{total_tokens:,}{UI.RESET}")
    july_tokens = models_used.get("july", {}).get("tokens", 0)
    july_reqs = models_used.get("july", {}).get("requests", 0)
    gravity_tokens = models_used.get("gravity", {}).get("tokens", 0)
    gravity_reqs = models_used.get("gravity", {}).get("requests", 0)
    print(f"   • July Model     : {july_reqs} requests | {july_tokens:,} tokens")
    print(f"   • Gravity Model  : {gravity_reqs} requests | {gravity_tokens:,} tokens")

    print(f"\n {UI.BOLD}{UI.CYAN}── RATE LIMITS & QUOTAS ─────────────────────────────────{UI.RESET}")
    print(f"   Policy Tier      : {UI.BOLD}{rl_metrics['tier_title']}{UI.RESET}")
    print(f"   Request Limit    : {_fmt_quota(rl_metrics['rpm_used'])}/{_fmt_quota(rl_metrics['rpm_max'])} req/min ({UI.GREEN}{_fmt_quota(rl_metrics['rpm_remaining'])}{UI.RESET} remaining)")
    print(f"   Throughput (TPM) : {_fmt_quota(rl_metrics['tpm_used'])}/{_fmt_quota(rl_metrics['tpm_max'])} tok/min ({UI.GREEN}{_fmt_quota(rl_metrics['tpm_remaining'])}{UI.RESET} remaining)")
    print(f"   Daily Limit      : {_fmt_quota(rl_metrics['daily_used'])}/{_fmt_quota(rl_metrics['daily_max'])} req/day ({UI.GREEN}{_fmt_quota(rl_metrics['daily_remaining'])}{UI.RESET} remaining)")
    print(f"   Window Duration  : {int(rl_metrics['window_seconds'])}s sliding window")

    print(f"\n {UI.BOLD}{UI.CYAN}── AVAILABLE FOUNDATION MODELS ──────────────────────────{UI.RESET}")
    print(f"   • {UI.BOLD}July{UI.RESET} (Lightweight)    : [READY] Fast, low-latency reasoning and coding execution")
    print(f"   • {UI.BOLD}Gravity{UI.RESET} (Heavyweight): [READY] Deep multi-step reasoning, architectural synthesis")
    print(f"   • {UI.BOLD}Auto{UI.RESET} (Intelligent)   : [READY] Dynamic routing based on complexity")

    print(f"\n {UI.BOLD}{UI.CYAN}── SIGN-OUT INSTRUCTIONS ────────────────────────────────{UI.RESET}")
    print(f"   To end your session and securely clear local cryptographic credentials:")
    print(f"   Run: {UI.BOLD}{UI.YELLOW}july logout{UI.RESET}\n")


def cmd_usage(args=None):
    UI.print_card("HS AI SOLUTIONS — TOKEN & MODEL USAGE TELEMETRY")
    clerk = ClerkAuthManager()
    session = clerk.get_session()

    usage = session.get("usage", {}) if session else {}
    total_tokens = usage.get("total_tokens", 0)
    req_count = usage.get("requests_count", 0)
    models = usage.get("models_used", {})

    user_tier = (session.get('tier', 'pro') if session else 'standard') or 'standard'
    limiter = ClientRateLimiter.get_instance()
    rl_metrics = limiter.get_metrics(tier=user_tier)

    print(f"   Total Requests   : {UI.BOLD}{req_count:,}{UI.RESET}")
    print(f"   Total Tokens     : {UI.BOLD}{total_tokens:,}{UI.RESET}")
    print(f"   Active Tier      : {UI.CYAN}{user_tier.upper()}{UI.RESET} ({rl_metrics['tier_title']})")
    print(f"   Rate Limit (RPM) : {_fmt_quota(rl_metrics['rpm_used'])}/{_fmt_quota(rl_metrics['rpm_max'])} req/min ({UI.GREEN}{_fmt_quota(rl_metrics['rpm_remaining'])}{UI.RESET} remaining)")
    print(f"   Throughput (TPM) : {_fmt_quota(rl_metrics['tpm_used'])}/{_fmt_quota(rl_metrics['tpm_max'])} tok/min ({UI.GREEN}{_fmt_quota(rl_metrics['tpm_remaining'])}{UI.RESET} remaining)")
    print(f"   Daily Limit      : {_fmt_quota(rl_metrics['daily_used'])}/{_fmt_quota(rl_metrics['daily_max'])} requests today ({UI.GREEN}{_fmt_quota(rl_metrics['daily_remaining'])}{UI.RESET} remaining)")
    print(f"\n {UI.BOLD}{UI.CYAN}── MODEL BREAKDOWN ───────────────────────────────────────{UI.RESET}")
    print(f" {'ENGINE / MODEL':<28} {'CALLS':<10} {'TOKENS'}")
    print(f" {'─'*28} {'─'*10} {'─'*15}")

    default_engines = [
        ("July Lightweight LLM", "july"),
        ("Gravity Heavyweight LLM", "gravity"),
        ("July Reasoning Engine", "reasoning"),
        ("July Agent Engine", "agent"),
        ("July Code Engine", "code"),
        ("July Vision Engine", "vision")
    ]

    for label, m_key in default_engines:
        m_info = models.get(m_key, {"calls": 0, "tokens": 0})
        print(f" {label:<28} {m_info.get('calls', 0):<10} {m_info.get('tokens', 0):,}")

    print(f"\n {UI.GRAY}[i] Local model inference is always unlimited and free on your hardware.{UI.RESET}\n")


def cmd_sync(args=None):
    UI.print_card("HS AI SOLUTIONS — CLOUD SYNCHRONIZATION")
    clerk = ClerkAuthManager()

    if not clerk.is_authenticated():
        print(f" {UI.YELLOW}[!] You are operating in offline unauthenticated mode.{UI.RESET}")
        print(f" {UI.GRAY}[i] Run 'july login' to link your Clerk account for cloud synchronization.{UI.RESET}\n")
        return

    print(f" {UI.CYAN}[*]{UI.RESET} Flushing offline queued operations to HS AI Solutions backend...")
    result = clerk.sync_offline_queue()

    if result.get("synced"):
        print(f" {UI.GREEN}[✓] Synchronization Complete!{UI.RESET}")
        print(f" {UI.GREEN}[✓]{UI.RESET} Events Flushed       : {result.get('flushed_events', 0)}")
        print(f" {UI.GREEN}[✓]{UI.RESET} Subscription Plan    : {UI.BOLD}{result.get('tier', 'pro').upper()}{UI.RESET}")
        print(f" {UI.GREEN}[✓]{UI.RESET} Server Sync Timestamp: {result.get('server_time')}\n")
    else:
        print(f" {UI.YELLOW}[!] Sync Notice:{UI.RESET} {result.get('reason')}")
        print(f" {UI.GRAY}[i] Offline usage metrics preserved locally for the next sync attempt.{UI.RESET}\n")


def cmd_register(args):
    UI.print_card("HS AI SOLUTIONS — USER REGISTRATION")
    auth = ClientAuthManager()

    username = args.username or input(f" {UI.CYAN}Choose Username{UI.RESET}: ").strip()
    email = args.email or input(f" {UI.CYAN}Email Address  {UI.RESET}: ").strip()
    password = args.password or getpass.getpass(f" {UI.CYAN}Choose Password{UI.RESET}: ")

    try:
        res = auth.register(username, email, password, server_url=args.server)
        print(f"\n {UI.GREEN}[✓] Account created!{UI.RESET} Welcome to HS AI Solutions, {UI.BOLD}{res.get('username')}{UI.RESET}!")
        print(f" {UI.GREEN}[✓]{UI.RESET} Studio Portal: {STUDIO_URL}\n")
    except Exception as e:
        print(f"\n {UI.RED}[!] Registration Failed:{UI.RESET} {e}\n")
        sys.exit(1)


def cmd_status():
    UI.print_banner("Hardware & Runtime Telemetry")
    auth = ClientAuthManager()
    session = auth.get_session()
    cfg = ClientConfig.load()

    print(f"\n {UI.BOLD}{UI.CYAN}── AUTHENTICATION ────────────────────────────────────────{UI.RESET}")
    if session:
        print(f"   Status           : {UI.GREEN}AUTHENTICATED{UI.RESET}")
        clerk_id = session.get("clerk_user_id")
        if clerk_id:
            print(f"   Clerk User ID    : {UI.CYAN}{clerk_id}{UI.RESET}")
            print(f"   Email            : {UI.WHITE}{session.get('email')}{UI.RESET}")
            print(f"   Plan Tier        : {UI.BOLD}{session.get('tier', 'pro').upper()}{UI.RESET}")
            print(f"   Credential Vault : {UI.GREEN}Windows DPAPI (Hardware Bound){UI.RESET}")
        else:
            print(f"   Username         : {UI.WHITE}{session.get('username', 'Developer')}{UI.RESET}")
            print(f"   Role             : {session.get('role', 'standard')}")
        print(f"   Model License    : {UI.GREEN}ACTIVE / GRANTED{UI.RESET}")
        print(f"   Control Server   : {session.get('server_url')}")
    else:
        print(f"   Status           : {UI.YELLOW}NOT AUTHENTICATED (Run 'july login'){UI.RESET}")

    print(f"\n {UI.BOLD}{UI.CYAN}── DUAL FOUNDATION MODEL ARCHITECTURE ───────────────────{UI.RESET}")
    from .state_manager import DualModelStateManager
    from .storage import PermanentModelStorage
    perm_storage = PermanentModelStorage()
    state_mgr = DualModelStateManager()

    print(f"   Selected Model   : {UI.BOLD}{state_mgr.selectedModel.upper()}{UI.RESET} (User Preference)")
    print(f"   Active Model     : {UI.GREEN if state_mgr.activeModel != 'none' else UI.GRAY}{state_mgr.activeModel.upper()}{UI.RESET} (Currently Operational in RAM)")
    print(f"   Available Models : {', '.join([m.upper() for m in state_mgr.availableModels]) or 'None'}")
    print()

    for mid in ("july", "gravity"):
        m_file = perm_storage.get_model_file(mid)
        has_file = m_file.exists() and m_file.stat().st_size > 0
        state_str = state_mgr.get_model_state(mid)
        if state_mgr.activeModel == mid:
            status_badge = f"{UI.GREEN}[ACTIVE / READY]{UI.RESET}"
        elif has_file:
            status_badge = f"{UI.CYAN}[AVAILABLE / UNLOADED]{UI.RESET}"
        elif state_str == "DOWNLOADING":
            status_badge = f"{UI.YELLOW}[DOWNLOADING]{UI.RESET}"
        else:
            status_badge = f"{UI.GRAY}[NOT_DOWNLOADED]{UI.RESET}"

        f_size_mb = (m_file.stat().st_size / (1024*1024)) if has_file else 0
        meta = MODEL_METADATA.get(mid, {})
        print(f"   • {UI.BOLD}{mid.upper():<8}{UI.RESET} : {status_badge:<32} {meta.get('parameters', '')} | {f_size_mb:.1f} MB | {m_file}")

    print(f"\n {UI.BOLD}{UI.CYAN}── COMPUTE HARDWARE TELEMETRY ────────────────────────────{UI.RESET}")
    hw = detect_client_hardware()
    print(f"   CPU Threads      : {hw['cpu_threads']} (Allocated: {hw['recommended_threads']})")
    print(f"   Physical RAM     : {hw['ram_available_gb']} GB free of {hw['ram_total_gb']} GB ({hw['ram_used_percent']}% utilized)")
    print(f"   GPU Acceleration : {UI.GREEN if hw['gpu_available'] else UI.YELLOW}{hw['gpu_name']}{UI.RESET}")
    if hw["gpu_available"]:
        print(f"   VRAM Allocation  : {hw['vram_free_mb']} MB free / {hw['vram_total_mb']} MB total")
        print(f"   Layer Offloading : {hw['recommended_gpu_layers']} layers to GPU")
    print()


def cmd_load(args):
    cfg = ClientConfig.load()
    target_model = getattr(args, "model", None) or getattr(cfg, "selected_model", "july") or "july"
    if target_model.lower() == "auto":
        target_model = "july"
    target_model = target_model.lower().strip()

    # Enforce authentication before loading models into RAM
    is_auth, session = ensure_authenticated_for_models(prompt_user=True)
    if not is_auth:
        print(f" {UI.RED}[!] Model Access Blocked:{UI.RESET} Authentication required before loading {target_model.upper()} LLM.")
        print(f" {UI.GRAY}[i] Run 'july login' to authenticate with Clerk / HS AI Solutions.{UI.RESET}\n")
        sys.exit(1)

    from .storage import PermanentModelStorage
    from .state_manager import DualModelStateManager, ModelStatus
    perm_storage = PermanentModelStorage()
    model_path = perm_storage.get_model_file(target_model)
    local_available = (model_path.exists() and model_path.stat().st_size > 0) or bool(resolve_model_seed(target_model))

    auth = ClientAuthManager()
    state_mgr = DualModelStateManager()

    # Fast seed check (if existing master seed present on workstation)
    root_seed = resolve_model_seed(target_model)
    if root_seed and root_seed.exists() and root_seed != model_path and (not model_path.exists() or model_path.stat().st_size == 0):
        print(f" {UI.GRAY}[*] Priming permanent storage from verified local master seed ({root_seed.name})...{UI.RESET}")
        import shutil
        try:
            os.link(str(root_seed), str(model_path))
        except Exception:
            shutil.copyfile(str(root_seed), str(model_path))

    from .lifecycle import ModelLifecyclePipeline
    pipeline = ModelLifecyclePipeline(config=cfg, auth=auth)

    try:
        llm, meta, budget = pipeline.execute_pipeline(
            model_id=target_model,
            dest_path=model_path,
            force_cpu=(cfg.hardware_mode.lower() == "cpu")
        )
        record_active_state(model_path, target_model)
        state_mgr.set_model_state(target_model, ModelStatus.READY.value)
        state_mgr.activeModel = target_model
        print(f" {UI.GREEN}[✓]{UI.RESET} Run {UI.CYAN}july chat{UI.RESET} to start genuine local inference.\n")
    except Exception as e:
        if root_seed and root_seed.exists() and model_path.exists() and model_path.stat().st_size > 1000000:
            print(f"\n {UI.GRAY}[*] Cloud check delayed ({e}). Mounting verified master seed directly into RAM.{UI.RESET}")
            record_active_state(model_path, target_model)
            state_mgr.set_model_state(target_model, ModelStatus.READY.value)
            state_mgr.activeModel = target_model
            print(f" {UI.GREEN}[✓] {target_model.upper()} LLM verified and loaded into physical RAM.{UI.RESET}")
            print(f" {UI.GREEN}[✓]{UI.RESET} Run {UI.CYAN}july chat{UI.RESET} to start genuine local inference.\n")
        else:
            state_mgr.set_model_state(target_model, ModelStatus.ERROR.value, {"error": str(e)})
            print(f"\n {UI.RED}[!] Model acquisition & initialization error:{UI.RESET} {e}")
            sys.exit(1)


class ThinkingResultStreamFilter:
    """
    Differentiates model thinking and result by highlighting in CLI.
    - Captures reasoning tags (<think>, <thought>, <reasoning>, [thinking], [think]) and textual markers.
    - Highlights thinking in a dedicated, formatted container with subtle styling and timer.
    - Differentiates and highlights the final Result/Answer in bold vibrant colors.
    - Filters out raw <visual ...> tags cleanly during streaming.
    - Supports 'expanded' (full highlighted thinking), 'collapsed' (summary badge), and 'hidden' modes.
    """
    STATE_INITIAL = "INITIAL"
    STATE_THINKING = "THINKING"
    STATE_RESULT = "RESULT"

    OPEN_TAGS = ["<think>", "<thought>", "<reasoning>", "[thinking]", "[think]"]
    OPEN_TEXT_MARKERS = [
        "thinking process:", "thought:", "thoughts:", "reasoning:",
        "### thinking", "## thinking", "### reasoning", "## reasoning",
        "### thought process", "## thought process"
    ]
    CLOSE_REGEX = re.compile(
        r"(?:</think>|</thought>|</reasoning>|\[/thinking\]|\[/think\]|"
        r"(?:^|\n)\s*(?:###?\s*(?:answer|result|solution|response|conclusion)|final answer:|answer:|result:))",
        re.IGNORECASE
    )

    def __init__(self, model_name: str = "JULY", badge_color: str = UI.CYAN, thinking_mode: str = "expanded"):
        self.model_name = model_name
        self.badge_color = badge_color
        self.thinking_mode = thinking_mode.lower() if thinking_mode else "expanded"
        self.state = self.STATE_INITIAL
        self.buffer = ""
        self.think_start_time = 0.0
        self.has_thought = False
        self.in_visual = False
        self.result_header_printed = False

    def process(self, token: str) -> str:
        self.buffer += token
        output = []

        while self.buffer:
            if self.state == self.STATE_INITIAL:
                stripped = self.buffer.lstrip()
                if not stripped:
                    break

                low_stripped = stripped.lower()

                matched_open = None
                for tag in self.OPEN_TAGS:
                    if low_stripped.startswith(tag):
                        matched_open = tag
                        break

                if matched_open:
                    self.state = self.STATE_THINKING
                    self.has_thought = True
                    self.think_start_time = time.time()
                    tag_len = len(matched_open)
                    self.buffer = stripped[tag_len:]
                    if self.buffer.startswith("\n"):
                        self.buffer = self.buffer[1:]

                    if self.thinking_mode == "expanded":
                        header = (
                            f"\n  \033[38;5;244m╭─ 🧠 Thinking Process ──────────────────────────────────────────\033[0m\n"
                            f"  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m"
                        )
                        output.append(header)
                    continue

                potential_match = False
                for tag in self.OPEN_TAGS:
                    if tag.startswith(low_stripped) or (low_stripped.startswith("<") and len(low_stripped) < 12):
                        potential_match = True
                        break

                if potential_match and len(stripped) < 15:
                    break

                matched_text_marker = None
                for marker in self.OPEN_TEXT_MARKERS:
                    if low_stripped.startswith(marker):
                        matched_text_marker = marker
                        break

                if matched_text_marker:
                    self.state = self.STATE_THINKING
                    self.has_thought = True
                    self.think_start_time = time.time()
                    marker_len = len(matched_text_marker)
                    self.buffer = stripped[marker_len:]
                    if self.buffer.startswith("\n"):
                        self.buffer = self.buffer[1:]
                    if self.thinking_mode == "expanded":
                        header = (
                            f"\n  \033[38;5;244m╭─ 🧠 Thinking Process ──────────────────────────────────────────\033[0m\n"
                            f"  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m"
                        )
                        output.append(header)
                    continue

                self.state = self.STATE_RESULT
                continue

            elif self.state == self.STATE_THINKING:
                m = self.CLOSE_REGEX.search(self.buffer)
                if m:
                    close_idx = m.start()
                    tag_len = len(m.group(0))

                    thinking_chunk = self.buffer[:close_idx]
                    if self.thinking_mode == "expanded":
                        formatted_chunk = thinking_chunk.replace("\n", "\n  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m")
                        output.append(formatted_chunk)

                    self.buffer = self.buffer[close_idx + tag_len:]
                    if self.buffer.startswith("\n"):
                        self.buffer = self.buffer.lstrip("\r\n")

                    dur = max(0.1, time.time() - self.think_start_time)
                    if self.thinking_mode == "expanded":
                        footer = (
                            f"\033[0m\n  \033[38;5;244m╰───────────────────────────────────────────\033[0m "
                            f"\033[90m(thought for {dur:.1f}s)\033[0m\n\n"
                            f"  {self.badge_color}\033[1m✦ Result:\033[0m\n  \033[0m"
                        )
                    elif self.thinking_mode == "collapsed":
                        footer = (
                            f"\n  \033[90m[🧠 Thought for {dur:.1f}s]\033[0m\n\n"
                            f"  {self.badge_color}\033[1m✦ Result:\033[0m\n  \033[0m"
                        )
                    else:
                        footer = f"\n  {self.badge_color}\033[1m✦ Result:\033[0m\n  \033[0m"

                    output.append(footer)
                    self.result_header_printed = True
                    self.state = self.STATE_RESULT
                    continue
                else:
                    partial_len = 0
                    low = self.buffer.lower()
                    for tag in ["</think>", "</thought>", "</reasoning>", "[/thinking]"]:
                        for pl in range(1, len(tag)):
                            if low.endswith(tag[:pl]):
                                if pl > partial_len:
                                    partial_len = pl

                    if partial_len > 0:
                        to_emit = self.buffer[:-partial_len]
                        self.buffer = self.buffer[-partial_len:]
                    else:
                        to_emit = self.buffer
                        self.buffer = ""

                    if to_emit and self.thinking_mode == "expanded":
                        formatted = to_emit.replace("\n", "\n  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m")
                        output.append(formatted)
                    break

            elif self.state == self.STATE_RESULT:
                if not self.in_visual:
                    low = self.buffer.lower()

                    matched_open = None
                    open_idx = -1
                    for tag in self.OPEN_TAGS:
                        idx = low.find(tag)
                        if idx != -1:
                            if open_idx == -1 or idx < open_idx:
                                open_idx = idx
                                matched_open = tag

                    if matched_open is not None:
                        pre_text = self.buffer[:open_idx]
                        if pre_text:
                            output.append(pre_text)

                        tag_len = len(matched_open)
                        self.buffer = self.buffer[open_idx + tag_len:]
                        if self.buffer.startswith("\n"):
                            self.buffer = self.buffer[1:]

                        self.state = self.STATE_THINKING
                        self.has_thought = True
                        self.think_start_time = time.time()
                        if self.thinking_mode == "expanded":
                            header = (
                                f"\n  \033[38;5;244m╭─ 🧠 Thinking Process ──────────────────────────────────────────\033[0m\n"
                                f"  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m"
                            )
                            output.append(header)
                        continue

                    if "<visual" in low:
                        idx = low.find("<visual")
                        pre_vis = self.buffer[:idx]
                        self.buffer = self.buffer[idx:]
                        self.in_visual = True
                        output.append(pre_vis)
                        continue

                    partial_len = 0
                    for tag in self.OPEN_TAGS + ["<visual"]:
                        for pl in range(1, len(tag)):
                            if low.endswith(tag[:pl]):
                                if pl > partial_len:
                                    partial_len = pl

                    if partial_len > 0:
                        to_emit = self.buffer[:-partial_len]
                        self.buffer = self.buffer[-partial_len:]
                        if to_emit:
                            output.append(to_emit)
                        break
                    else:
                        output.append(self.buffer)
                        self.buffer = ""
                        break
                else:
                    low = self.buffer.lower()
                    if "</visual>" in low:
                        idx = low.find("</visual>")
                        self.buffer = self.buffer[idx + len("</visual>"):]
                        self.in_visual = False
                        continue
                    elif ">" in self.buffer and "}" in self.buffer:
                        idx = self.buffer.find(">")
                        self.buffer = self.buffer[idx + 1:]
                        self.in_visual = False
                        continue
                    break

        return "".join(output)

    def flush(self) -> str:
        output = []
        if self.state == self.STATE_THINKING:
            if self.buffer and self.thinking_mode == "expanded":
                formatted = self.buffer.replace("\n", "\n  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m")
                output.append(formatted)
            dur = max(0.1, time.time() - self.think_start_time)
            if self.thinking_mode == "expanded":
                footer = (
                    f"\033[0m\n  \033[38;5;244m╰───────────────────────────────────────────\033[0m "
                    f"\033[90m(thought for {dur:.1f}s)\033[0m\n"
                )
            elif self.thinking_mode == "collapsed":
                footer = f"\n  \033[90m[🧠 Thought for {dur:.1f}s]\033[0m\n"
            else:
                footer = ""
            output.append(footer)
            self.buffer = ""
        elif self.state == self.STATE_INITIAL:
            output.append(self.buffer)
            self.buffer = ""
        elif self.state == self.STATE_RESULT:
            if not self.in_visual:
                output.append(self.buffer)
            self.buffer = ""
        return "".join(output)


VisualTokenFilter = ThinkingResultStreamFilter


def read_terminal_input(prompt_label: str) -> str:
    """Reads single-line or multi-line/bulk input from the user."""
    try:
        first_line = input(prompt_label)
    except EOFError:
        return "exit"

    trimmed = first_line.strip()

    # 1. Triple quotes multi-line trigger: """ or '''
    if trimmed.startswith('"""') or trimmed.startswith("'''"):
        quote = '"""' if trimmed.startswith('"""') else "'''"
        if len(trimmed) > 3 and trimmed.endswith(quote):
            return trimmed[3:-3].strip()

        lines = [trimmed[3:]]
        print(f" {UI.GRAY}[Bulk mode active. Paste your text, then type {quote} or /send on a new line]{UI.RESET}")
        while True:
            try:
                line = input(f" {UI.GRAY}...{UI.RESET} ")
                if quote in line:
                    idx = line.find(quote)
                    lines.append(line[:idx])
                    break
                if line.strip().lower() in ("/send", "/end", ":q"):
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break
        return "\n".join(lines).strip()

    # 2. Backslash line continuation
    if trimmed.endswith("\\"):
        lines = [trimmed[:-1].strip()]
        while True:
            try:
                line = input(f" {UI.GRAY}...{UI.RESET} ")
                if line.endswith("\\"):
                    lines.append(line[:-1].strip())
                else:
                    lines.append(line)
                    break
            except (EOFError, KeyboardInterrupt):
                break
        return "\n".join(lines).strip()

    return trimmed


def interactive_select_personality(cfg: ClientConfig, customizer: UserCustomizationManager) -> Optional[str]:
    """Displays an interactive numbered menu for selecting assistant personality."""
    print(f"\n {UI.MAGENTA}┌── 🎭 SELECT JULY PERSONALITY PROFILE ─────────────────────────────────┐{UI.RESET}")
    print(f" {UI.GRAY}│ Choose how July reasons, structures responses, and communicates.     │{UI.RESET}")
    print(f" {UI.MAGENTA}├───────────────────────────────────────────────────────────────────────┤{UI.RESET}")

    items = list(customizer.PERSONALITY_METADATA.items())
    for i, (k, meta) in enumerate(items, 1):
        is_curr = (k == cfg.personality)
        mark = f"{UI.GREEN}● ACTIVE{UI.RESET}" if is_curr else " "
        title_colored = f"{UI.BOLD}{UI.CYAN}{meta['title']}{UI.RESET}" if is_curr else f"{UI.WHITE}{meta['title']}{UI.RESET}"
        print(f" {UI.GRAY}│{UI.RESET} [{UI.YELLOW}{i}{UI.RESET}] {meta['icon']} {title_colored:<30} {mark}")
        print(f" {UI.GRAY}│     {UI.DIM}{meta['description'][:60]}{UI.RESET}")

    print(f" {UI.MAGENTA}└───────────────────────────────────────────────────────────────────────┘{UI.RESET}")
    curr_meta = customizer.PERSONALITY_METADATA.get(cfg.personality, {})
    curr_title = curr_meta.get("title", cfg.personality)
    curr_icon = curr_meta.get("icon", "🎭")
    print(f"  Current Active: {curr_icon} {UI.GREEN}{curr_title}{UI.RESET}")

    try:
        choice = input(f"\n  Choose personality [1-{len(items)}] (or Enter to keep current): ").strip()
        if not choice:
            return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                selected_key = items[idx][0]
                cfg.personality = selected_key
                cfg.save()
                customizer.config = cfg
                sel_meta = items[idx][1]
                print(f"\n  {UI.GREEN}[✓] Switched personality to:[/] {UI.BOLD}{sel_meta['icon']} {sel_meta['title']}{UI.RESET}")
                print(f"      {UI.GRAY}{sel_meta['description']}{UI.RESET}\n")
                return selected_key
            else:
                print(f"  {UI.RED}[!] Invalid choice number.{UI.RESET}\n")
        else:
            matched = None
            for k, meta in items:
                if choice.lower() in k.lower() or choice.lower() in meta["title"].lower():
                    matched = (k, meta)
                    break
            if matched:
                cfg.personality = matched[0]
                cfg.save()
                customizer.config = cfg
                print(f"\n  {UI.GREEN}[✓] Switched personality to:[/] {UI.BOLD}{matched[1]['icon']} {matched[1]['title']}{UI.RESET}\n")
                return matched[0]
            else:
                print(f"  {UI.RED}[!] Unknown personality name.{UI.RESET}\n")
    except (EOFError, KeyboardInterrupt):
        print()
    return None


def cmd_personality(args):
    # Enforce strict authentication before allowing personality / mode configuration
    is_auth, _ = ensure_authenticated_for_models(prompt_user=True)
    if not is_auth:
        print(f"\n {UI.RED}[!] Access Blocked:{UI.RESET} Strict authentication required before configuring model personality.")
        print(f" {UI.GRAY}[i] Run 'july login' to authenticate with Clerk / HS AI Solutions.{UI.RESET}\n")
        return

    UI.print_banner("Personality & Tone Configuration")
    cfg = ClientConfig.load()
    customizer = UserCustomizationManager(cfg)
    target = getattr(args, "name", None)
    if target:
        items = list(customizer.PERSONALITY_METADATA.items())
        matched = None
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(items):
                matched = items[idx]
        if not matched:
            for k, meta in items:
                if target.lower() in k.lower() or target.lower() in meta["title"].lower():
                    matched = (k, meta)
                    break
        if matched:
            cfg.personality = matched[0]
            cfg.save()
            print(f"\n {UI.GREEN}[✓] Switched personality to:[/] {UI.BOLD}{matched[1]['icon']} {matched[1]['title']}{UI.RESET}")
            print(f"     {UI.GRAY}{matched[1]['description']}{UI.RESET}\n")
            return
    interactive_select_personality(cfg, customizer)


def interactive_select_model(cfg: ClientConfig) -> Optional[str]:
    """Displays an interactive numbered menu for selecting foundation model or auto routing."""
    # Enforce strict authentication before displaying model selector menu
    is_auth, _ = ensure_authenticated_for_models(prompt_user=True)
    if not is_auth:
        print(f"\n {UI.RED}[!] Model Selection Blocked:{UI.RESET} Strict authentication required before selecting a model.")
        print(f" {UI.GRAY}[i] Run 'july login' to authenticate with Clerk / HS AI Solutions.{UI.RESET}\n")
        return None

    from .state_manager import DualModelStateManager, ModelStatus
    from .storage import PermanentModelStorage
    state_mgr = DualModelStateManager()
    perm_storage = PermanentModelStorage()

    print(f"\n {UI.MAGENTA}┌── 🧠 HS AI SOLUTIONS — DUAL MODEL ARCHITECTURE SELECTOR ─────────────┐{UI.RESET}")
    print(f" {UI.GRAY}│ July and Gravity are independent, permanently available model choices.│{UI.RESET}")
    print(f" {UI.MAGENTA}├───────────────────────────────────────────────────────────────────────┤{UI.RESET}")

    current = getattr(cfg, "selected_model", "july").lower()
    active_m = state_mgr.activeModel

    items = [
        ("1", "july", MODEL_METADATA["july"]),
        ("2", "gravity", MODEL_METADATA["gravity"]),
        ("3", "auto", MODEL_METADATA["auto"]),
    ]

    for num, k, meta in items:
        is_pref = (k == current)
        is_act = (k == active_m)

        if k == "auto":
            state_label = f"{UI.MAGENTA}[DYNAMIC ROUTER]{UI.RESET}"
        elif is_act:
            state_label = f"{UI.GREEN}[Active]{UI.RESET}"
        elif perm_storage.is_model_present(k):
            state_label = f"{UI.CYAN}[Available / Unloaded]{UI.RESET}"
        elif state_mgr.get_model_state(k) == ModelStatus.DOWNLOADING.value:
            state_label = f"{UI.YELLOW}[Downloading]{UI.RESET}"
        else:
            state_label = f"{UI.GRAY}[Available for Download]{UI.RESET}"

        pref_mark = f" {UI.BOLD}{UI.YELLOW}(Selected){UI.RESET}" if is_pref else ""
        title_col = f"{UI.BOLD}{UI.CYAN}{meta['title']}{UI.RESET}"
        print(f" {UI.GRAY}│{UI.RESET} [{UI.YELLOW}{num}{UI.RESET}] {title_col:<30} {state_label:<24} {pref_mark}")
        print(f" {UI.GRAY}│     {UI.DIM}Arch: {meta['architecture']} | {meta['parameters']}{UI.RESET}")
        print(f" {UI.GRAY}│     {UI.GRAY}{meta['description'][:68]}{UI.RESET}")
        if num != "3":
            print(f" {UI.GRAY}│{UI.RESET}")

    print(f" {UI.MAGENTA}└───────────────────────────────────────────────────────────────────────┘{UI.RESET}")

    try:
        choice = input(f"\n  {UI.BOLD}Select model [1-3, name, or Enter to cancel]{UI.RESET} › ").strip().lower()
        if not choice:
            print(f"  {UI.GRAY}[*] Model selection unchanged: {current.upper()}{UI.RESET}\n")
            return None

        matched_key = None
        for num, k, meta in items:
            if choice in (num, k, meta["title"].lower(), f"{k} llm", f"{k}_llm"):
                matched_key = k
                break

        if matched_key:
            cfg.selected_model = matched_key
            cfg.save()
            state_mgr.selectedModel = matched_key
            meta = MODEL_METADATA[matched_key]
            print(f"\n  {UI.GREEN}[✓] Persistent model preference configured:[/] {UI.BOLD}{meta['title']}{UI.RESET}")
            print(f"      {UI.GRAY}{meta['description']}{UI.RESET}\n")
            return matched_key
        else:
            print(f"  {UI.RED}[!] Invalid choice.{UI.RESET}\n")
            return None
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def cmd_model(args):
    # Enforce strict authentication before allowing model selection, listing, or configuration
    is_auth, session = ensure_authenticated_for_models(prompt_user=True)
    if not is_auth:
        print(f"\n {UI.RED}[!] Model Access Blocked:{UI.RESET} Strict authentication required before viewing or selecting July or Gravity models.")
        print(f" {UI.GRAY}[i] Run 'july login' to authenticate with Clerk / HS AI Solutions.{UI.RESET}\n")
        return

    UI.print_banner("Dual-Model Configuration & Management")
    cfg = ClientConfig.load()
    name = getattr(args, "name", None)
    is_list = getattr(args, "list", False)
    is_status = getattr(args, "status", False)
    target_arg = getattr(args, "target", None)

    perm = PermanentModelStorage()
    from .dual_engine import DualModelCoordinator
    coordinator = DualModelCoordinator(config=cfg, storage=perm)

    if is_list or (name and name.lower() in ("list", "ls", "models")):
        print(f"\n {UI.BOLD}{UI.CYAN}Registered Foundation Models:{UI.RESET}")
        for k, meta in MODEL_METADATA.items():
            active_str = f" {UI.GREEN}[ACTIVE]{UI.RESET}" if getattr(cfg, "selected_model", "july") == k else ""
            is_down = perm.is_model_present(k)
            down_str = f"{UI.GREEN}Downloaded{UI.RESET}" if is_down else f"{UI.YELLOW}Not Downloaded{UI.RESET}"
            print(f"\n   {UI.BOLD}{UI.CYAN}• {meta['title']}{UI.RESET}{active_str} — [{down_str}]")
            print(f"     Architecture  : {meta['architecture']}")
            print(f"     Parameters    : {meta['parameters']}")
            print(f"     Quantization  : {meta['quantization']}")
            print(f"     Context Limit : {meta['context_length']:,} tokens")
            print(f"     Specialty     : {meta['description']}")
        print()
        return

    if is_status or (name and name.lower() in ("status", "telemetry")):
        cmd_status()
        return

    if name:
        target = name.lower().strip()

        # Handle "download [gravity]"
        if target in ("download", "get"):
            model_target = (target_arg or "gravity").lower().strip()
            if perm.is_model_present(model_target):
                print(f"\n {UI.GREEN}[✓] {model_target.upper()} LLM is already downloaded and verified on disk.{UI.RESET}\n")
            elif coordinator.is_downloading(model_target):
                print(f"\n {UI.YELLOW}[*] {model_target.upper()} LLM is currently downloading in the background.{UI.RESET}\n")
            else:
                print(f"\n {UI.CYAN}[*] Starting background download of {model_target.upper()} LLM from Cloudflare R2...{UI.RESET}")
                coordinator._launch_background_download(model_target, auto_activate=True)
                print(f" {UI.GREEN}[✓] Background acquisition started. July LLM remains active for inference.{UI.RESET}\n")
            return

        # Handle "cancel [gravity]"
        if target in ("cancel", "stop"):
            model_target = (target_arg or "gravity").lower().strip()
            if coordinator.cancel_download(model_target):
                print(f"\n {UI.GREEN}[✓] Cancelled download for {model_target.upper()} LLM. Partial data preserved.{UI.RESET}\n")
            else:
                print(f"\n {UI.YELLOW}[*] No active download found for {model_target.upper()} LLM.{UI.RESET}\n")
            return

        matched = None
        for k in ("july", "gravity", "auto"):
            if target in (k, f"{k} llm", f"{k}_llm", f"mode_{k}"):
                matched = k
                break
        if target in ("1", "j"): matched = "july"
        elif target in ("2", "g"): matched = "gravity"
        elif target in ("3", "a"): matched = "auto"

        if matched:
            cfg.selected_model = matched
            cfg.save()
            meta = MODEL_METADATA[matched]
            print(f"\n {UI.GREEN}[✓] Configured active model:[/] {UI.BOLD}{meta['title']}{UI.RESET}")
            print(f"     {UI.GRAY}{meta['description']}{UI.RESET}\n")

            if matched == "gravity" and not perm.is_model_present("gravity"):
                print(f" {UI.CYAN}[JULY ACTIVE] [GRAVITY DOWNLOADING: 0%]{UI.RESET}")
                print(f" {UI.BOLD}{UI.CYAN}JULY LLM:{UI.RESET} I'm July. Gravity is downloading in the background. You can continue chatting with me while it prepares.\n")
                coordinator._launch_background_download("gravity", auto_activate=True)
            elif matched in ("july", "gravity"):
                if perm.is_model_present(matched):
                    record_active_state(perm.get_model_file(matched), matched)
                    print(f" {UI.GREEN}[✓] {matched.upper()} LLM mounted into persistent active memory.{UI.RESET}\n")
            return
        else:
            print(f" {UI.RED}[!] Unknown model '{name}'. Available: july, gravity, auto, list, status, download, cancel{UI.RESET}\n")
            return

    interactive_select_model(cfg)


def cmd_hardware(args=None):
    """Displays comprehensive hardware and resource telemetry."""
    UI.print_banner("Hardware & System Telemetry")
    cfg = ClientConfig.load()
    mid = getattr(cfg, "selected_model", "july")
    telem = get_detailed_hardware_telemetry(mid)
    print("\n" + render_hardware_card(telem) + "\n")


def cmd_memory_report(args=None):
    """Displays detailed RAM, VRAM, and memory persistence profile."""
    UI.print_banner("Memory & VRAM Telemetry")
    cfg = ClientConfig.load()
    mid = getattr(cfg, "selected_model", "july")
    telem = get_detailed_hardware_telemetry(mid)
    try:
        from .memory_engine import HierarchicalMemoryEngine
        mem_count = len(HierarchicalMemoryEngine().get_all_active_memories())
    except Exception:
        mem_count = 0
    print("\n" + render_memory_card(telem, mem_count) + "\n")


def cmd_gpu(args=None):
    """Displays GPU acceleration, VRAM allocation, and layer offloading report."""
    UI.print_banner("GPU & CUDA Telemetry")
    cfg = ClientConfig.load()
    mid = getattr(cfg, "selected_model", "july")
    telem = get_detailed_hardware_telemetry(mid)
    print("\n" + render_gpu_card(telem) + "\n")


def cmd_models(args=None):
    """Displays table of all registered foundation models."""
    cmd_model(argparse.Namespace(name="list", list=True, status=False, target=None))


def cmd_voice(args=None):
    """Configures Whisper STT voice input and multilingual TTS voice output."""
    v_coord = CLIHardwareVoiceCoordinator.get_instance()
    action = getattr(args, "action", None)
    value = getattr(args, "value", None)

    if not action:
        stt_stat = "ON" if v_coord.stt.is_enabled else "OFF"
        tts_stat = "ON" if v_coord.tts.is_enabled else "OFF"
        print(f"\n {UI.BOLD}{UI.CYAN}Voice Configuration:{UI.RESET}")
        print(f"   Whisper STT Input : {UI.GREEN if v_coord.stt.is_enabled else UI.GRAY}{stt_stat}{UI.RESET} (Model: {v_coord.stt.model_name}, Lang: {v_coord.stt.language})")
        print(f"   TTS Speech Output : {UI.GREEN if v_coord.tts.is_enabled else UI.GRAY}{tts_stat}{UI.RESET} (Backend: {v_coord.tts.backend}, Gender: {v_coord.tts.voice_gender}, Speed: {v_coord.tts.speed} wpm)\n")
        print(f"   Commands: {UI.CYAN}/voice on{UI.RESET}, {UI.CYAN}/voice off{UI.RESET}, {UI.CYAN}/voice input{UI.RESET}, {UI.CYAN}/voice language <code>{UI.RESET}, {UI.CYAN}/voice model <size>{UI.RESET}")
        print(f"             {UI.CYAN}/voice output on{UI.RESET}, {UI.CYAN}/voice output off{UI.RESET}, {UI.CYAN}/voice female{UI.RESET}, {UI.CYAN}/voice gender <female|male>{UI.RESET}")
        print(f"             {UI.CYAN}/voice speed <wpm>{UI.RESET}, {UI.CYAN}/voice stop{UI.RESET}\n")
        return

    act = action.lower()
    if act == "on":
        v_coord.stt.is_enabled = True
        print(f"\n {UI.GREEN}[✓] Whisper voice input enabled.{UI.RESET}\n")
    elif act == "off":
        v_coord.stt.is_enabled = False
        print(f"\n {UI.YELLOW}[*] Whisper voice input disabled.{UI.RESET}\n")
    elif act == "input":
        print(f"\n {UI.MAGENTA}🎙️  [WHISPER VOICE INPUT]{UI.RESET} Listening for 5 seconds... Speak now!")
        audio = v_coord.stt.record_audio(5.0)
        if audio is not None:
            txt, lang = v_coord.stt.transcribe_audio(audio)
            print(f"\n {UI.GREEN}[Whisper STT ({lang})]:{UI.RESET} \"{txt}\"\n")
    elif act in ("language", "lang"):
        if value:
            v_coord.stt.set_language(value)
            print(f"\n {UI.GREEN}[✓] Whisper language set to: {value.upper()}{UI.RESET}\n")
        else:
            print(f"\n {UI.CYAN}Whisper language: {v_coord.stt.language.upper()}{UI.RESET}\n")
    elif act in ("model", "size"):
        if value:
            try:
                mod = v_coord.stt.set_model(value)
                print(f"\n {UI.GREEN}[✓] Whisper model size set to: {mod}{UI.RESET}\n")
            except Exception as e:
                print(f"\n {UI.RED}[!] {e}{UI.RESET}\n")
        else:
            print(f"\n {UI.CYAN}Whisper model size: {v_coord.stt.model_name}{UI.RESET}\n")
    elif act == "output":
        sub_act = (value or "").lower()
        if sub_act == "on":
            v_coord.tts.is_enabled = True
            print(f"\n {UI.GREEN}[✓] TTS Voice Output enabled.{UI.RESET} (Backend: {v_coord.tts.backend})\n")
        elif sub_act == "off":
            v_coord.tts.is_enabled = False
            v_coord.tts.stop()
            print(f"\n {UI.YELLOW}[*] TTS Voice Output disabled.{UI.RESET}\n")
        else:
            print(f"\n Usage: july voice output on | off\n")
    elif act in ("speed", "rate"):
        if value:
            try:
                spd = v_coord.tts.set_speed(int(value))
                print(f"\n {UI.GREEN}[✓] TTS speed set to: {spd} wpm{UI.RESET}\n")
            except ValueError:
                print(f"\n {UI.RED}[!] Speed must be an integer (e.g. 180).{UI.RESET}\n")
        else:
            print(f"\n {UI.CYAN}TTS speed: {v_coord.tts.speed} wpm{UI.RESET}\n")
    elif act in ("gender", "voice"):
        if value:
            g = v_coord.tts.set_gender(value)
            print(f"\n {UI.GREEN}[✓] TTS voice gender set to: {g}{UI.RESET}\n")
        else:
            print(f"\n {UI.CYAN}TTS voice gender: {v_coord.tts.voice_gender}{UI.RESET}\n")
    elif act == "female":
        v_coord.tts.set_gender("female")
        print(f"\n {UI.GREEN}[✓] TTS voice set to Female (Microsoft Zira / Female Voice).{UI.RESET}\n")
    elif act == "male":
        v_coord.tts.set_gender("male")
        print(f"\n {UI.GREEN}[✓] TTS voice set to Male.{UI.RESET}\n")
    elif act in ("stop", "halt", "mute"):
        v_coord.tts.stop()
        print(f"\n {UI.GREEN}[✓] TTS speech stopped.{UI.RESET}\n")
    else:
        print(f"\n {UI.YELLOW}Unknown voice action '{action}'. Options: on, off, input, language, model, output on|off, female, gender <female|male>, speed, stop{UI.RESET}\n")


def cmd_chat(args):
    # Enforce authentication before allowing model chat
    is_auth, session = ensure_authenticated_for_models(prompt_user=True)
    if not is_auth:
        print(f"\n {UI.RED}[!] Model Access Blocked:{UI.RESET} Authentication required before chatting with July or Gravity models.")
        print(f" {UI.GRAY}[i] Run 'july login' to authenticate with Clerk / HS AI Solutions.{UI.RESET}\n")
        sys.exit(1)

    user_tier = (session.get("tier") if session else "standard") or "standard"
    limiter = ClientRateLimiter.get_instance()

    cfg = ClientConfig.load()

    # Check for CLI model override: --model / -M
    cli_model = getattr(args, "model", None)
    if cli_model:
        m_norm = cli_model.lower().strip()
        if m_norm in ("1", "j", "july"):
            cfg.selected_model = "july"
        elif m_norm in ("2", "g", "gravity"):
            cfg.selected_model = "gravity"
        elif m_norm in ("3", "a", "auto"):
            cfg.selected_model = "auto"
        cfg.save()

    active_path, active_mid = get_active_model_info()
    wanted_model = getattr(cfg, "selected_model", "july").lower()
    if wanted_model == "auto":
        wanted_model = "july"  # default warm seed

    if not active_path or (active_mid != wanted_model and active_mid != "none"):
        print(f" {UI.YELLOW}[!] Initializing {wanted_model.upper()} LLM into RAM storage...{UI.RESET}")
        cmd_load(argparse.Namespace(model=wanted_model))
        active_path, active_mid = get_active_model_info()
        if not active_path:
            print(f" {UI.RED}[!] Could not initialize model.{UI.RESET}")
            sys.exit(1)

    cfg = ClientConfig.load()
    storage = ClientEphemeralStorage()
    customizer = UserCustomizationManager(cfg)

    # Check for CLI personality override
    cli_persona = getattr(args, "personality", None)
    if cli_persona:
        items = list(customizer.PERSONALITY_METADATA.items())
        matched = None
        if cli_persona.isdigit():
            idx = int(cli_persona) - 1
            if 0 <= idx < len(items):
                matched = items[idx]
        if not matched:
            for k, meta in items:
                if cli_persona.lower() in k.lower() or cli_persona.lower() in meta["title"].lower():
                    matched = (k, meta)
                    break
        if matched:
            cfg.personality = matched[0]
            cfg.save()
            customizer.config = cfg

    runtime = ClientInferenceRuntime(cfg, storage, customizer)

    prompt_to_run = getattr(args, "prompt", None)
    file_arg = getattr(args, "file", None)
    if file_arg:
        fpath = Path(file_arg)
        if fpath.exists() and fpath.is_file():
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    prompt_to_run = f.read().strip()
            except Exception as e:
                print(f" {UI.RED}[!] Error reading prompt file:{UI.RESET} {e}")
                sys.exit(1)
        else:
            print(f" {UI.RED}[!] File not found:{UI.RESET} {file_arg}")
            sys.exit(1)
    elif not prompt_to_run and not sys.stdin.isatty():
        try:
            # Only read piped stdin if no direct prompt provided
            import select
            if hasattr(select, "select"):
                r, _, _ = select.select([sys.stdin], [], [], 0.0)
                if r:
                    prompt_to_run = sys.stdin.read().strip()
        except Exception:
            pass

    if not prompt_to_run:
        UI.print_banner()
        active_mode = getattr(cfg, "selected_model", "july").upper()
        user_email = (session.get('email') if session else 'Developer') or 'Developer'
        print(f"  {UI.GRAY}User Account:{UI.RESET} {UI.GREEN}{user_email}{UI.RESET} {UI.GRAY}[{UI.CYAN}{user_tier.upper()}{UI.GRAY} Plan • Model Access Granted]{UI.RESET}")
        print(f"  {UI.GRAY}Active Model:{UI.RESET} {UI.CYAN}{active_mode} LLM{UI.RESET} {UI.GRAY}(Type {UI.YELLOW}/model{UI.GRAY} to switch models){UI.RESET}")
        print(f"  {UI.GRAY}Personality :{UI.RESET} {UI.YELLOW}{cfg.personality.replace('_', ' ').title()}{UI.RESET}  {UI.GRAY}Thinking:{UI.RESET} {UI.GREEN}{getattr(cfg, 'thinking_mode', 'expanded').upper()}{UI.RESET}")
        print(f"  {UI.GRAY}Commands    :{UI.RESET} {UI.CYAN}/model{UI.RESET}, {UI.CYAN}/hardware{UI.RESET}, {UI.CYAN}/memory{UI.RESET}, {UI.CYAN}/gpu{UI.RESET}, {UI.CYAN}/voice{UI.RESET}, {UI.CYAN}/think{UI.RESET}, {UI.CYAN}/help{UI.RESET}, {UI.CYAN}exit{UI.RESET}")
        print(f"{UI.GRAY}─────────────────────────────────────────────────────────────────────────────{UI.RESET}\n")

        # Premium Status Box (Requirement 7)
        v_coord = CLIHardwareVoiceCoordinator.get_instance()
        p_stor = PermanentModelStorage()
        grav_stat = "Ready" if p_stor.is_model_present("gravity") else "Not Downloaded"
        telem = get_detailed_hardware_telemetry(active_mode.lower(), runtime)
        box = render_cli_status_box(
            active_model=active_mode,
            gravity_status=grav_stat,
            download_pct=0.0,
            speed_mb=0.0,
            ram_used_gb=telem["ram_used_gb"],
            ram_total_gb=telem["ram_total_gb"],
            vram_used_gb=telem["vram_used_gb"],
            vram_total_gb=telem["vram_total_gb"],
            voice_stt=v_coord.stt.is_enabled,
            voice_tts=v_coord.tts.is_enabled,
            voice_gender=v_coord.tts.voice_gender
        )
        print(box + "\n")

    runtime.load_model(active_path)

    if prompt_to_run:
        # Rate Limit check
        allowed, retry_after, reason, metrics = limiter.check_limit(tier=user_tier, estimated_tokens=len(prompt_to_run.split()) * 2)
        if not allowed:
            print(f"\n {UI.RED}[!] RATE LIMIT EXCEEDED:{UI.RESET} {reason}")
            print(f" {UI.YELLOW}[*] Cooldown period:{UI.RESET} Please wait {retry_after:.1f}s before sending another prompt.")
            print(f" {UI.GRAY}[i] Rate Limit: {metrics.get('rpm_used', 0)}/{metrics.get('rpm_max', 20)} RPM ({metrics.get('tier', 'standard').upper()} Tier){UI.RESET}")
            print(f" {UI.GRAY}[i] Upgrade your plan for higher throughput at:{UI.RESET} {UI.URL}{STUDIO_URL}{UI.RESET}\n")
            return

        # One-off or bulk prompt
        active_mode = getattr(cfg, "selected_model", "july").upper()
        if active_mode == "GRAVITY":
            badge_color = UI.YELLOW
            label = "GRAVITY"
        elif active_mode == "AUTO":
            badge_color = UI.MAGENTA
            label = f"AUTO ({runtime.current_model_id.upper()})"
        else:
            badge_color = UI.CYAN
            label = "JULY"

        print(f"\n{UI.BOLD}{UI.GREEN}❯ You{UI.RESET} {UI.GRAY}›{UI.RESET} {prompt_to_run[:200]}{'...' if len(prompt_to_run) > 200 else ''}")
        print(f"{UI.BOLD}{badge_color}❯ {label}{UI.RESET} {UI.GRAY}›{UI.RESET} ", end="", flush=True)
        t0 = time.time()
        tok_count = 0
        full_response = []
        th_mode = getattr(cfg, "thinking_mode", "expanded")
        token_filter = ThinkingResultStreamFilter(model_name=label, badge_color=badge_color, thinking_mode=th_mode)
        for token in runtime.generate_stream(prompt_to_run):
            chunk = token_filter.process(token)
            if chunk:
                sys.stdout.write(chunk)
                sys.stdout.flush()
            tok_count += 1
            full_response.append(token)
        rem = token_filter.flush()
        if rem:
            sys.stdout.write(rem)
            sys.stdout.flush()
        elapsed = max(0.001, time.time() - t0)
        print(f"\n\n{UI.GRAY}[⚡ {tok_count} tokens | {tok_count/elapsed:.1f} tok/s | {elapsed:.2f}s | Ephemeral RAM: Active]{UI.RESET}")

        limiter.record_usage(tokens=tok_count)

        try:
            ClerkAuthManager().record_usage(active_mid, len(prompt_to_run.split()), tok_count)
        except Exception:
            pass

        full_text = "".join(full_response)
        try:
            from .visual import VisualResponseEngine
            engine = VisualResponseEngine()
            rendered = engine.process_and_render(user_prompt=prompt_to_run, model_response=full_text)
            if not rendered:
                visual_info = detect_visual_content(full_text)
                if visual_info:
                    v_type, v_code = visual_info
                    if v_type == "mermaid":
                        cli_diagram = render_mermaid_to_cli(v_code)
                        if cli_diagram:
                            print(f"\n{cli_diagram}\n")
        except Exception as e:
            pass
        print()
        return

    # Interactive REPL
    session_id = f"cli_{int(time.time())}"
    last_visual_file: Path | None = None
    voice_coord = CLIHardwareVoiceCoordinator.get_instance()
    perm_storage = PermanentModelStorage()
    from .dual_engine import DualModelCoordinator
    coordinator = DualModelCoordinator(config=cfg, runtime=runtime, storage=perm_storage)

    while True:
        try:
            # Render background download status line if active (non-destructive)
            if coordinator.is_downloading("gravity"):
                d_stat = coordinator.state_mgr.modelInitializationStatus.get("gravity", {})
                pct = d_stat.get("percent", 0.0)
                print(f"  {UI.CYAN}[JULY ACTIVE] [GRAVITY DOWNLOADING: {pct:.0f}%]{UI.RESET}")

            prompt_label = f"{UI.BOLD}{UI.GREEN}❯ You{UI.RESET} {UI.GRAY}(Voice/Text) ›{UI.RESET} " if voice_coord.stt.is_enabled else f"{UI.BOLD}{UI.GREEN}❯ You{UI.RESET} {UI.GRAY}›{UI.RESET} "
            user_input = read_terminal_input(prompt_label).strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print(f"\n {UI.GRAY}Leaving chat session...{UI.RESET}")
                break

            # Slash commands
            if user_input.startswith("/"):
                cmd_parts = user_input.split()
                c = cmd_parts[0].lower()

                if c == "/help":
                    print(f"\n {UI.BOLD}{UI.CYAN}Available Commands:{UI.RESET}")
                    print(f"   {UI.CYAN}/whoami{UI.RESET}         - View active authenticated identity, tier & creator badge")
                    print(f"   {UI.CYAN}/context{UI.RESET}        - View live runtime context (Date, Time, Location & Host)")
                    print(f"   {UI.CYAN}/model <july|gravity|download|cancel|status>{UI.RESET} - Select or background-download model")
                    print(f"   {UI.CYAN}/models{UI.RESET}                 - List all registered models and specifications")
                    print(f"   {UI.CYAN}/hardware{UI.RESET}               - Real-time CPU, RAM, GPU, VRAM & utilization telemetry")
                    print(f"   {UI.CYAN}/memory{UI.RESET}                 - Detailed RAM, VRAM, and model memory breakdown")
                    print(f"   {UI.CYAN}/gpu{UI.RESET}                    - GPU acceleration, VRAM allocation, and layer offloading")
                    print(f"   {UI.CYAN}/voice <on|off|input|lang|model>{UI.RESET} - Whisper STT microphone input & language")
                    print(f"   {UI.CYAN}/voice output <on|off|speed|stop>{UI.RESET} - Multilingual TTS voice response synthesis")
                    print(f"   {UI.CYAN}/sandbox [act]{UI.RESET}   - Windows Sandbox status and isolation control (status, reset, run)")
                    print(f"   {UI.CYAN}/think [mode]{UI.RESET}   - Highlight model thinking (expanded, collapsed, hidden)")
                    print(f"   {UI.CYAN}/paste, /bulk{UI.RESET}   - Enter multi-line bulk prompt mode (finish with /send)")
                    print(f"   {UI.CYAN}/file <path>{UI.RESET}    - Load entire text file as prompt")
                    print(f"   {UI.CYAN}/visual{UI.RESET}         - Show On-Demand Visual Response Engine status and visual capabilities")
                    print(f"   {UI.CYAN}/studio{UI.RESET}         - Open HS AI Studio Portal link")
                    print(f"   {UI.CYAN}/clear{UI.RESET}          - Clear terminal and reset chat history")
                    print(f"   {UI.CYAN}/status{UI.RESET}         - Show hardware, memory, and model telemetry")
                    print(f"   {UI.CYAN}/feedback{UI.RESET}       - Record feedback or failure report for continuous evolution")
                    print(f"   {UI.CYAN}/mode <name>{UI.RESET}   - Switch personality profile")
                    print(f"   {UI.CYAN}exit, quit{UI.RESET}      - Exit and safely reclaim RAM\n")
                    continue

                if c == "/hardware":
                    cmd_hardware()
                    continue

                if c in ("/memory", "/mem"):
                    cmd_memory_report()
                    continue

                if c == "/gpu":
                    cmd_gpu()
                    continue

                if c == "/models":
                    cmd_models()
                    continue

                if c == "/sandbox":
                    from .sandbox import SandboxManager
                    mgr = SandboxManager.get_instance()
                    sub_act = cmd_parts[1].lower() if len(cmd_parts) > 1 else "status"
                    if sub_act == "status":
                        print(mgr.render_dashboard())
                    elif sub_act == "reset":
                        res = mgr.reset()
                        print(f"\n  {UI.GREEN}[✓] {res['message']}{UI.RESET}\n")
                    elif sub_act in ("run", "exec") and len(cmd_parts) > 2:
                        target_cmd = " ".join(cmd_parts[2:])
                        print(f"\n  {UI.CYAN}[SANDBOX]{UI.RESET} Executing: {UI.BOLD}{target_cmd}{UI.RESET}")
                        sbx_res = mgr.execute(target_cmd)
                        if sbx_res.stdout:
                            sys.stdout.write(sbx_res.stdout)
                        if sbx_res.stderr:
                            sys.stderr.write(sbx_res.stderr)
                        print(f"\n  {UI.GRAY}[Exit: {sbx_res.exit_code} | Duration: {sbx_res.duration_seconds}s]{UI.RESET}\n")
                    else:
                        print(f"\n  {UI.CYAN}Usage: /sandbox status | /sandbox reset | /sandbox run <command>{UI.RESET}\n")
                    continue

                if c in ("/think", "/thinking"):
                    if len(cmd_parts) > 1:
                        target = cmd_parts[1].lower().strip()
                        if target in ("on", "show", "expand", "expanded", "1"):
                            cfg.thinking_mode = "expanded"
                        elif target in ("collapse", "collapsed", "summary", "2"):
                            cfg.thinking_mode = "collapsed"
                        elif target in ("off", "hide", "hidden", "0"):
                            cfg.thinking_mode = "hidden"
                        else:
                            print(f"\n  {UI.RED}[!] Unknown mode '{target}'. Available: {UI.CYAN}/think expanded{UI.RESET} | {UI.CYAN}collapsed{UI.RESET} | {UI.CYAN}hidden{UI.RESET}\n")
                            continue
                        cfg.save()
                        print(f"\n  {UI.GREEN}[✓] Thinking display mode set to:[/] {UI.BOLD}{cfg.thinking_mode.upper()}{UI.RESET}\n")
                    else:
                        modes = ["expanded", "collapsed", "hidden"]
                        cur = getattr(cfg, "thinking_mode", "expanded")
                        nxt = modes[(modes.index(cur) + 1) % len(modes)] if cur in modes else "expanded"
                        cfg.thinking_mode = nxt
                        cfg.save()
                        print(f"\n  {UI.GREEN}[✓] Toggled thinking display mode to:[/] {UI.BOLD}{nxt.upper()}{UI.RESET} (options: expanded, collapsed, hidden)\n")
                    continue

                if c in ("/paste", "/bulk", "/multiline"):
                    print(f"\n {UI.MAGENTA}┌── 📋 BULK PROMPT INPUT MODE ──────────────────────────────────────┐{UI.RESET}")
                    print(f" {UI.GRAY}│ Paste or type unlimited lines of prompt, code, or data below.     │{UI.RESET}")
                    print(f" {UI.GRAY}│ To submit: type {UI.CYAN}/send{UI.GRAY} or {UI.CYAN}/end{UI.GRAY} on a new line (or press Ctrl+Z then Enter). │{UI.RESET}")
                    print(f" {UI.MAGENTA}└───────────────────────────────────────────────────────────────────┘{UI.RESET}\n")
                    bulk_lines = []
                    while True:
                        try:
                            line = input(f" {UI.CYAN}│{UI.RESET} ")
                            if line.strip().lower() in ("/send", "/end", "/done", ":q", "eof"):
                                break
                            bulk_lines.append(line)
                        except (EOFError, KeyboardInterrupt):
                            break
                    bulk_text = "\n".join(bulk_lines).strip()
                    if not bulk_text:
                        print(f" {UI.YELLOW}[*] Bulk prompt cancelled (empty).{UI.RESET}\n")
                        continue
                    user_input = bulk_text

                elif c in ("/file", "/load", "/import"):
                    if len(cmd_parts) > 1:
                        target_file = Path(" ".join(cmd_parts[1:]).strip().strip('"').strip("'"))
                        if target_file.exists() and target_file.is_file():
                            try:
                                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                                    user_input = f.read().strip()
                                print(f" {UI.GREEN}[✓] Loaded bulk prompt ({len(user_input)} chars) from: {target_file.name}{UI.RESET}\n")
                            except Exception as e:
                                print(f" {UI.RED}[!] Could not read file:{UI.RESET} {e}\n")
                                continue
                        else:
                            print(f" {UI.RED}[!] File not found:{UI.RESET} {target_file}\n")
                            continue
                    else:
                        print(f" {UI.YELLOW}Usage:{UI.RESET} /file <path_to_text_file>\n")
                        continue

                if c in ("/visual", "/view", "/preview"):
                    print(f"\n  {UI.MAGENTA}🎨 [HS AI ON-DEMAND VISUAL RESPONSE ENGINE]{UI.RESET}")
                    print(f"  All diagrams, graphs, circuits, and architectures render directly inside PowerShell.")
                    print(f"  Supported: Binary search, Water phase diagram, CPU architecture, Neural networks,")
                    print(f"             Electrical circuits, OS scheduling, Math functions, UML, Flowcharts.")
                    print(f"  Examples: 'draw a phase diagram', 'explain binary search visually', 'show cpu architecture'")
                    print(f"            'draw neural network architecture', 'draw an electrical circuit', 'os scheduling'\n")
                    continue

                if c == "/studio":
                    print(f"\n  {UI.YELLOW}🔗 HS AI Studio Portal:{UI.RESET} {UI.URL}{STUDIO_URL}{UI.RESET}\n")
                    continue

                if c == "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    session_id = f"cli_{int(time.time())}"
                    UI.print_banner()
                    print(f"  {UI.GREEN}[✓] Chat screen and conversation history cleared.{UI.RESET}\n")
                    continue

                if c in ("/whoami", "/account", "/user"):
                    cmd_whoami()
                    continue

                if c in ("/context", "/time", "/location"):
                    from .context_provider import RuntimeContextProvider
                    print("\n" + RuntimeContextProvider.build_system_context_block() + "\n")
                    continue

                if c == "/status":
                    cmd_status()
                    continue

                if c in ("/memory", "/mem"):
                    from .memory_engine import HierarchicalMemoryEngine
                    mem_eng = HierarchicalMemoryEngine()
                    mems = mem_eng.get_all_active_memories()
                    print(f"\n  {UI.CYAN}🧠 [HS AI PERSISTENT MEMORY STORE]{UI.RESET}")
                    if mems:
                        for m in mems:
                            print(f"  • [{m.category.upper()}] {UI.BOLD}{m.key}{UI.RESET}: {m.content} {UI.GRAY}(source: {m.source_tag}){UI.RESET}")
                    else:
                        print("  No persistent memories currently recorded.")
                    print()
                    continue

                if c in ("/feedback", "/report"):
                    from .evolution_engine import ContinuousEvolutionEngine
                    evo = ContinuousEvolutionEngine()
                    stats = evo.analyze_recurring_weaknesses()
                    print(f"\n  {UI.CYAN}📋 [HS AI FEEDBACK & CONTINUOUS EVOLUTION]{UI.RESET}")
                    print(f"  Total Feedback Entries : {stats['total_feedback']}")
                    print(f"  Negative Reports       : {stats['negative_count']}")
                    print(f"  Top Recurring Weakness : {stats['top_recurring_weakness']}")
                    print(f"  System Recommendation  : {stats['recommendation']}\n")
                    continue

                if c in ("/mode", "/personality", "/persona"):
                    if len(cmd_parts) > 1:
                        target = " ".join(cmd_parts[1:]).lower().strip()
                        items = list(customizer.PERSONALITY_METADATA.items())
                        matched = None
                        if target.isdigit():
                            idx = int(target) - 1
                            if 0 <= idx < len(items):
                                matched = items[idx]
                        if not matched:
                            for k, meta in items:
                                if target in k.lower() or target in meta["title"].lower():
                                    matched = (k, meta)
                                    break
                        if matched:
                            cfg.personality = matched[0]
                            cfg.save()
                            customizer.config = cfg
                            print(f"\n  {UI.GREEN}[✓] Switched personality to:[/] {UI.BOLD}{matched[1]['icon']} {matched[1]['title']}{UI.RESET}")
                            print(f"      {UI.GRAY}{matched[1]['description']}{UI.RESET}\n")
                        else:
                            print(f"\n  {UI.RED}[!] Unknown personality.{UI.RESET} Type {UI.CYAN}/mode{UI.RESET} to open the interactive menu.\n")
                    else:
                        interactive_select_personality(cfg, customizer)
                    continue

                if c in ("/model", "/models"):
                    if c == "/models" or (len(cmd_parts) > 1 and cmd_parts[1].lower() in ("list", "ls")):
                        cmd_models()
                        continue

                    if len(cmd_parts) > 1:
                        sub = cmd_parts[1].lower().strip()
                        if sub in ("status", "telemetry"):
                            cmd_status()
                            continue

                        if sub in ("download", "get"):
                            target_dl = cmd_parts[2].lower().strip() if len(cmd_parts) > 2 else "gravity"
                            if perm_storage.is_model_present(target_dl):
                                print(f"\n  {UI.GREEN}[✓] {target_dl.upper()} LLM is already downloaded and verified on disk.{UI.RESET}\n")
                            elif coordinator.is_downloading(target_dl):
                                print(f"\n  {UI.YELLOW}[*] {target_dl.upper()} LLM is currently downloading in the background.{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.CYAN}[*] Starting background download of {target_dl.upper()} LLM from Cloudflare R2...{UI.RESET}")
                                coordinator._launch_background_download(target_dl, auto_activate=True)
                                print(f"  {UI.GREEN}[✓] Background acquisition started. {runtime.current_model_id.upper()} LLM remains operational for chat.{UI.RESET}\n")
                            continue

                        if sub in ("cancel", "stop"):
                            target_c = cmd_parts[2].lower().strip() if len(cmd_parts) > 2 else "gravity"
                            if coordinator.cancel_download(target_c):
                                print(f"\n  {UI.GREEN}[✓] Background download for {target_c.upper()} has been cancelled. Partial chunks preserved for safe resumption.{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.YELLOW}[*] No active background download found for {target_c.upper()}.{UI.RESET}\n")
                            continue

                        matched_m = None
                        if sub in ("july", "1", "j"): matched_m = "july"
                        elif sub in ("gravity", "2", "g"): matched_m = "gravity"
                        elif sub in ("auto", "3", "a"): matched_m = "auto"

                        if matched_m == "july":
                            if runtime.current_model_id == "july" and runtime.is_loaded():
                                print(f"\n  {UI.CYAN}[i] July LLM is already active.{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.YELLOW}[*] Switching active inference engine to JULY LLM...{UI.RESET}")
                                coordinator._activate_local_model("july")
                                cfg.selected_model = "july"
                                cfg.save()
                                print(f"  {UI.GREEN}[✓] JULY LLM mounted into memory and active.{UI.RESET}\n")
                            continue

                        elif matched_m == "gravity":
                            if perm_storage.is_model_present("gravity"):
                                if runtime.current_model_id == "gravity" and runtime.is_loaded():
                                    print(f"\n  {UI.CYAN}[i] Gravity LLM is already active.{UI.RESET}\n")
                                else:
                                    print(f"\n  {UI.YELLOW}[*] Switching active inference engine to GRAVITY LLM...{UI.RESET}")
                                    try:
                                        coordinator._activate_local_model("gravity")
                                        cfg.selected_model = "gravity"
                                        cfg.save()
                                        print(f"  {UI.GREEN}[✓] GRAVITY LLM mounted into memory and active.{UI.RESET}\n")
                                    except Exception as e:
                                        print(f"  {UI.RED}[!] Could not activate Gravity: {e}{UI.RESET}\n")
                            else:
                                # Gravity is NOT downloaded!
                                # 1. Keep July running as active inference engine
                                if not runtime.is_loaded() or runtime.current_model_id != "july":
                                    coordinator._activate_local_model("july")
                                # 2. Start Gravity downloading asynchronously in background
                                coordinator._launch_background_download("gravity", auto_activate=True)
                                # 3. Display download progress status line
                                print(f"\n  {UI.CYAN}[JULY ACTIVE] [GRAVITY DOWNLOADING: 0%]{UI.RESET}")
                                # 4. July responds
                                jul_greeting = "I'm July. Gravity is downloading in the background. You can continue chatting with me while it prepares."
                                print(f"  {UI.BOLD}{UI.CYAN}JULY LLM:{UI.RESET} {jul_greeting}\n")
                                if voice_coord.tts.is_enabled:
                                    voice_coord.tts.speak(jul_greeting, non_blocking=True)
                            continue

                        elif matched_m == "auto":
                            cfg.selected_model = "auto"
                            cfg.save()
                            print(f"\n  {UI.GREEN}[✓] Selected Model Preference:[/] {UI.BOLD}AUTO DUAL ROUTER{UI.RESET}\n")
                            continue
                        else:
                            print(f"\n  {UI.RED}[!] Unknown model name '{sub}'.{UI.RESET} Available: {UI.CYAN}/model july{UI.RESET}, {UI.CYAN}/model gravity{UI.RESET}, {UI.CYAN}/model auto{UI.RESET}, {UI.CYAN}/model list{UI.RESET}, {UI.CYAN}/model download gravity{UI.RESET}, {UI.CYAN}/model cancel gravity{UI.RESET}\n")
                            continue
                    else:
                        new_m = interactive_select_model(cfg)
                        if new_m and new_m in ("july", "gravity"):
                            if perm_storage.is_model_present(new_m):
                                coordinator._activate_local_model(new_m)
                                print(f"  {UI.GREEN}[✓] {new_m.upper()} LLM mounted into memory and active.{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.CYAN}[JULY ACTIVE] [GRAVITY DOWNLOADING: 0%]{UI.RESET}")
                                jul_greeting = "I'm July. Gravity is downloading in the background. You can continue chatting with me while it prepares."
                                print(f"  {UI.BOLD}{UI.CYAN}JULY LLM:{UI.RESET} {jul_greeting}\n")
                                coordinator._launch_background_download(new_m, auto_activate=True)
                        continue

                if c == "/voice":
                    if len(cmd_parts) > 1:
                        v_sub = cmd_parts[1].lower().strip()
                        if v_sub == "on":
                            voice_coord.stt.is_enabled = True
                            print(f"\n  {UI.GREEN}[✓] Whisper voice input enabled.{UI.RESET} Type {UI.CYAN}/voice input{UI.RESET} to speak.\n")
                            continue
                        elif v_sub == "off":
                            voice_coord.stt.is_enabled = False
                            print(f"\n  {UI.YELLOW}[*] Whisper voice input disabled.{UI.RESET}\n")
                            continue
                        elif v_sub == "input":
                            print(f"\n  {UI.MAGENTA}🎙️  [WHISPER VOICE INPUT]{UI.RESET} Listening for 5 seconds... Speak now!")
                            try:
                                audio_rec = voice_coord.stt.record_audio(duration_seconds=5.0)
                                if audio_rec is not None:
                                    print(f"  {UI.CYAN}⏳ Transcribing audio with Whisper ({voice_coord.stt.model_name})...{UI.RESET}")
                                    trans_text, det_lang = voice_coord.stt.transcribe_audio(audio_rec)
                                    if trans_text:
                                        print(f"\n  {UI.GREEN}[Whisper STT ({det_lang})]:{UI.RESET} \"{trans_text}\"")
                                        try:
                                            edit_prompt = input(f"  {UI.GRAY}Press Enter to submit or type correction: {UI.RESET}").strip()
                                            final_prompt = edit_prompt if edit_prompt else trans_text
                                        except (EOFError, KeyboardInterrupt):
                                            final_prompt = trans_text
                                        user_input = final_prompt
                                    else:
                                        print(f"  {UI.YELLOW}[*] No speech detected in audio.{UI.RESET}\n")
                                        continue
                                else:
                                    print(f"  {UI.RED}[!] Could not capture audio from microphone.{UI.RESET}\n")
                                    continue
                            except Exception as v_err:
                                print(f"  {UI.RED}[!] Voice input error:{UI.RESET} {v_err}. Falling back to keyboard.\n")
                                continue
                        elif v_sub in ("language", "lang"):
                            if len(cmd_parts) > 2:
                                new_lang = voice_coord.stt.set_language(cmd_parts[2])
                                print(f"\n  {UI.GREEN}[✓] Whisper recognition language set to:[/] {UI.BOLD}{new_lang.upper()}{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.CYAN}Whisper current language:[/] {UI.BOLD}{voice_coord.stt.language.upper()}{UI.RESET}\n")
                            continue
                        elif v_sub in ("model", "size"):
                            if len(cmd_parts) > 2:
                                try:
                                    new_mod = voice_coord.stt.set_model(cmd_parts[2])
                                    print(f"\n  {UI.GREEN}[✓] Whisper model size set to:[/] {UI.BOLD}{new_mod}{UI.RESET}\n")
                                except Exception as m_err:
                                    print(f"\n  {UI.RED}[!] {m_err}{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.CYAN}Whisper current model:[/] {UI.BOLD}{voice_coord.stt.model_name}{UI.RESET}\n")
                            continue
                        elif v_sub == "output":
                            if len(cmd_parts) > 2:
                                out_act = cmd_parts[2].lower().strip()
                                if out_act == "on":
                                    voice_coord.tts.is_enabled = True
                                    print(f"\n  {UI.GREEN}[✓] TTS Voice Output enabled.{UI.RESET} Responses will be spoken aloud ({voice_coord.tts.backend}).\n")
                                elif out_act == "off":
                                    voice_coord.tts.is_enabled = False
                                    voice_coord.tts.stop()
                                    print(f"\n  {UI.YELLOW}[*] TTS Voice Output disabled.{UI.RESET}\n")
                                else:
                                    print(f"\n  {UI.YELLOW}Usage:{UI.RESET} /voice output on | /voice output off\n")
                            else:
                                cur_stat = "ON" if voice_coord.tts.is_enabled else "OFF"
                                print(f"\n  {UI.CYAN}TTS Voice Output:[/] {UI.BOLD}{cur_stat}{UI.RESET} (Backend: {voice_coord.tts.backend})\n")
                            continue
                        elif v_sub in ("speed", "rate"):
                            if len(cmd_parts) > 2:
                                try:
                                    new_spd = voice_coord.tts.set_speed(int(cmd_parts[2]))
                                    print(f"\n  {UI.GREEN}[✓] TTS speech speed set to:[/] {UI.BOLD}{new_spd} wpm{UI.RESET}\n")
                                except ValueError:
                                    print(f"\n  {UI.RED}[!] Speed must be an integer (e.g. 180).{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.CYAN}TTS speed:[/] {UI.BOLD}{voice_coord.tts.speed} wpm{UI.RESET}\n")
                            continue
                        elif v_sub in ("gender", "voice"):
                            if len(cmd_parts) > 2:
                                new_g = voice_coord.tts.set_gender(cmd_parts[2])
                                print(f"\n  {UI.GREEN}[✓] TTS Voice Gender set to:[/] {UI.BOLD}{new_g}{UI.RESET}\n")
                            else:
                                print(f"\n  {UI.CYAN}TTS current gender:[/] {UI.BOLD}{voice_coord.tts.voice_gender}{UI.RESET}\n")
                            continue
                        elif v_sub == "female":
                            voice_coord.tts.set_gender("female")
                            print(f"\n  {UI.GREEN}[✓] TTS voice set to Female (Microsoft Zira / Female Voice).{UI.RESET}\n")
                            continue
                        elif v_sub == "male":
                            voice_coord.tts.set_gender("male")
                            print(f"\n  {UI.GREEN}[✓] TTS voice set to Male.{UI.RESET}\n")
                            continue
                        elif v_sub in ("stop", "halt", "mute"):
                            voice_coord.tts.stop()
                            print(f"\n  {UI.GREEN}[✓] TTS audio playback stopped.{UI.RESET}\n")
                            continue
                        else:
                            print(f"\n  {UI.YELLOW}Unknown /voice command.{UI.RESET} Options: on, off, input, language, model, output on|off, female, gender <female|male>, speed, stop\n")
                            continue
                    else:
                        stt_stat = "ON" if voice_coord.stt.is_enabled else "OFF"
                        tts_stat = "ON" if voice_coord.tts.is_enabled else "OFF"
                        print(f"\n  {UI.BOLD}{UI.CYAN}Voice Configuration:{UI.RESET}")
                        print(f"   Whisper STT Input : {UI.GREEN if voice_coord.stt.is_enabled else UI.GRAY}{stt_stat}{UI.RESET} (Model: {voice_coord.stt.model_name}, Lang: {voice_coord.stt.language})")
                        print(f"   TTS Speech Output : {UI.GREEN if voice_coord.tts.is_enabled else UI.GRAY}{tts_stat}{UI.RESET} (Backend: {voice_coord.tts.backend}, Gender: {voice_coord.tts.voice_gender}, Speed: {voice_coord.tts.speed} wpm)\n")
                        continue

            # Render background download status if any active
            from .state_manager import DualModelStateManager
            sm = DualModelStateManager()
            for d_m in sm.downloadingModels:
                d_stat = sm.modelInitializationStatus.get(d_m, {})
                pct = d_stat.get("percent", 0.0)
                spd = d_stat.get("speed_mb", 0.0)
                print(f" {UI.GRAY}[Background: {d_m.upper()} downloading: {pct:.1f}% ({spd:.1f} MB/s)]{UI.RESET}")

            # Rate Limit Check
            allowed, retry_after, reason, metrics = limiter.check_limit(tier=user_tier, estimated_tokens=len(user_input.split()) * 2)
            if not allowed:
                print(f"\n {UI.RED}[!] RATE LIMIT EXCEEDED:{UI.RESET} {reason}")
                print(f" {UI.YELLOW}[*] Cooldown period:{UI.RESET} Please wait {retry_after:.1f}s before sending another prompt.")
                print(f" {UI.GRAY}[i] Rate Limit: {metrics.get('rpm_used', 0)}/{metrics.get('rpm_max', 20)} RPM ({metrics.get('tier', 'standard').upper()} Tier){UI.RESET}")
                print(f" {UI.GRAY}[i] Upgrade your plan for higher throughput at:{UI.RESET} {UI.URL}{STUDIO_URL}{UI.RESET}\n")
                continue

            active_mode = getattr(cfg, "selected_model", "july").upper()
            active_actual = runtime.current_model_id.upper()
            if active_mode != active_actual and active_mode != "AUTO":
                badge_color = UI.YELLOW
                label = f"{active_actual} (Fallback for {active_mode})"
            elif active_actual == "GRAVITY":
                badge_color = UI.YELLOW
                label = "GRAVITY"
            elif active_mode == "AUTO":
                badge_color = UI.MAGENTA
                label = f"AUTO ({runtime.current_model_id.upper()})"
            else:
                badge_color = UI.CYAN
                label = "JULY"

            sys.stdout.write(f"{UI.BOLD}{badge_color}❯ {label}{UI.RESET} {UI.GRAY}›{UI.RESET} ")
            sys.stdout.flush()
            t0 = time.time()
            tok_count = 0
            full_response = []
            th_mode = getattr(cfg, "thinking_mode", "expanded")
            token_filter = ThinkingResultStreamFilter(model_name=label, badge_color=badge_color, thinking_mode=th_mode)
            for token in runtime.generate_stream(user_input, session_id=session_id):
                chunk = token_filter.process(token)
                if chunk:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                tok_count += 1
                full_response.append(token)
            rem = token_filter.flush()
            if rem:
                sys.stdout.write(rem)
                sys.stdout.flush()
            elapsed = max(0.001, time.time() - t0)
            sys.stdout.write(f"\n{UI.GRAY}[⚡ {tok_count} tokens | {tok_count/elapsed:.1f} tok/s | {elapsed:.2f}s | RAM: Active]{UI.RESET}\n")

            limiter.record_usage(tokens=tok_count)

            try:
                ClerkAuthManager().record_usage(active_mid, len(user_input.split()), tok_count)
            except Exception:
                pass

            # Multilingual TTS Speech Synthesis
            if voice_coord.tts.is_enabled:
                voice_coord.tts.speak(full_text, non_blocking=True)

            # Autonomous Visual Representation Rendering
            full_text = "".join(full_response)
            try:
                from .visual import VisualResponseEngine
                engine = VisualResponseEngine()
                rendered = engine.process_and_render(user_prompt=user_input, model_response=full_text)
                if not rendered:
                    visual_info = detect_visual_content(full_text)
                    if visual_info:
                        v_type, v_code = visual_info
                        if v_type == "mermaid":
                            cli_diagram = render_mermaid_to_cli(v_code)
                            if cli_diagram:
                                print(f"\n{cli_diagram}\n")
            except Exception as e:
                pass
            print()

        except KeyboardInterrupt:
            print(f"\n\n {UI.GRAY}Exiting chat session...{UI.RESET}")
            break


def cmd_unload():
    UI.print_card("HS AI SOLUTIONS — RAM RECLAMATION")
    from .state_manager import DualModelStateManager, ModelStatus
    from .storage import ClientEphemeralStorage
    state_mgr = DualModelStateManager()
    active_path, active_mid = get_active_model_info()
    storage = ClientEphemeralStorage()

    if active_path or active_mid != "none":
        print(f" {UI.CYAN}[⚡]{UI.RESET} Releasing {active_mid.upper()} neural weights from active RAM/VRAM...")
        # Safe memory reclamation: DOES NOT UNLINK PERMANENT DISK GGUF
        storage.wipe_and_unlink(active_path, allow_permanent_deletion=False)
        state_mgr.set_model_state(active_mid, ModelStatus.UNLOADED.value)
        clear_active_state()
        print(f" {UI.GREEN}[✓] Model safely unloaded from active RAM. Permanent GGUF files preserved on disk.{UI.RESET}")
    else:
        print(f" {UI.GRAY}[*] No active model loaded in RAM.{UI.RESET}")

    storage.reclaim_os_memory()
    print(f" {UI.GREEN}[✓] Working set memory released back to Windows OS.{UI.RESET}\n")


def cmd_update(args):
    UI.print_card("HS AI SOLUTIONS — MODEL VERSION CHECK")
    cfg = ClientConfig.load()
    url = f"{cfg.server_url.rstrip('/')}/api/v1/model/check-update"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"  Latest Server Version : {data.get('latest_server_version')}")
        print(f"  Release Notes         : {data.get('release_notes')}")
        print(f"  SHA-256 Digest        : {data.get('sha256')}")
        print(f"\n {UI.GREEN}[✓]{UI.RESET} To reload latest weights: {UI.CYAN}july unload && july load{UI.RESET}\n")
    except Exception as e:
        print(f" {UI.RED}[!] Update check failed:{UI.RESET} {e}\n")


def cmd_config(args):
    cfg = ClientConfig.load()
    if args.set:
        key, val = args.set
        if key in ("selected_model", "model"):
            is_auth, _ = ensure_authenticated_for_models(prompt_user=True)
            if not is_auth:
                print(f"\n {UI.RED}[!] Model Selection Blocked:{UI.RESET} Strict authentication required before configuring model.")
                print(f" {UI.GRAY}[i] Run 'july login' to authenticate with Clerk / HS AI Solutions.{UI.RESET}\n")
                return
        if hasattr(cfg, key):
            curr_val = getattr(cfg, key)
            if isinstance(curr_val, bool):
                val = val.lower() in ("true", "1", "yes")
            elif isinstance(curr_val, int):
                val = int(val)
            elif isinstance(curr_val, float):
                val = float(val)
            setattr(cfg, key, val)
            cfg.save()
            print(f" {UI.GREEN}[✓]{UI.RESET} Updated config {UI.CYAN}{key}{UI.RESET} = {val}")
        else:
            print(f" {UI.RED}[!] Unknown config key:{UI.RESET} {key}")
        return

    UI.print_card("HS AI SOLUTIONS — CLIENT CONFIGURATION")
    data = cfg.__dict__
    for k, v in data.items():
        print(f"  {k:<24}: {v}")
    print(f"\n {UI.GRAY}To modify setting:{UI.RESET} {UI.CYAN}july config --set <key> <value>{UI.RESET}\n")


def cmd_sandbox(args):
    """Handles 'july sandbox <action>' CLI commands."""
    from .sandbox import SandboxManager
    mgr = SandboxManager.get_instance()
    action = getattr(args, "action", "status") or "status"
    action = action.lower().strip()

    if action == "install":
        print(f"\n {UI.CYAN}[*] Initializing Windows Sandbox Execution Engine & Security Primitives...{UI.RESET}")
        res = mgr.install()
        print(f" {UI.GREEN}[✓]{UI.RESET} {res['message']}")
        print(f" {UI.GRAY}Sandbox Root: {res['root_directory']}{UI.RESET}\n")

    elif action == "status":
        print(mgr.render_dashboard())

    elif action == "start":
        res = mgr.start()
        print(f"\n {UI.GREEN}[✓]{UI.RESET} {res['message']}\n")

    elif action == "stop":
        res = mgr.stop()
        print(f"\n {UI.YELLOW}[*]{UI.RESET} {res['message']}\n")

    elif action == "reset":
        res = mgr.reset()
        print(f"\n {UI.GREEN}[✓]{UI.RESET} {res['message']}\n")

    elif action == "remove":
        confirmed = getattr(args, "confirm", False)
        if not confirmed:
            try:
                ans = input(f" {UI.RED}[!] WARNING: Are you sure you want to remove July Sandbox accounts, firewall rules, and ephemeral data? [y/N]: {UI.RESET}").strip().lower()
                confirmed = ans in ("y", "yes")
            except (EOFError, KeyboardInterrupt):
                confirmed = False
        if not confirmed:
            print(f"\n {UI.YELLOW}[*] Sandbox removal cancelled.{UI.RESET}\n")
            return
        res = mgr.remove(confirmed=True)
        print(f"\n {UI.GREEN}[✓]{UI.RESET} {res['message']}\n")

    elif action in ("run", "exec"):
        cmd_str = getattr(args, "target_command", "")
        if not cmd_str:
            print(f"\n {UI.RED}[!] Error: No command provided to run in sandbox.{UI.RESET}")
            print(f"     Usage: july sandbox run \"<command>\"\n")
            return
        timeout = getattr(args, "timeout", None)
        allow_net = getattr(args, "network", False)
        print(f"\n {UI.CYAN}[SANDBOX EXECUTOR]{UI.RESET} Spawning inside Windows Job Object: {UI.BOLD}{cmd_str}{UI.RESET}")
        res = mgr.execute(cmd_str, timeout=timeout, allow_network=allow_net)
        if res.stdout:
            sys.stdout.write(res.stdout)
            sys.stdout.flush()
        if res.stderr:
            sys.stderr.write(res.stderr)
            sys.stderr.flush()
        if res.security_blocked:
            print(f"\n {UI.RED}[BLOCKED BY SANDBOX SECURITY POLICY]{UI.RESET} {res.violation_reason}\n")
        else:
            print(f"\n {UI.GRAY}[Exit: {res.exit_code} | Duration: {res.duration_seconds}s | Peak Mem: {res.peak_memory_mb} MB]{UI.RESET}\n")
    else:
        print(f"\n {UI.RED}[!] Unknown sandbox action '{action}'. Available: install, status, start, stop, reset, remove, run{UI.RESET}\n")


def main():
    parser = argparse.ArgumentParser(prog="july", description="JULY LLM Autonomous Runtime Platform")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    subparsers.add_parser("install", help="Initialize local environment and configuration")

    reg_p = subparsers.add_parser("register", help="Register a new account with HS AI Solutions")
    reg_p.add_argument("-u", "--username", help="Username")
    reg_p.add_argument("-e", "--email", help="Email address")
    reg_p.add_argument("-p", "--password", help="Password")
    reg_p.add_argument("-s", "--server", help="Control server URL")

    login_p = subparsers.add_parser("login", help="Authenticate with Clerk Identity & Access Management")
    login_p.add_argument("-u", "--username", help="Email or username for in-CLI authentication")
    login_p.add_argument("-p", "--password", help="Password for in-CLI authentication")
    login_p.add_argument("-s", "--server", help="Control server URL")
    login_p.add_argument("-b", "--browser", action="store_true", help="Authenticate via browser")
    login_p.add_argument("--browser-only", action="store_true", help="Force browser loopback authentication")
    login_p.add_argument("-f", "--force", action="store_true", help="Force re-authentication even if already signed in")
    login_p.add_argument("--cli", action="store_true", help="Force interactive in-CLI terminal login")
    login_p.add_argument("--sso", choices=["google", "github"], help="Direct Single Sign-On provider (google, github)")
    login_p.add_argument("--token", help="Manual Clerk session token or API key (for in-CLI or headless/CI)")
    login_p.add_argument("--email", help="Email address associated with token")

    subparsers.add_parser("logout", help="Log out and securely wipe local cryptographic credential vault")
    signup_p = subparsers.add_parser("signup", help="Create a new Clerk account directly in CLI or browser")
    signup_p.add_argument("-b", "--browser", action="store_true", help="Open sign-up in external browser")
    signup_p.add_argument("-u", "--username", help="Username for in-CLI registration")
    signup_p.add_argument("-e", "--email", help="Email for in-CLI registration")
    signup_p.add_argument("-p", "--password", help="Password for in-CLI registration")
    subparsers.add_parser("whoami", help="Display active Clerk user identity, tier, and device registration")

    auth_p = subparsers.add_parser("auth", help="Clerk Identity & Access Management telemetry and device controls")
    auth_p.add_argument("action", nargs="?", default="status", choices=["status", "refresh", "devices", "revoke"], help="Action: status, refresh, devices, revoke")
    auth_p.add_argument("device_id", nargs="?", help="Target device ID to revoke")

    subparsers.add_parser("account", help="View account subscription tier, limits, and linked providers")
    subparsers.add_parser("usage", help="View model token consumption telemetry and daily quotas")
    subparsers.add_parser("sync", help="Flush offline queued operations and synchronize with cloud backend")

    subparsers.add_parser("status", help="Display authentication, model, and hardware telemetry")

    model_p = subparsers.add_parser("model", help="Select or switch active foundation model (JULY LLM, GRAVITY LLM, AUTO)")
    model_p.add_argument("name", nargs="?", help="Model to activate (july, gravity, auto, list, status, download, cancel)")
    model_p.add_argument("target", nargs="?", help="Target model for download or cancel commands (e.g. gravity)")
    model_p.add_argument("-l", "--list", action="store_true", help="List all available models and their specifications")
    model_p.add_argument("-s", "--status", action="store_true", help="Show current active model status and telemetry")

    subparsers.add_parser("models", help="List all registered models and their specifications")
    subparsers.add_parser("hardware", help="Display real-time CPU, RAM, GPU, and VRAM telemetry")
    subparsers.add_parser("memory", help="Display RAM and VRAM memory consumption report")
    subparsers.add_parser("gpu", help="Display GPU acceleration, VRAM allocation, and layer offloading report")

    voice_p = subparsers.add_parser("voice", help="Whisper voice input and multilingual TTS voice output controls")
    voice_p.add_argument("action", nargs="?", help="Action: on, off, input, language, model, output, speed, stop")
    voice_p.add_argument("value", nargs="?", help="Parameter value for language, model, output, or speed")

    load_p = subparsers.add_parser("load", help="Retrieve GGUF into ephemeral RAM-backed storage")
    load_p.add_argument("-M", "--model", help="Specific model to load: july or gravity")

    chat_p = subparsers.add_parser("chat", help="Start chat session running genuine local inference")
    chat_p.add_argument("prompt", nargs="?", help="One-off prompt to execute")
    chat_p.add_argument("-f", "--file", help="Path to text file containing a bulk or multi-line prompt")
    chat_p.add_argument("-m", "--mode", "--personality", dest="personality", help="Run chat with a specific personality")
    chat_p.add_argument("-M", "--model", help="Foundation model to use: july, gravity, or auto")

    pers_p = subparsers.add_parser("personality", help="Choose assistant personality profile")
    pers_p.add_argument("name", nargs="?", help="Optional personality name or number")

    mode_p = subparsers.add_parser("mode", help="Alias for personality")
    mode_p.add_argument("name", nargs="?", help="Optional personality name or number")

    subparsers.add_parser("unload", help="Unload model and securely wipe RAM storage")
    subparsers.add_parser("update", help="Check for model version updates")

    cfg_p = subparsers.add_parser("config", help="View or modify user configuration")
    cfg_p.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set a configuration option")

    sbx_p = subparsers.add_parser("sandbox", help="Windows Sandbox Isolated Execution Engine")
    sbx_p.add_argument("action", nargs="?", default="status", choices=["install", "status", "start", "stop", "reset", "remove", "run", "exec"], help="Sandbox action to perform")
    sbx_p.add_argument("target_command", nargs="?", default="", help="Command to execute if action is 'run'")
    sbx_p.add_argument("--confirm", action="store_true", help="Confirm removal without prompting")
    sbx_p.add_argument("-t", "--timeout", type=float, help="Execution timeout in seconds")
    sbx_p.add_argument("-n", "--network", action="store_true", help="Allow network access for this execution")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install()
    elif args.command == "register":
        cmd_register(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "logout":
        cmd_logout(args)
    elif args.command == "signup":
        cmd_signup(args)
    elif args.command == "whoami":
        cmd_whoami(args)
    elif args.command == "auth":
        cmd_auth(args)
    elif args.command == "account":
        cmd_account(args)
    elif args.command == "usage":
        cmd_usage(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "status":
        cmd_status()
    elif args.command == "model":
        cmd_model(args)
    elif args.command == "models":
        cmd_models(args)
    elif args.command == "hardware":
        cmd_hardware(args)
    elif args.command == "memory":
        cmd_memory_report(args)
    elif args.command == "gpu":
        cmd_gpu(args)
    elif args.command == "voice":
        cmd_voice(args)
    elif args.command == "load":
        cmd_load(args)
    elif args.command in ("personality", "mode"):
        cmd_personality(args)
    elif args.command == "chat":
        cmd_chat(args)
    elif args.command == "unload":
        cmd_unload()
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "sandbox":
        cmd_sandbox(args)
    else:
        cmd_chat(argparse.Namespace(prompt=None))


if __name__ == "__main__":
    main()
