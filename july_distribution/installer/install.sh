#!/usr/bin/env bash
# ==============================================================================
# HS AI SOLUTIONS — JULY LLM NATIVE LINUX & TAILS OS INSTALLER
# Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
# Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
# Repository: https://github.com/25it038-beep/julyllm
#
# One-liner execution:
# curl -fsSL https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/install.sh | bash
# wget -qO- https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/install.sh | bash
# ==============================================================================
set -e

# ANSI Color Codes
CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
WHITE='\033[97m'
GRAY='\033[90m'
BOLD='\033[1m'
RESET='\033[0m'

SERVER_URL="https://julyllm.onrender.com"
STUDIO_URL="https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/"
GITHUB_ZIP_URL="https://github.com/25it038-beep/julyllm/archive/refs/heads/main.zip"

INSTALL_MODE="auto" # auto, temp, persistent
CUSTOM_INSTALL_DIR=""
NON_INTERACTIVE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --persistent|-p)
            INSTALL_MODE="persistent"
            shift
            ;;
        --temp|-t)
            INSTALL_MODE="temp"
            shift
            ;;
        --dir|-d)
            CUSTOM_INSTALL_DIR="$2"
            shift 2
            ;;
        --server|-s)
            SERVER_URL="$2"
            shift 2
            ;;
        --no-prompt|-y)
            NON_INTERACTIVE=true
            shift
            ;;
        --help|-h)
            echo "JULY LLM Linux & Tails OS Installer"
            echo "Usage: ./install.sh [options]"
            echo "Options:"
            echo "  -p, --persistent    Install into Tails Persistent Storage"
            echo "  -t, --temp          Install in temporary amnesia mode (cleared on reboot)"
            echo "  -d, --dir <path>    Specify custom installation root directory"
            echo "  -s, --server <url>  Set backend control server URL"
            echo "  -y, --no-prompt     Run non-interactively"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Render Banner
clear 2>/dev/null || true
echo ""
echo -e "${CYAN}     ██╗██╗   ██╗██╗  ██╗   ██╗    ██╗     ██╗     ███╗   ███╗${RESET}"
echo -e "${CYAN}     ██║██║   ██║██║  ╚██╗ ██╔╝    ██║     ██║     ████╗ ████║${RESET}"
echo -e "${CYAN}     ██║██║   ██║██║   ╚████╔╝     ██║     ██║     ██╔████╔██║${RESET}"
echo -e "${CYAN}██   ██║██║   ██║██║    ╚██╔╝      ██║     ██║     ██║╚██╔╝██║${RESET}"
echo -e "${CYAN}╚█████╔╝╚██████╔╝███████╗██║       ███████╗███████╗██║ ╚═╝ ██║${RESET}"
echo -e "${CYAN} ╚════╝  ╚═════╝ ╚══════╝╚═╝       ╚══════╝╚══════╝╚═╝     ╚═╝${RESET}"
echo -e "${GRAY}─────────────────────────────────────────────────────────────────────────────${RESET}"
echo -e "  ${BOLD}${WHITE}HS AI SOLUTIONS${RESET}  ${GRAY}•${RESET}  ${GREEN}JULY LLM AUTONOMOUS RUNTIME PLATFORM${RESET}"
echo -e "  ${GRAY}Founder & Architect:${RESET} Harshan Seliyan  ${GRAY}•${RESET}  ${YELLOW}Tails OS & Linux Native${RESET}"
echo -e "  ${GRAY}Studio Portal:${RESET} ${CYAN}${STUDIO_URL}${RESET}"
echo -e "${GRAY}─────────────────────────────────────────────────────────────────────────────${RESET}"
echo ""

# [1/5] OS & Distribution Detection
echo -e " ${GREEN}[⚡] [1/5] Detecting Linux Distribution & Environment...${RESET}"

DISTRO_NAME="Generic Linux"
DISTRO_ID="linux"
IS_TAILS=false
HAS_PERSISTENCE=false
PERSISTENT_DIR=""

if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="${ID:-linux}"
    DISTRO_NAME="${NAME:-Linux}"
fi

