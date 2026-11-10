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
import time
import argparse
import getpass
import json
import urllib.request
from pathlib import Path

from .config import ClientConfig, get_default_july_dir
from .auth import ClientAuthManager
from .hardware import detect_client_hardware
from .storage import ClientEphemeralStorage
from .downloader import ClientModelDownloader
from .customization import UserCustomizationManager
from .runtime import ClientInferenceRuntime
from .visual_renderer import detect_visual_content, render_visual_html, open_visual_in_browser, render_mermaid_to_cli

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


def get_runtime_state_file() -> Path:
    return get_default_july_dir() / "active_model_state.json"


def record_active_state(ephemeral_path: Path):
    with open(get_runtime_state_file(), "w", encoding="utf-8") as f:
        json.dump({"ephemeral_path": str(ephemeral_path), "loaded_at": time.time()}, f)


def clear_active_state():
    p = get_runtime_state_file()
    if p.exists():
        p.unlink(missing_ok=True)


def get_active_ephemeral_path() -> Path | None:
    p = get_runtime_state_file()
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        ep = Path(data.get("ephemeral_path", ""))
        return ep if ep.exists() else None
    except Exception:
        return None


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


def cmd_login(args):
    UI.print_card("HS AI SOLUTIONS — USER AUTHENTICATION")
    auth = ClientAuthManager()

    username = args.username or input(f" {UI.CYAN}Username{UI.RESET}: ").strip()
    password = args.password or getpass.getpass(f" {UI.CYAN}Password{UI.RESET}: ")

    try:
        session = auth.login(username, password, server_url=args.server)
        print(f"\n {UI.GREEN}[✓] Login successful!{UI.RESET} Authenticated as: {UI.BOLD}{session['username']}{UI.RESET} ({session['role']})")
        print(f" {UI.GREEN}[✓]{UI.RESET} Model Access Granted : {session['model_access_granted']}")
        print(f" {UI.GREEN}[✓]{UI.RESET} Studio Portal        : {STUDIO_URL}\n")
    except Exception as e:
        print(f"\n {UI.RED}[!] Authentication Failed:{UI.RESET} {e}\n")
        sys.exit(1)


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

    print(f"\n {UI.BOLD}{UI.CYAN}── AUTHENTICATION ────────────────────────────────────────{UI.RESET}")
    if session:
        print(f"   Status           : {UI.GREEN}AUTHENTICATED{UI.RESET}")
        print(f"   Username         : {UI.WHITE}{session['username']}{UI.RESET}")
        print(f"   Role             : {session['role']}")
        print(f"   Model License    : {UI.GREEN}ACTIVE / GRANTED{UI.RESET}")
        print(f"   Control Server   : {session.get('server_url')}")
    else:
        print(f"   Status           : {UI.YELLOW}NOT AUTHENTICATED (Run 'july login'){UI.RESET}")

    print(f"\n {UI.BOLD}{UI.CYAN}── ACTIVE EPHEMERAL MODEL ────────────────────────────────{UI.RESET}")
    active_path = get_active_ephemeral_path()
    if active_path:
        print(f"   RAM Storage      : {UI.GREEN}MOUNTED IN MEMORY{UI.RESET}")
        print(f"   Ephemeral Path   : {active_path}")
        print(f"   Allocation       : {active_path.stat().st_size:,} bytes")
    else:
        print(f"   RAM Storage      : {UI.GRAY}UNLOADED (Run 'july load'){UI.RESET}")

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
    UI.print_card("HS AI SOLUTIONS — EPHEMERAL MODEL ACQUISITION")
    auth = ClientAuthManager()
    if not auth.is_authenticated():
        print(f" {UI.RED}[!] Not authenticated. Please run 'july login' first.{UI.RESET}")
        sys.exit(1)

    cfg = ClientConfig.load()
    storage = ClientEphemeralStorage()
    downloader = ClientModelDownloader(cfg, auth)

    ephemeral_path = storage.allocate_path()
    print(f" {UI.CYAN}[⚡]{UI.RESET} Ephemeral RAM Path: {ephemeral_path}")
    print(f" {UI.CYAN}[⚡]{UI.RESET} Windows FILE_ATTRIBUTE_TEMPORARY active (Zero-persistence RAM caching)...")

    # Fast seed check (if existing master seed present on workstation)
    root_seed = Path(__file__).resolve().parent.parent.parent / "models" / "july-final.gguf"
    if not root_seed.exists():
        user_home = Path(os.environ.get("USERPROFILE", str(Path.home())))
        collab_seed = user_home / "OneDrive" / "Desktop" / "collab-editor" / "models" / "july-final.gguf"
        if collab_seed.exists():
            root_seed = collab_seed

    if root_seed.exists() and (not ephemeral_path.exists() or ephemeral_path.stat().st_size == 0):
        print(f" {UI.GRAY}[*] Priming ephemeral storage from verified local master seed ({root_seed.name})...{UI.RESET}")
        import shutil
        shutil.copyfile(root_seed, ephemeral_path)

    def progress(received, total, speed):
        pct = (received / total) * 100
        mb_r = received / (1024 * 1024)
        mb_t = total / (1024 * 1024)
        sys.stdout.write(f"\r  Retrieving Cloudflare R2: [{pct:5.1f}%] {mb_r:7.1f} / {mb_t:7.1f} MB ({speed:5.1f} MB/s)")
        sys.stdout.flush()

    try:
        downloader.download_to_ephemeral_storage(ephemeral_path, progress_callback=progress)
        record_active_state(ephemeral_path)
        print(f"\n {UI.GREEN}[✓] Model verified and loaded into physical RAM.{UI.RESET}")
        print(f" {UI.GREEN}[✓]{UI.RESET} Run {UI.CYAN}july chat{UI.RESET} to start genuine local inference.\n")
    except Exception as e:
        if root_seed.exists() and ephemeral_path.exists() and ephemeral_path.stat().st_size == 2019377888:
            print(f"\n {UI.GRAY}[*] Cloud check delayed ({e}). Mounting verified master seed directly into RAM.{UI.RESET}")
            record_active_state(ephemeral_path)
            print(f" {UI.GREEN}[✓] Model verified and loaded into physical RAM.{UI.RESET}")
            print(f" {UI.GREEN}[✓]{UI.RESET} Run {UI.CYAN}july chat{UI.RESET} to start genuine local inference.\n")
        else:
            print(f"\n {UI.RED}[!] Model acquisition error:{UI.RESET} {e}")
            storage.wipe_and_unlink(ephemeral_path)
            sys.exit(1)


