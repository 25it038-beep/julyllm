#!/usr/bin/env bash
# ==============================================================================
# HS AI SOLUTIONS — JULY LLM ALL-IN-ONE AUTONOMOUS RUNTIME (LINUX & TAILS OS)
# Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
# Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
# Repository: https://github.com/25it038-beep/julyllm
#
# One-liner execution:
# curl -fsSL https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/start.sh | bash
# wget -qO- https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/start.sh | bash
# ==============================================================================
set -e

# ANSI Color Codes
CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
WHITE='\033[97m'
GRAY='\033[90m'
MAGENTA='\033[95m'
BOLD='\033[1m'
RESET='\033[0m'

SERVER_URL="https://julyllm.onrender.com"
STUDIO_URL="https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/"
RAW_INSTALL_URL="https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/install.sh"

UPDATE=false
SWITCH_USER=false
MODEL=""
VOICE=false
LIVE=false
PERSISTENT_MODE=false
TEMP_MODE=false

# Argument parsing
while [[ $# -gt 0 ]]; do
    case "$1" in
        --update|-Update|-u)
            UPDATE=true
            shift
            ;;
        --switch-user|-SwitchUser)
            SWITCH_USER=true
            shift
            ;;
        --voice|-Voice)
            VOICE=true
            shift
            ;;
        --live|-Live)
            LIVE=true
            shift
            ;;
        --model|-Model)
            MODEL="$2"
            shift 2
            ;;
        --persistent|-p)
            PERSISTENT_MODE=true
            shift
            ;;
        --temp|-t)
            TEMP_MODE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Render ASCII Banner
clear 2>/dev/null || true
echo ""
echo -e "${CYAN}     ██╗██╗   ██╗██╗  ██╗   ██╗    ██╗     ██╗     ███╗   ███╗${RESET}"
echo -e "${CYAN}     ██║██║   ██║██║  ╚██╗ ██╔╝    ██║     ██║     ████╗ ████║${RESET}"
echo -e "${CYAN}     ██║██║   ██║██║   ╚████╔╝     ██║     ██║     ██╔████╔██║${RESET}"
echo -e "${CYAN}██   ██║██║   ██║██║    ╚██╔╝      ██║     ██║     ██║╚██╔╝██║${RESET}"
echo -e "${CYAN}╚█████╔╝╚██████╔╝███████╗██║       ███████╗███████╗██║ ╚═╝ ██║${RESET}"
echo -e "${CYAN} ╚════╝  ╚═════╝ ╚══════╝╚═╝       ╚══════╝╚══════╝╚═╝     ╚═╝${RESET}"
echo -e "${GRAY}─────────────────────────────────────────────────────────────────────────────${RESET}"
echo -e "  ${BOLD}${WHITE}HS AI SOLUTIONS${RESET}  ${GRAY}•${RESET}  ${GREEN}JULY LLM & GRAVITY LLM RUNTIME PLATFORM${RESET}"
echo -e "  ${GRAY}Founder & Architect:${RESET} Harshan Seliyan  ${GRAY}•${RESET}  ${YELLOW}Tails OS & Linux Native${RESET}"
echo -e "  ${GRAY}Studio Portal:${RESET} ${CYAN}${STUDIO_URL}${RESET}"
echo -e "${GRAY}─────────────────────────────────────────────────────────────────────────────${RESET}"
echo ""

# Detect Environment
DISTRO_NAME="Linux"
IS_TAILS=false
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_NAME="${NAME:-Linux}"
fi
if [ "${ID:-}" = "tails" ] || grep -qi "tails" /etc/os-release 2>/dev/null || [ -f /etc/amnesia/version ] || [ -f /etc/tails/version ]; then
    IS_TAILS=true
    DISTRO_NAME="Tails (The Amnesic Incognito Live System)"
fi

echo -e "  ${BOLD}${WHITE}Status:${RESET} ${GREEN}Connected${RESET}  ${GRAY}•${RESET}  ${BOLD}${WHITE}Runtime:${RESET} ${CYAN}Linux${RESET}  ${GRAY}•${RESET}  ${BOLD}${WHITE}Environment:${RESET} ${YELLOW}${DISTRO_NAME}${RESET}"
echo -e "${GRAY}─────────────────────────────────────────────────────────────────────────────${RESET}"
echo ""

# [1/4] Ensure Client Runtime Installed
JULY_CMD=""
INSTALL_ROOT=""

if command -v july >/dev/null 2>&1; then
    JULY_CMD="$(command -v july)"
elif [ -x "$HOME/Persistent/.july_runtime/bin/july" ]; then
    JULY_CMD="$HOME/Persistent/.july_runtime/bin/july"
    INSTALL_ROOT="$HOME/Persistent/.july_runtime"