# Explicit Tails OS Detection
if [ "$DISTRO_ID" = "tails" ] || grep -qi "tails" /etc/os-release 2>/dev/null || [ -f /etc/amnesia/version ] || [ -f /etc/tails/version ] || [ "$USER" = "amnesia" -a -d /live ]; then
    IS_TAILS=true
    DISTRO_NAME="Tails (The Amnesic Incognito Live System)"
    DISTRO_ID="tails"
fi

if [ "$IS_TAILS" = true ]; then
    echo -e "      ${GREEN}[✓] Detected Operating System :${RESET} ${BOLD}${CYAN}${DISTRO_NAME}${RESET}"
    echo -e "      ${GREEN}[✓] Amnesia Security Model    :${RESET} Active (Zero Permanent Traces by Default)"

    # Check for Tails Persistent Storage
    if [ -d "/home/amnesia/Persistent" ] && [ -w "/home/amnesia/Persistent" ]; then
        HAS_PERSISTENCE=true
        PERSISTENT_DIR="/home/amnesia/Persistent"
    elif [ -d "$HOME/Persistent" ] && [ -w "$HOME/Persistent" ]; then
        HAS_PERSISTENCE=true
        PERSISTENT_DIR="$HOME/Persistent"
    elif [ -d "/live/persistence/TailsData_unlocked" ]; then
        HAS_PERSISTENCE=true
        PERSISTENT_DIR="$HOME/Persistent"
    fi

    if [ "$HAS_PERSISTENCE" = true ]; then
        echo -e "      ${GREEN}[✓] Tails Persistent Storage  :${RESET} ${GREEN}UNLOCKED & AVAILABLE (${PERSISTENT_DIR})${RESET}"
    else
        echo -e "      ${YELLOW}[!] Tails Persistent Storage  :${RESET} ${YELLOW}NOT UNLOCKED OR NOT CONFIGURED${RESET}"
    fi
else
    echo -e "      ${GREEN}[✓] Detected Operating System :${RESET} ${BOLD}${WHITE}${DISTRO_NAME} (${DISTRO_ID})${RESET}"
fi

# Determine Installation Directory based on OS and Persistence Choice
INSTALL_ROOT=""
JULY_CONFIG_DIR=""
SELECTED_STORAGE_MODE="temporary"

if [ -n "$CUSTOM_INSTALL_DIR" ]; then
    INSTALL_ROOT="$CUSTOM_INSTALL_DIR"
    JULY_CONFIG_DIR="$INSTALL_ROOT/.july"
elif [ "$IS_TAILS" = true ]; then
    if [ "$INSTALL_MODE" = "persistent" ] && [ "$HAS_PERSISTENCE" = true ]; then
        SELECTED_STORAGE_MODE="persistent"
    elif [ "$INSTALL_MODE" = "temp" ]; then
        SELECTED_STORAGE_MODE="temporary"
    elif [ "$HAS_PERSISTENCE" = true ] && [ "$NON_INTERACTIVE" = false ]; then
        echo ""
        echo -e " ${BOLD}${WHITE}Tails OS Storage Selection:${RESET}"
        echo -e "   ${CYAN}[1]  💾 Persistent Mode${RESET}  - Install inside Tails Persistent Storage (${PERSISTENT_DIR}/.july_runtime)"
        echo -e "                        Preserves JULY CLI, config, models and login across reboots."
        echo -e "   ${YELLOW}[2]  🛡️  Temporary Mode${RESET}   - Install into ephemeral amnesia RAM ($HOME/.local/share/JulyRuntime)"
        echo -e "                        Disappears completely upon shutdown or restart."
        echo ""
        read -p " Selection [1-2, default: 1]: " storage_choice </dev/tty || storage_choice="1"
        if [ "$storage_choice" = "2" ]; then
            SELECTED_STORAGE_MODE="temporary"
        else
            SELECTED_STORAGE_MODE="persistent"
        fi
    else
        SELECTED_STORAGE_MODE="temporary"
    fi

    if [ "$SELECTED_STORAGE_MODE" = "persistent" ]; then
        INSTALL_ROOT="$PERSISTENT_DIR/.july_runtime"
        JULY_CONFIG_DIR="$PERSISTENT_DIR/.july"
        echo -e "      ${GREEN}[✓] Selected Storage Mode     :${RESET} ${BOLD}${CYAN}PERSISTENT${RESET} ($INSTALL_ROOT)"
    else
        INSTALL_ROOT="$HOME/.local/share/JulyRuntime"
        JULY_CONFIG_DIR="$HOME/.july"
        echo -e "      ${YELLOW}[✓] Selected Storage Mode     :${RESET} ${BOLD}${YELLOW}TEMPORARY (Amnesia Active)${RESET}"
        echo -e "      ${GRAY}    Note: This temporary installation will disappear when Tails restarts.${RESET}"
    fi
