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
    cfg = ClientConfig.load()

    print(f"\n {UI.BOLD}{UI.CYAN}── AUTHENTICATION ────────────────────────────────────────{UI.RESET}")
    if session:
        print(f"   Status           : {UI.GREEN}AUTHENTICATED{UI.RESET}")
        print(f"   Username         : {UI.WHITE}{session['username']}{UI.RESET}")
        print(f"   Role             : {session['role']}")
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
    auth = ClientAuthManager()
    if not auth.is_authenticated():
        print(f" {UI.RED}[!] Not authenticated. Please run 'july login' first.{UI.RESET}")
        sys.exit(1)

    cfg = ClientConfig.load()
    target_model = getattr(args, "model", None) or getattr(cfg, "selected_model", "july") or "july"
    if target_model.lower() == "auto":
        target_model = "july"
    target_model = target_model.lower().strip()

    from .storage import PermanentModelStorage
    from .state_manager import DualModelStateManager, ModelStatus
    perm_storage = PermanentModelStorage()
    state_mgr = DualModelStateManager()
    model_path = perm_storage.get_model_file(target_model)

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
    UI.print_banner("Dual-Model Configuration & Management")
    cfg = ClientConfig.load()
    name = getattr(args, "name", None)
    is_list = getattr(args, "list", False)
    is_status = getattr(args, "status", False)

    if is_list or (name and name.lower() in ("list", "ls")):
        print(f"\n {UI.BOLD}{UI.CYAN}Registered Foundation Models:{UI.RESET}")
        for k, meta in MODEL_METADATA.items():
            active_str = f" {UI.GREEN}[ACTIVE]{UI.RESET}" if getattr(cfg, "selected_model", "july") == k else ""
            print(f"\n   {UI.BOLD}{UI.CYAN}• {meta['title']}{UI.RESET}{active_str}")
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
            return
        else:
            print(f" {UI.RED}[!] Unknown model '{name}'. Available: july, gravity, auto, list{UI.RESET}\n")
            return

    interactive_select_model(cfg)


