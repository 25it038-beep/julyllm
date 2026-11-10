"""
HS AI SOLUTIONS — JULY CLIENT CLI
Layer: COMMAND LINE INTERFACE (july_distribution.client.cli)
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM 3B | Family: HS AI FAMILY

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

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Global singleton runtime for persistent session within process
_active_runtime: ClientInferenceRuntime | None = None
_active_ephemeral_path: Path | None = None


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
    print("=" * 70)
    print("HS AI SOLUTIONS — JULY RUNTIME INSTALLATION")
    print("=" * 70)
    july_dir = get_default_july_dir()
    print(f"[+] Setting up configuration directory: {july_dir}")

    cfg = ClientConfig.load()
    print(f"[+] Loaded client configuration: server = {cfg.server_url}")

    # Check dependencies
    print("\n[+] Checking local dependencies...")
    try:
        import llama_cpp
        print(f"  - llama-cpp-python: INSTALLED (v{llama_cpp.__version__})")
    except ImportError:
        print("  - llama-cpp-python: NOT INSTALLED. Run: pip install llama-cpp-python")

    hw = detect_client_hardware()
    print(f"\n[+] Detected Hardware Profile:")
    print(f"  - CPU Threads:     {hw['cpu_threads']}")
    print(f"  - System RAM:      {hw['ram_available_gb']} GB free of {hw['ram_total_gb']} GB")
    print(f"  - GPU Acceleration: {hw['gpu_name']} ({hw['vram_free_mb']} MB VRAM)")

    print("\n[+] JULY Runtime successfully installed and configured!")
    print("Next step: Run 'july login' to authenticate with HS AI Solutions.")


def cmd_login(args):
    print("=" * 70)
    print("HS AI SOLUTIONS — JULY AUTHENTICATION")
    print("=" * 70)
    auth = ClientAuthManager()

    username = args.username or input("Username: ").strip()
    password = args.password or getpass.getpass("Password: ")

    try:
        session = auth.login(username, password, server_url=args.server)
        print(f"\n[+] Login successful! Authenticated as: {session['username']} ({session['role']})")
        print(f"[+] Model Access Granted: {session['model_access_granted']}")
        print(f"[+] Active Token Cached in: {auth.session_file}")
    except Exception as e:
        print(f"\n[!] Authentication Failed: {e}")
        sys.exit(1)


def cmd_register(args):
    print("=" * 70)
    print("HS AI SOLUTIONS — USER REGISTRATION")
    print("=" * 70)
    auth = ClientAuthManager()

    username = args.username or input("Username: ").strip()
    email = args.email or input("Email: ").strip()
    password = args.password or getpass.getpass("Password: ")

    try:
        res = auth.register(username, email, password, server_url=args.server)
        print(f"\n[+] Registration successful! Welcome to HS AI Solutions, {res.get('username')}!")
        print(f"[+] Model Access Granted: Authorized")
        print(f"[+] Active Token Cached in: {auth.session_file}")
    except Exception as e:
        print(f"\n[!] Registration Failed: {e}")
        sys.exit(1)


def cmd_status():
    print("=" * 70)
    print("HS AI SOLUTIONS — JULY RUNTIME STATUS")
    print("=" * 70)
    auth = ClientAuthManager()
    session = auth.get_session()

    print("[USER AUTHENTICATION]")
    if session:
        print(f"  Status:               LOGGED IN")
        print(f"  Username:             {session['username']}")
        print(f"  Role:                 {session['role']}")
        print(f"  Model Access Granted: {session.get('model_access_granted', True)}")
        print(f"  Connected Server:     {session.get('server_url')}")
    else:
        print("  Status:               NOT LOGGED IN (Run 'july login')")

    print("\n[MODEL STATE]")
    active_path = get_active_ephemeral_path()
    if active_path:
        print(f"  Status:               LOADED IN RAM")
        print(f"  Storage Location:     {active_path} (Temporary RAM-backed)")
        print(f"  Size:                 {active_path.stat().st_size:,} bytes")
    else:
        print("  Status:               UNLOADED (Run 'july load')")

    print("\n[LOCAL HARDWARE TELEMETRY]")
    hw = detect_client_hardware()
    print(f"  CPU Cores/Threads:    {hw['cpu_threads']} (Allocated: {hw['recommended_threads']})")
    print(f"  RAM Available/Total:  {hw['ram_available_gb']} GB / {hw['ram_total_gb']} GB ({hw['ram_used_percent']}% used)")
    print(f"  GPU Hardware:         {hw['gpu_name']}")
    if hw["gpu_available"]:
        print(f"  VRAM Free/Total:      {hw['vram_free_mb']} MB / {hw['vram_total_mb']} MB")
        print(f"  Recommended Offload:  {hw['recommended_gpu_layers']} layers")


def cmd_load(args):
    print("=" * 70)
    print("HS AI SOLUTIONS — JULY EPHEMERAL MODEL ACQUISITION")
    print("=" * 70)

    auth = ClientAuthManager()
    if not auth.is_authenticated():
        print("[!] Not authenticated. Please run 'july login' first.")
        sys.exit(1)

    cfg = ClientConfig.load()
    storage = ClientEphemeralStorage()
    downloader = ClientModelDownloader(cfg, auth)

    # Allocate temporary RAM-backed storage path
    ephemeral_path = storage.allocate_path()
    print(f"[+] Allocated Ephemeral Storage: {ephemeral_path}")
    print(f"[+] Applying Windows FILE_ATTRIBUTE_TEMPORARY (RAM-backed caching)...")

    # Fast seed check (if existing master seed present on developer workstation)
    root_seed = Path(__file__).resolve().parent.parent.parent / "models" / "july-final.gguf"
    if root_seed.exists() and not ephemeral_path.exists():
        print("[*] Priming ephemeral storage from verified seed...")
        import shutil
        shutil.copyfile(root_seed, ephemeral_path)

    def progress(received, total, speed):
        pct = (received / total) * 100
        mb_r = received / (1024 * 1024)
        mb_t = total / (1024 * 1024)
        sys.stdout.write(f"\r  Downloading from Cloudflare R2: [{pct:5.1f}%] {mb_r:7.1f} / {mb_t:7.1f} MB ({speed:5.1f} MB/s)")
        sys.stdout.flush()

    try:
        downloader.download_to_ephemeral_storage(ephemeral_path, progress_callback=progress)
        record_active_state(ephemeral_path)
        print(f"\n[+] Model successfully validated and mounted in temporary RAM-backed storage.")
        print("[+] You can now run 'july chat' to perform genuine local inference.")
    except Exception as e:
        print(f"\n[!] Model acquisition error: {e}")
        storage.wipe_and_unlink(ephemeral_path)
        sys.exit(1)


def cmd_chat(args):
    active_path = get_active_ephemeral_path()
    if not active_path:
        print("[!] Model is not currently loaded in RAM.")
        print("[*] Automatically initiating 'july load'...")
        cmd_load(args)
        active_path = get_active_ephemeral_path()
        if not active_path:
            print("[!] Could not initialize model.")
            sys.exit(1)

    cfg = ClientConfig.load()
    storage = ClientEphemeralStorage()
    customizer = UserCustomizationManager(cfg)
    runtime = ClientInferenceRuntime(cfg, storage, customizer)

    print("\n" + "=" * 70)
    print("HS AI SOLUTIONS — JULY LLM INTERACTIVE CHAT")
    print(f"Personality: {cfg.personality.replace('_', ' ').title()}")
    print("Type 'exit', 'quit', or press Ctrl+C to stop.")
    print("=" * 70 + "\n")

    runtime.load_model(active_path)

    if args.prompt:
        # One-off prompt
        print(f"User: {args.prompt}\nJULY: ", end="", flush=True)
        for token in runtime.generate_stream(args.prompt):
            sys.stdout.write(token)
            sys.stdout.flush()
        print("\n")
        return

    # Interactive REPL
    session_id = f"cli_{int(time.time())}"
    while True:
        try:
            user_input = input("User > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                break

            sys.stdout.write("JULY > ")
            sys.stdout.flush()
            t0 = time.time()
            tok_count = 0
            for token in runtime.generate_stream(user_input, session_id=session_id):
                sys.stdout.write(token)
                sys.stdout.flush()
                tok_count += 1
            elapsed = max(0.001, time.time() - t0)
            sys.stdout.write(f"\n({tok_count} tokens in {elapsed:.2f}s | {tok_count/elapsed:.1f} tok/s)\n\n")
        except KeyboardInterrupt:
            print("\nExiting chat session...")
            break


def cmd_unload():
    print("=" * 70)
    print("HS AI SOLUTIONS — UNLOADING MODEL & RECLAIMING RAM")
    print("=" * 70)
    active_path = get_active_ephemeral_path()
    storage = ClientEphemeralStorage()

    if active_path:
        print(f"[+] Wiping ephemeral RAM file: {active_path}")
        storage.wipe_and_unlink(active_path)
        clear_active_state()
        print("[+] Ephemeral storage securely unlinked and erased.")
    else:
        print("[*] No active model was mounted in RAM.")

    storage.reclaim_os_memory()
    print("[+] Working set memory released back to Windows OS.")


def cmd_update(args):
    print("=" * 70)
    print("HS AI SOLUTIONS — CHECKING MODEL UPDATES")
    print("=" * 70)
    cfg = ClientConfig.load()
    url = f"{cfg.server_url.rstrip('/')}/api/v1/model/check-update"

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"  Latest Server Version: {data.get('latest_server_version')}")
        print(f"  Release Notes:         {data.get('release_notes')}")
        print(f"  SHA-256:               {data.get('sha256')}")
        print("\n[+] To load the latest model version, execute: july unload && july load")
    except Exception as e:
        print(f"[!] Update check failed: {e}")


def cmd_config(args):
    cfg = ClientConfig.load()
    if args.set:
        key, val = args.set
        if hasattr(cfg, key):
            # Parse type
            cur_val = getattr(cfg, key)
            if isinstance(cur_val, int):
                setattr(cfg, key, int(val))
            elif isinstance(cur_val, float):
                setattr(cfg, key, float(val))
            else:
                setattr(cfg, key, val)
            cfg.save()
            print(f"[+] Updated configuration: {key} = {getattr(cfg, key)}")
        else:
            print(f"[!] Unknown config key: {key}")
        return

    print("=" * 70)
    print("HS AI SOLUTIONS — JULY CLIENT CONFIGURATION")
    print("=" * 70)
    data = cfg.__dict__
    for k, v in data.items():
        print(f"  {k:<24}: {v}")
    print("\nTo update a setting: july config --set <key> <value>")


def main():
    parser = argparse.ArgumentParser(prog="july", description="JULY LLM Multi-Computer Distribution CLI")
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
    elif args.command == "chat":
        cmd_chat(args)
    elif args.command == "unload":
        cmd_unload()
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