else
    INSTALL_ROOT="$HOME/.local/share/JulyRuntime"
    JULY_CONFIG_DIR="$HOME/.july"
fi

BIN_DIR="$INSTALL_ROOT/bin"
LOCAL_BIN="$HOME/.local/bin"

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$LOCAL_BIN" "$JULY_CONFIG_DIR"

# [2/5] Python Runtime & Isolated Virtual Environment
echo ""
echo -e " ${GREEN}[⚡] [2/5] Verifying Python Runtime & Creating Virtual Environment...${RESET}"

PYTHON_SYS=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_SYS="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_SYS="$(command -v python)"
else
    echo -e "      ${RED}[!] Error: Python 3.10+ is required but not installed.${RESET}"
    if [ "$IS_TAILS" = true ]; then
        echo -e "      ${YELLOW}Tails OS comes with Python 3 pre-installed. Please check your system PATH.${RESET}"
    else
        echo -e "      Please install python3: sudo apt update && sudo apt install -y python3 python3-venv"
    fi
    exit 1
fi

PY_VER="$($PYTHON_SYS -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")"
PY_MAJOR="$(echo "$PY_VER" | cut -d. -f1)"
PY_MINOR="$(echo "$PY_VER" | cut -d. -f2)"

if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MAJOR" -eq 3 -a "$PY_MINOR" -lt 10 ]; then
    echo -e "      ${RED}[!] Error: Python 3.10+ is required. Found Python $PY_VER.${RESET}"
    exit 1
fi
echo -e "      ${GREEN}[✓] Python located:${RESET} $PYTHON_SYS (v$PY_VER)"

# Setup isolated virtualenv inside INSTALL_ROOT
VENV_DIR="$INSTALL_ROOT/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

if [ ! -x "$VENV_PYTHON" ]; then
    echo -e "      ${GRAY}[*] Creating isolated virtual environment at $VENV_DIR...${RESET}"
    if ! "$PYTHON_SYS" -m venv "$VENV_DIR" 2>/dev/null; then
        echo -e "      ${YELLOW}[*] python3 -m venv failed. Attempting --without-pip fallback...${RESET}"
        "$PYTHON_SYS" -m venv --without-pip "$VENV_DIR" || {
            echo -e "      ${RED}[!] Failed to create venv. Ensure python3-venv is installed.${RESET}"
            exit 1
        }
        # Bootstrap pip if missing
        curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$VENV_PYTHON" - --no-warn-script-location -q || true
    fi
fi

if [ ! -x "$VENV_PYTHON" ]; then
    VENV_PYTHON="$VENV_DIR/bin/python"
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo -e "      ${YELLOW}[!] Virtualenv python not found, falling back to system interpreter with user scope.${RESET}"
    VENV_PYTHON="$PYTHON_SYS"
    PIP_EXTRA="--user"
else
    PIP_EXTRA=""
fi

# Upgrade pip inside virtual environment
echo -e "      ${GRAY}[*] Upgrading pip...${RESET}"
"$VENV_PYTHON" -m pip install --upgrade pip -q $PIP_EXTRA 2>/dev/null || true

# [3/5] Acquire JULY Client Distribution Files
echo ""
echo -e " ${GREEN}[⚡] [3/5] Acquiring & Installing JULY Client Runtime...${RESET}"

TARGET_DIST="$INSTALL_ROOT/july_distribution"
mkdir -p "$TARGET_DIST"

LOCAL_FOUND=false
# Check if running from local git checkout
if [ -n "${BASH_SOURCE[0]}" ]; then
    SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
    POSSIBLE_DIST="$(cd "$SELF_DIR/.." >/dev/null 2>&1 && pwd)"
    if [ -d "$POSSIBLE_DIST/client" ] && [ -f "$POSSIBLE_DIST/client/cli.py" ]; then
        echo -e "      ${GREEN}[✓] Found local distribution at:${RESET} $POSSIBLE_DIST"
        cp -r "$POSSIBLE_DIST/"* "$TARGET_DIST/"
        LOCAL_FOUND=true
    fi