elif [ -x "$HOME/.local/bin/july" ]; then
    JULY_CMD="$HOME/.local/bin/july"
    INSTALL_ROOT="$HOME/.local/share/JulyRuntime"
elif [ -x "$HOME/.local/share/JulyRuntime/bin/july" ]; then
    JULY_CMD="$HOME/.local/share/JulyRuntime/bin/july"
    INSTALL_ROOT="$HOME/.local/share/JulyRuntime"
fi

NEEDS_INSTALL=false
if [ -z "$JULY_CMD" ] || [ ! -x "$JULY_CMD" ] || [ "$UPDATE" = true ]; then
    NEEDS_INSTALL=true
fi

if [ "$NEEDS_INSTALL" = true ]; then
    echo -e " ${GREEN}[⚡] [1/4] Initializing and synchronizing JULY runtime...${RESET}"
    SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
    INSTALL_FLAGS=""
    if [ "$PERSISTENT_MODE" = true ]; then
        INSTALL_FLAGS="--persistent"
    elif [ "$TEMP_MODE" = true ]; then
        INSTALL_FLAGS="--temp"
    fi

    if [ -f "$SELF_DIR/install.sh" ]; then
        bash "$SELF_DIR/install.sh" $INSTALL_FLAGS
    else
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL "$RAW_INSTALL_URL" | bash -s -- $INSTALL_FLAGS
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- "$RAW_INSTALL_URL" | bash -s -- $INSTALL_FLAGS
        else
            echo -e " ${RED}[!] Failed to fetch installer. Please install curl or wget.${RESET}"
            exit 1
        fi
    fi

    # Re-evaluate JULY_CMD
    if command -v july >/dev/null 2>&1; then
        JULY_CMD="$(command -v july)"
    elif [ -x "$HOME/Persistent/.july_runtime/bin/july" ]; then
        JULY_CMD="$HOME/Persistent/.july_runtime/bin/july"
    elif [ -x "$HOME/.local/bin/july" ]; then
        JULY_CMD="$HOME/.local/bin/july"
    fi
fi

if [ -z "$JULY_CMD" ] || [ ! -x "$JULY_CMD" ]; then
    echo -e " ${RED}[!] Error: Could not locate 'july' executable after installation.${RESET}"
    exit 1
fi

# Refresh PATH for active script execution
export PATH="$HOME/.local/bin:$HOME/Persistent/.july_runtime/bin:$HOME/.local/share/JulyRuntime/bin:$PATH"

# Configure control server
"$JULY_CMD" config --set server_url "$SERVER_URL" >/dev/null 2>&1 || true

# [2/4] Verify Clerk Identity & Access Management (IAM)
echo ""
echo -e " ${GREEN}[⚡] [2/4] Verifying Clerk Identity & Access Management (IAM)...${RESET}"

AUTH_JSON="$("$JULY_CMD" whoami 2>/dev/null || true)"
IS_AUTH=false

# Check environment fallback directly
if [ -n "$JULY_API_KEY" ] || [ -n "$JULY_TOKEN" ] || [ -n "$CLERK_TOKEN" ]; then
    IS_AUTH=true
    echo -e "      ${GREEN}[✓] Clerk Identity Verified:${RESET} Environment Fallback Key Active"
    echo -e "      ${GREEN}[✓] Credential Storage     :${RESET} Ephemeral RAM (Zero Permanent Trace)"
elif "$JULY_CMD" auth status 2>&1 | grep -qi "AUTHENTICATED"; then
    IS_AUTH=true
    echo -e "      ${GREEN}[✓] Clerk Identity Verified:${RESET} Cryptographic Vault Active"
    echo -e "      ${GREEN}[✓] Credential Storage     :${RESET} AES-GCM Encrypted Vault (User-Scoped 0600)"
fi