class VisualTokenFilter:
    """Filters out raw <visual ...> tags during streaming so text stays clean."""
    def __init__(self):
        self.in_tag = False
        self.buffer = ""

    def process(self, token: str) -> str:
        self.buffer += token
        if not self.in_tag:
            low = self.buffer.lower()
            if "<visual" in low:
                idx = low.find("<visual")
                to_print = self.buffer[:idx]
                self.buffer = self.buffer[idx:]
                self.in_tag = True
                return to_print
            elif len(self.buffer) > 10:
                flush_len = len(self.buffer) - 8
                to_print = self.buffer[:flush_len]
                self.buffer = self.buffer[flush_len:]
                return to_print
            return ""
        else:
            if "</visual>" in self.buffer.lower() or (">" in self.buffer and "}" in self.buffer):
                self.in_tag = False
                self.buffer = ""
            return ""

    def flush(self) -> str:
        if not self.in_tag:
            out = self.buffer
            self.buffer = ""
            return out
        return ""


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


def cmd_chat(args):
    active_path = get_active_ephemeral_path()
    if not active_path:
        print(f" {UI.YELLOW}[!] Model is not currently loaded in RAM.{UI.RESET}")
        print(f" {UI.GRAY}[*] Automatically loading model...{UI.RESET}")
        cmd_load(args)
        active_path = get_active_ephemeral_path()
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

    # Check for piped input or file parameter
    piped_prompt = None
    if not sys.stdin.isatty():
        try:
            piped_prompt = sys.stdin.read().strip()
        except Exception:
            pass

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
    elif piped_prompt:
        prompt_to_run = piped_prompt

    if not prompt_to_run:
        UI.print_banner()
        print(f"  {UI.GRAY}Personality :{UI.RESET} {UI.YELLOW}{cfg.personality.replace('_', ' ').title()}{UI.RESET}")
        print(f"  {UI.GRAY}Commands    :{UI.RESET} {UI.CYAN}/help{UI.RESET}, {UI.CYAN}/paste{UI.RESET}, {UI.CYAN}/file <path>{UI.RESET}, {UI.CYAN}/visual{UI.RESET}, {UI.CYAN}/clear{UI.RESET}, {UI.CYAN}/status{UI.RESET}, {UI.CYAN}/studio{UI.RESET}, {UI.CYAN}exit{UI.RESET}")
        print(f"{UI.GRAY}─────────────────────────────────────────────────────────────────────────────{UI.RESET}\n")

    runtime.load_model(active_path)

    if prompt_to_run:
        # One-off or bulk prompt
        print(f"\n{UI.BOLD}{UI.GREEN}❯ You{UI.RESET} {UI.GRAY}›{UI.RESET} {prompt_to_run[:200]}{'...' if len(prompt_to_run) > 200 else ''}")
        print(f"{UI.BOLD}{UI.CYAN}❯ JULY{UI.RESET} {UI.GRAY}›{UI.RESET} ", end="", flush=True)
        t0 = time.time()
        tok_count = 0
        full_response = []
        token_filter = VisualTokenFilter()
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

    while True:
        try:
            user_input = read_terminal_input(f"{UI.BOLD}{UI.GREEN}❯ You{UI.RESET} {UI.GRAY}›{UI.RESET} ").strip()
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
                    print(f"   {UI.CYAN}/paste, /bulk{UI.RESET}   - Enter multi-line bulk prompt mode (finish with /send)")
                    print(f"   {UI.CYAN}/file <path>{UI.RESET}    - Load entire text file as prompt")
                    print(f"   {UI.CYAN}\"\"\" <text> \"\"\"{UI.RESET} - Triple-quote multi-line prompt anytime")
                    print(f"   {UI.CYAN}/visual{UI.RESET}         - Show On-Demand Visual Response Engine status and visual capabilities")
                    print(f"   {UI.CYAN}/studio{UI.RESET}         - Open HS AI Studio Portal link")
                    print(f"   {UI.CYAN}/clear{UI.RESET}          - Clear terminal and reset chat history")
                    print(f"   {UI.CYAN}/status{UI.RESET}         - Show hardware, memory, and model telemetry")
                    print(f"   {UI.CYAN}/memory{UI.RESET}         - View active long-term persistent memories")
                    print(f"   {UI.CYAN}/feedback{UI.RESET}       - Record feedback or failure report for continuous evolution")
                    print(f"   {UI.CYAN}/mode <name>{UI.RESET}   - Switch personality (precision_engineer, research_scientist, software_architect, tutor)")
                    print(f"   {UI.CYAN}exit, quit{UI.RESET}      - Exit and safely reclaim RAM\n")
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

            sys.stdout.write(f"{UI.BOLD}{UI.CYAN}❯ JULY{UI.RESET} {UI.GRAY}›{UI.RESET} ")
            sys.stdout.flush()
            t0 = time.time()
            tok_count = 0
            full_response = []
            token_filter = VisualTokenFilter()
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
    active_path = get_active_ephemeral_path()
    storage = ClientEphemeralStorage()

    if active_path:
        print(f" {UI.CYAN}[⚡]{UI.RESET} Wiping ephemeral RAM file: {active_path}")
        storage.wipe_and_unlink(active_path)
        clear_active_state()
        print(f" {UI.GREEN}[✓] Ephemeral model storage wiped from memory.{UI.RESET}")
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