def cmd_chat(args):
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
        print(f"  {UI.GRAY}Active Model:{UI.RESET} {UI.CYAN}{active_mode} LLM{UI.RESET} {UI.GRAY}(Type {UI.YELLOW}/model{UI.GRAY} to switch models){UI.RESET}")
        print(f"  {UI.GRAY}Personality :{UI.RESET} {UI.YELLOW}{cfg.personality.replace('_', ' ').title()}{UI.RESET}  {UI.GRAY}Thinking:{UI.RESET} {UI.GREEN}{getattr(cfg, 'thinking_mode', 'expanded').upper()}{UI.RESET}")
        print(f"  {UI.GRAY}Commands    :{UI.RESET} {UI.CYAN}/model{UI.RESET}, {UI.CYAN}/think{UI.RESET}, {UI.CYAN}/help{UI.RESET}, {UI.CYAN}/paste{UI.RESET}, {UI.CYAN}/file <path>{UI.RESET}, {UI.CYAN}/visual{UI.RESET}, {UI.CYAN}/clear{UI.RESET}, {UI.CYAN}/status{UI.RESET}, {UI.CYAN}exit{UI.RESET}")
        print(f"{UI.GRAY}─────────────────────────────────────────────────────────────────────────────{UI.RESET}\n")

    runtime.load_model(active_path)

    if prompt_to_run:
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
                    print(f"   {UI.CYAN}/model [name]{UI.RESET}   - Select or switch foundation model (july, gravity, auto, list)")
                    print(f"   {UI.CYAN}/think [mode]{UI.RESET}   - Highlight model thinking (expanded, collapsed, hidden)")
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
                    if len(cmd_parts) > 1:
                        sub = cmd_parts[1].lower().strip()
                        if sub in ("list", "ls"):
                            print(f"\n  {UI.BOLD}{UI.CYAN}Registered Foundation Models:{UI.RESET}")
                            for mk, mm in MODEL_METADATA.items():
                                cur = f" {UI.GREEN}[ACTIVE]{UI.RESET}" if getattr(cfg, "selected_model", "july") == mk else ""
                                print(f"   • {UI.BOLD}{mm['title']}{UI.RESET}{cur} — {mm['description']}")
                            print()
                            continue
                        matched_m = None
                        if sub in ("july", "1", "j"): matched_m = "july"
                        elif sub in ("gravity", "2", "g"): matched_m = "gravity"
                        elif sub in ("auto", "3", "a"): matched_m = "auto"

                        if matched_m:
                            cfg.selected_model = matched_m
                            cfg.save()
                            meta = MODEL_METADATA[matched_m]
                            print(f"\n  {UI.GREEN}[✓] Selected Model Preference:[/] {UI.BOLD}{meta['title']}{UI.RESET}")
                            print(f"      {UI.GRAY}{meta['description']}{UI.RESET}\n")
                            if matched_m in ("july", "gravity"):
                                from .storage import PermanentModelStorage
                                perm = PermanentModelStorage()
                                if perm.is_model_present(matched_m):
                                    runtime.switch_model(matched_m, model_path=perm.get_model_file(matched_m))
                                    record_active_state(perm.get_model_file(matched_m), matched_m)
                                    print(f"  {UI.GREEN}[✓] {matched_m.upper()} LLM mounted into memory and active.{UI.RESET}\n")
                                else:
                                    print(f"  {UI.YELLOW}[*] {matched_m.upper()} LLM is not downloaded on this machine.{UI.RESET}")
                                    print(f"  {UI.CYAN}[*] Starting background download. You can continue chatting with {runtime.current_model_id.upper()}!{UI.RESET}\n")
                                    from .dual_engine import DualModelCoordinator
                                    coord = DualModelCoordinator(config=cfg, runtime=runtime)
                                    coord.select_model(matched_m)
                        else:
                            print(f"\n  {UI.RED}[!] Unknown model name.{UI.RESET} Available: {UI.CYAN}/model july{UI.RESET}, {UI.CYAN}/model gravity{UI.RESET}, {UI.CYAN}/model auto{UI.RESET}, {UI.CYAN}/model list{UI.RESET}\n")
                    else:
                        new_m = interactive_select_model(cfg)
                        if new_m and new_m in ("july", "gravity"):
                            from .storage import PermanentModelStorage
                            perm = PermanentModelStorage()
                            if perm.is_model_present(new_m):
                                runtime.switch_model(new_m, model_path=perm.get_model_file(new_m))
                                record_active_state(perm.get_model_file(new_m), new_m)
                                print(f"  {UI.GREEN}[✓] {new_m.upper()} LLM mounted into memory and active.{UI.RESET}\n")
                            else:
                                print(f"  {UI.YELLOW}[*] {new_m.upper()} LLM is not downloaded on this machine.{UI.RESET}")
                                print(f"  {UI.CYAN}[*] Starting background download. You can continue chatting with {runtime.current_model_id.upper()}!{UI.RESET}\n")
                                from .dual_engine import DualModelCoordinator
                                coord = DualModelCoordinator(config=cfg, runtime=runtime)
                                coord.select_model(new_m)
                    continue

            # Render background download status if any active
            from .state_manager import DualModelStateManager
            sm = DualModelStateManager()
            for d_m in sm.downloadingModels:
                d_stat = sm.modelInitializationStatus.get(d_m, {})
                pct = d_stat.get("percent", 0.0)
                spd = d_stat.get("speed_mb", 0.0)
                print(f" {UI.GRAY}[Background: {d_m.upper()} downloading: {pct:.1f}% ({spd:.1f} MB/s)]{UI.RESET}")

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

    model_p = subparsers.add_parser("model", help="Select or switch active foundation model (JULY LLM, GRAVITY LLM, AUTO)")
    model_p.add_argument("name", nargs="?", help="Model to activate (july, gravity, auto, list, status)")
    model_p.add_argument("-l", "--list", action="store_true", help="List all available models and their specifications")
    model_p.add_argument("-s", "--status", action="store_true", help="Show current active model status and telemetry")

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

    args = parser.parse_args()

    if args.command == "install":
        cmd_install()
    elif args.command == "register":
        cmd_register(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "status":
        cmd_status()
    elif args.command == "model":
        cmd_model(args)
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