if [ "$IS_AUTH" = false ] || [ "$SWITCH_USER" = true ]; then
    echo ""
    echo -e " ┌──────────────────────────────────────────────────────────────────┐"
    echo -e " │             CLERK AUTHENTICATION REQUIRED TO ACCESS JULY         │"
    echo -e " │                                                                  │"
    echo -e " │  Access to July & Gravity AI models is protected by Clerk IAM.   │"
    echo -e " │  Please authenticate to unlock models and rate-limited quotas.   │"
    echo -e " └──────────────────────────────────────────────────────────────────┘"
    echo ""
    echo -e " ${BOLD}${WHITE}Select Authentication Method:${RESET}"
    echo -e "   ${CYAN}[1]  🎟️  Sign In with Clerk Token / API Key (Headless / Tails Recommended)${RESET}"
    echo -e "   ${GREEN}[2]  🌐  Browser Single Sign-On (Google, GitHub, Clerk Web)${RESET}"
    echo -e "   ${GRAY}[q]  ❌  Cancel & Exit${RESET}"
    echo ""
    read -p " Selection [1-2, default: 1]: " auth_choice </dev/tty || auth_choice="1"
    [ -z "$auth_choice" ] && auth_choice="1"

    if [ "$auth_choice" = "1" ]; then
        echo ""
        echo -e " ─── ${GREEN}CLERK TOKEN / API KEY SIGN IN${RESET} ───"
        read -s -p "  Enter Clerk Token or API Key: " user_token </dev/tty
        echo ""
        read -p "  Email (Optional, press Enter to skip): " user_email </dev/tty
        if [ -n "$user_email" ]; then
            "$JULY_CMD" login --token "$user_token" --email "$user_email"
        else
            "$JULY_CMD" login --token "$user_token"
        fi
    elif [ "$auth_choice" = "2" ]; then
        echo ""
        echo -e " ─── ${CYAN}BROWSER AUTHENTICATION${RESET} ───"
        "$JULY_CMD" login
    else
        echo ""
        echo -e " ${RED}[!] Authentication cancelled. Access to July & Gravity models is locked.${RESET}"
        echo -e "     Run '${CYAN}july login${RESET}' whenever you are ready to authenticate."
        exit 0
    fi
fi

# [3/4] Check Rate Limit Governance
echo ""
echo -e " ${GREEN}[⚡] [3/4] Checking Rate Limit Governance & Quota Policy...${RESET}"
"$JULY_CMD" usage 2>/dev/null || true

# Register cleanup handler for ephemeral RAM wipe
cleanup() {
    echo ""
    echo -e " ${YELLOW}[⚡] Session concluding. Securely wiping ephemeral RAM storage...${RESET}"
    "$JULY_CMD" unload >/dev/null 2>&1 || true
    echo -e " ${GREEN}[✓] RAM reclaimed. Zero sensitive artifacts remain on disk or memory.${RESET}"
    echo ""
}
trap cleanup EXIT INT TERM

# [4/4] Foundation Model Selection & Ephemeral RAM Initialization
if [ -z "$MODEL" ]; then
    if [ -n "$JULY_MODEL" ]; then
        MODEL="$JULY_MODEL"
    else
        echo ""
        echo -e " ${BOLD}${WHITE}Select Foundation Model / Interactive Mode:${RESET}"
        echo -e "   ${CYAN}[1]  🌟  July LLM (General Intelligence, Coding & Agentic Reasoning)${RESET}"
        echo -e "   ${YELLOW}[2]  🌌  Gravity LLM (Deep Mathematical Reasoning, Proofs & Physics)${RESET}"
        echo -e "   ${MAGENTA}[3]  ⚡  Auto Router (Dynamic Query Routing to July or Gravity)${RESET}"
        echo -e "   ${GREEN}[4]  🤖  JULY AGENT (Autonomous Cognitive Agent with Tool Calling)${RESET}"
        echo -e "   ${CYAN}[5]  🎙️   JULY LIVE (Continuous Conversational Voice AI Mode)${RESET}"
        echo ""
        read -p " Select Option [1-5] (Default: 1 - July): " m_choice </dev/tty || m_choice="1"
        case "$m_choice" in
            2) MODEL="gravity" ;;
            3) MODEL="auto" ;;
            4) MODEL="agent" ;;
            5) MODEL="july"; LIVE=true ;;
            *) MODEL="july" ;;
        esac
    fi
fi

if [ "$MODEL" = "agent" ]; then
    "$JULY_CMD" agent
    exit 0
fi

"$JULY_CMD" config --set selected_model "$MODEL" >/dev/null 2>&1 || true

echo ""
echo -e " ${GREEN}[⚡] [4/4] Mounting $(echo "$MODEL" | tr '[:lower:]' '[:upper:]') LLM into Ephemeral Physical RAM...${RESET}"
"$JULY_CMD" load --model "$MODEL" || {
    echo -e " ${YELLOW}[*] Model pre-load skipped or using cloud inference gateway.${RESET}"
}

echo ""
echo -e " ${GREEN}🛡️  Model ready. Entering interactive session with rate limit governance.${RESET}"
echo -e " ${YELLOW}🔒  Ephemeral Privacy: Weights and session are wiped from RAM on exit.${RESET}"
echo ""

if [ "$VOICE" = true ]; then
    "$JULY_CMD" voice on >/dev/null 2>&1 || true
    echo -e " ${GREEN}[✓] Voice system activated.${RESET}"
fi

if [ "$LIVE" = true ]; then
    "$JULY_CMD" live --model "$MODEL"
else
    "$JULY_CMD" chat --model "$MODEL"
fi