fi

if [ "$LOCAL_FOUND" = false ]; then
    TMP_ZIP="/tmp/julyllm_$(date +%s).zip"
    TMP_EXTRACT="/tmp/julyllm_extract_$(date +%s)"
    mkdir -p "$TMP_EXTRACT"
    echo -e "      ${GRAY}[*] Fetching release archive from repository...${RESET}"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$GITHUB_ZIP_URL" -o "$TMP_ZIP"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$TMP_ZIP" "$GITHUB_ZIP_URL"
    else
        echo -e "      ${RED}[!] Neither curl nor wget was found. Cannot download distribution.${RESET}"
        exit 1
    fi

    if command -v unzip >/dev/null 2>&1; then
        unzip -q "$TMP_ZIP" -d "$TMP_EXTRACT"
    else
        "$VENV_PYTHON" -c "import zipfile; zipfile.ZipFile('$TMP_ZIP').extractall('$TMP_EXTRACT')"
    fi

    if [ -d "$TMP_EXTRACT/julyllm-main/july_distribution" ]; then
        cp -r "$TMP_EXTRACT/julyllm-main/july_distribution/"* "$TARGET_DIST/"
    else
        echo -e "      ${RED}[!] Failed to locate july_distribution in downloaded archive.${RESET}"
        rm -rf "$TMP_ZIP" "$TMP_EXTRACT"
        exit 1
    fi
    rm -rf "$TMP_ZIP" "$TMP_EXTRACT"
fi

# Install dependencies
echo -e "      ${GRAY}[*] Installing dependencies (requests, psutil, pydantic, fastapi, cryptography)...${RESET}"
CORE_DEPS=("requests>=2.31.0" "psutil>=5.9.0" "pydantic>=2.0.0" "fastapi>=0.110.0" "uvicorn>=0.30.0" "slowapi>=0.1.9" "boto3>=1.34.0" "cryptography>=41.0.0" "httpx>=0.27.0")

if [ -f "$TARGET_DIST/linux/requirements.txt" ]; then
    "$VENV_PYTHON" -m pip install -r "$TARGET_DIST/linux/requirements.txt" -q $PIP_EXTRA
else
    "$VENV_PYTHON" -m pip install "${CORE_DEPS[@]}" -q $PIP_EXTRA
fi

echo -e "      ${GREEN}[✓] Core dependencies installed successfully.${RESET}"

# [4/5] Generate Native Executable Launcher & Shell PATH Integration
echo ""
echo -e " ${GREEN}[⚡] [4/5] Generating Native Executable & Configuring User PATH...${RESET}"

JULY_EXEC="$BIN_DIR/july"
cat << EOF > "$JULY_EXEC"
#!/usr/bin/env bash
export PYTHONPATH="$INSTALL_ROOT:\$PYTHONPATH"
export PYTHONUNBUFFERED=1
EOF

if [ "$SELECTED_STORAGE_MODE" = "persistent" ]; then
cat << EOF >> "$JULY_EXEC"
export JULY_CLIENT_HOME="$JULY_CONFIG_DIR"
export JULY_PERSISTENT=1
EOF
fi

cat << EOF >> "$JULY_EXEC"
exec "$VENV_PYTHON" -m july_distribution.client.cli "\$@"
EOF

chmod +x "$JULY_EXEC"

# Link or copy to ~/.local/bin/july
mkdir -p "$LOCAL_BIN"
ln -sf "$JULY_EXEC" "$LOCAL_BIN/july" 2>/dev/null || cp "$JULY_EXEC" "$LOCAL_BIN/july"
chmod +x "$LOCAL_BIN/july"

# Also symlink to Persistent bin if Tails Persistent mode
if [ "$SELECTED_STORAGE_MODE" = "persistent" ] && [ -n "$PERSISTENT_DIR" ]; then
    mkdir -p "$PERSISTENT_DIR/bin"
    ln -sf "$JULY_EXEC" "$PERSISTENT_DIR/bin/july" 2>/dev/null || cp "$JULY_EXEC" "$PERSISTENT_DIR/bin/july"
    chmod +x "$PERSISTENT_DIR/bin/july"
fi