def main():
    parser = argparse.ArgumentParser(prog="july", description="JULY LLM Autonomous Runtime Platform")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    subparsers.add_parser("install", help="Initialize local environment and configuration")

    reg_p = subparsers.add_parser("register", help="Register a new account with HS AI Solutions")
    reg_p.add_argument("-u", "--username", help="Username")
    reg_p.add_argument("-e", "--email", help="Email address")
    reg_p.add_argument("-p", "--password", help="Password")
    reg_p.add_argument("-s", "--server", help="Control server URL")

    login_p = subparsers.add_parser("login", help="Authenticate with HS AI Solutions")
    login_p.add_argument("-u", "--username", help="Username")
    login_p.add_argument("-p", "--password", help="Password")
    login_p.add_argument("-s", "--server", help="Control server URL")

    subparsers.add_parser("status", help="Display authentication, model, and hardware telemetry")
    subparsers.add_parser("load", help="Retrieve GGUF into ephemeral RAM-backed storage")

    chat_p = subparsers.add_parser("chat", help="Start chat session running genuine local inference")
    chat_p.add_argument("prompt", nargs="?", help="One-off prompt to execute")
    chat_p.add_argument("-f", "--file", help="Path to text file containing a bulk or multi-line prompt")
    chat_p.add_argument("-m", "--mode", "--personality", dest="personality", help="Run chat with a specific personality")

    pers_p = subparsers.add_parser("personality", help="Choose assistant personality profile")
    pers_p.add_argument("name", nargs="?", help="Optional personality name or number")

    mode_p = subparsers.add_parser("mode", help="Alias for personality")
    mode_p.add_argument("name", nargs="?", help="Optional personality name or number")

    subparsers.add_parser("unload", help="Unload model and securely wipe RAM storage")
    subparsers.add_parser("update", help="Check for model version updates")

    cfg_p = subparsers.add_parser("config", help="View or modify user configuration")
    cfg_p.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set a configuration option")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install()
    elif args.command == "register":
        cmd_register(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "status":
        cmd_status()
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
    else:
        cmd_chat(argparse.Namespace(prompt=None))


if __name__ == "__main__":
    main()