# Shell PATH registration
SHELL_CONFIGS=("$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile")
if [ "$SELECTED_STORAGE_MODE" = "persistent" ] && [ -n "$PERSISTENT_DIR" ]; then
    SHELL_CONFIGS+=("$PERSISTENT_DIR/.bashrc")
fi

PATH_EXPORT_LINE='export PATH="$HOME/.local/bin:'"$BIN_DIR"':$PATH"'

for sc in "${SHELL_CONFIGS[@]}"; do
    if [ -f "$sc" ] || [ "$sc" = "$HOME/.bashrc" ]; then
        touch "$sc" 2>/dev/null || true
        if ! grep -q "JulyRuntime" "$sc" 2>/dev/null && ! grep -q "$BIN_DIR" "$sc" 2>/dev/null; then
            echo "" >> "$sc"
            echo "# HS AI Solutions — JULY CLI PATH Integration" >> "$sc"
            echo "$PATH_EXPORT_LINE" >> "$sc"
            if [ "$SELECTED_STORAGE_MODE" = "persistent" ]; then
                echo "export JULY_CLIENT_HOME=\"$JULY_CONFIG_DIR\"" >> "$sc"
                echo "export JULY_PERSISTENT=1" >> "$sc"
            fi
            echo -e "      ${GREEN}[✓] Added PATH to:${RESET} $sc"
        fi
    fi
done

# Configure Default User Settings
CONFIG_FILE="$JULY_CONFIG_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    cat << EOF > "$CONFIG_FILE"
{
  "server_url": "$SERVER_URL",
  "hardware_mode": "auto",
  "context_length": 4096,
  "n_threads": 4,
  "n_batch": 64,
  "n_gpu_layers": 0,
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 0,
  "enable_web_search": true,
  "selected_model": "july",
  "personality": "precision_engineer",
  "thinking_mode": "expanded",
  "system_prompt": "You are JULY LLM, an advanced autonomous neural model created by Harshan Seliyan and developed by HS AI Solutions. Deliver accurate, rigorous, and helpful answers."
}
EOF
fi

# [5/5] Installation Verification & Diagnostics
echo ""
echo -e " ${GREEN}[⚡] [5/5] Running Installation Verification Diagnostics (july doctor)...${RESET}"

export PATH="$LOCAL_BIN:$BIN_DIR:$PATH"
"$JULY_EXEC" doctor

echo ""
echo -e "${CYAN}================================================================================"
echo -e "                    INSTALLATION COMPLETED SUCCESSFULLY!"
echo -e "================================================================================${RESET}"
echo ""
echo -e " ${BOLD}${WHITE}Execution Path:${RESET} $JULY_EXEC"
if [ "$SELECTED_STORAGE_MODE" = "persistent" ]; then
    echo -e " ${BOLD}${GREEN}Storage Mode  :${RESET} Persistent Storage ($PERSISTENT_DIR/.july_runtime) [Survives Reboot]"
else
    echo -e " ${BOLD}${YELLOW}Storage Mode  :${RESET} Temporary ($INSTALL_ROOT) [Cleared on Reboot / Amnesia]"
fi
echo ""
echo -e " ${BOLD}${WHITE}Available Commands:${RESET}"
echo -e "   ${CYAN}july${RESET}                - Launch interactive conversation"
echo -e "   ${CYAN}july chat${RESET}           - Single prompt or interactive chat"
echo -e "   ${CYAN}july agent${RESET}          - Autonomous multi-step cognitive agent"
echo -e "   ${CYAN}july models${RESET}         - List registered models and specs"
echo -e "   ${CYAN}july login${RESET}          - Sign in with Clerk IAM or token"
echo -e "   ${CYAN}july logout${RESET}         - Securely wipe credentials"
echo -e "   ${CYAN}july config${RESET}         - View or set runtime configuration"
echo -e "   ${CYAN}july doctor${RESET}         - Run full system diagnostic check"
echo -e "   ${CYAN}july version${RESET}        - Display version and architecture"
echo -e "   ${CYAN}july help${RESET}           - View all available commands"
echo ""
echo -e " ${YELLOW}To start using JULY right now, run:${RESET} ${BOLD}${WHITE}july${RESET}"
echo -e " ${GRAY}(Or in a new terminal session, type: july login)${RESET}"
echo ""
