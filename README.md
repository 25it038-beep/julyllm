# JULY LLM: MULTI-COMPUTER MODEL DISTRIBUTION PLATFORM
### HS AI SOLUTIONS | Founder & Chief Architect: Harshan Seliyan

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Model**: July LLM 3B (`july-final.gguf`, 2,019,377,888 bytes, SHA-256: `f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4`)  
**Storage**: Cloudflare R2 (Private Bucket: `july`, Endpoint: `https://21e5f9f23e1d60cb56bf1200e89255f3.r2.cloudflarestorage.com/`)  
**Target Cloud Platform**: [Render](https://render.com) (FastAPI Web Service + Managed PostgreSQL)

---

## 1. System Architecture

The **JULY Multi-Computer Distribution Platform** allows authorized Windows workstations across different physical locations to authenticate with HS AI Solutions, stream the private Cloudflare R2-hosted GGUF model directly into temporary RAM-backed storage, and perform genuine local inference (CPU / NVIDIA CUDA) with zero disk persistence.

```
┌─────────────────────────────────────────────────────────────┐
│                 RENDER MANAGED CLOUD HOSTING                │
│                                                             │
│   ┌──────────────────────────┐   ┌──────────────────────┐  │
│   │ Managed PostgreSQL DB    │   │ FastAPI Web Service  │  │
│   │ (Database: july_distrib) │◄──┤ (july-backend)       │  │
│   │ - Users, Tokens, Devices │   │ - SlowAPI Rate Limit │  │
│   │ - Audit Logs & Telemetry │   │ - HTTPS & CORS       │  │
│   └──────────────────────────┘   └──────────▲───────────┘  │
│                                             │               │
└─────────────────────────────────────────────┼───────────────┘
                                              │ Public HTTPS
                                              │ (onrender.com)
                                   ┌──────────▼───────────┐
                                   │ Remote Windows PCs   │
                                   │ (july CLI Clients)   │
                                   └──────────────────────┘
```

```
                             ┌────────────────────────────────────────┐
                             │       CLOUDFLARE R2 (PRIVATE)          │
                             │  Bucket: july                          │
                             │  Object: july-final.gguf (1.88 GB)     │
                             │  Public access strictly DISABLED       │
                             └───────────────────▲────────────────────┘
                                                 │ 15-Min Presigned
                                                 │ Resumable Stream
                                                 │ (Range Requests)
┌──────────────────────────────────────────────┐ │
│            RENDER CLOUD HOSTING              │ │
│                                              │ │
│  ┌────────────────────┐ ┌──────────────────┐ │ │
│  │ Managed PostgreSQL │ │ FastAPI Service  │─┼─┘
│  │ (july-postgres)    │ │ (july-backend)   │ │
│  │ - Users & Tokens   │◄┤ - SlowAPI Limit  │ │
│  │ - Approved Devices │ │ - HTTPS & CORS   │ │
│  │ - Audit Logs       │ │ - Token Auth     │ │
│  └────────────────────┘ └─────────▲────────┘ │
└───────────────────────────────────┼──────────┘
                         Public API │ (e.g. https://july-distribution-backend.onrender.com)
                         & Installer│
          ┌─────────────────────────┴────────────────────────┐
          │                                                  │
┌─────────▼──────────────┐                        ┌──────────▼─────────────┐
│ Windows Computer 1     │                        │ Windows Computer 2     │
│ (e.g. Office PC)       │                        │ (e.g. Remote Laptop)   │
│ - july CLI             │                        │ - july CLI             │
│ - RAM Storage          │                        │ - RAM Storage          │
│ - Local llama.cpp CUDA │                        │ - Local llama.cpp CPU  │
└────────────────────────┘                        └────────────────────────┘
```

---

## 2. Security & Operational Guarantees

1. **Zero Permanent Disk Storage**: GGUF weights reside solely in ephemeral memory tagged with `FILE_ATTRIBUTE_TEMPORARY`.
2. **Zero Cloud Credential Exposure**: Client machines never receive permanent Cloudflare credentials; access is strictly brokered via 15-minute presigned URLs.
3. **Hardware Access Control**: Every download request validates `X-Device-Id`. Lost, unauthorized, or compromised devices can be immediately revoked from the database.
4. **Resumable HTTP Range Transfers**: Supported via standard HTTP 206 Partial Content Range requests directly from Cloudflare edge nodes.
5. **Safe Memory Wiping**: Unload closes model handles, zero-wipes the initial 4KB header, unlinks the temporary file, and calls Windows `psapi.dll!EmptyWorkingSet()`.

---

## 3. Deploy to Render

### 3.1 Blueprint Deployment (`render.yaml`)
1. In the **Render Dashboard** (https://dashboard.render.com/):
   - Click **New +** -> **Blueprint**.
   - Select this repository (`25it038-beep/julyllm`).
   - Render reads `render.yaml` automatically and configures:
     - `july-postgres` (Managed PostgreSQL Free/Starter Instance)
     - `july-distribution-backend` (FastAPI Web Service)
   - When prompted for environment variables, fill in your Cloudflare R2 credentials:
     - `AWS_ACCESS_KEY_ID`: Cloudflare R2 Access Key
     - `AWS_SECRET_ACCESS_KEY`: Cloudflare R2 Secret Key
   - Click **Apply**.
2. Once deployed, your backend will be live at:
   `https://july-distribution-backend.onrender.com`

### 3.2 Environment Variables

| Variable | Description |
| :--- | :--- |
| `DATABASE_URL` | Auto-populated by Render Managed PostgreSQL |
| `JULY_R2_ENDPOINT` | `https://21e5f9f23e1d60cb56bf1200e89255f3.r2.cloudflarestorage.com/` |
| `JULY_R2_BUCKET` | `july` |
| `JULY_R2_OBJECT` | `july-final.gguf` |
| `AWS_ACCESS_KEY_ID` | Cloudflare R2 Access Key |
| `AWS_SECRET_ACCESS_KEY`| Cloudflare R2 Secret Key |
| `ALLOWED_ORIGINS` | `*` |

---

## 4. Workstation Installation & CLI Suite

### 4.1 Windows Installation
Run from Windows PowerShell:
```powershell
irm https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/start.ps1 | iex
```

### 4.2 Linux & Tails OS (Amnesia) Native Installation
Run natively inside the terminal on **Tails OS**, **Debian**, **Ubuntu**, **Kali Linux**, or any Linux distribution:

```bash
# One-liner launch & execution (cURL):
curl -fsSL https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/start.sh | bash

# Or via wget:
wget -qO- https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/start.sh | bash

# Or direct headless installer:
curl -fsSL https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/install.sh | bash
```

#### Tails OS (Amnesia) Native Features:
- **Zero Global Root Changes**: Never uses `sudo`, installs into isolated user space.
- **Dual Storage Options**:
  - **Temporary Mode**: Operates in RAM/tmpfs; completely erased on reboot/shutdown.
  - **Persistent Mode**: Mounts inside Tails Persistent Storage (`~/Persistent/.july_runtime`) with configuration preserved across restarts.
- **Privacy Shield**: Hardware fingerprints disabled on Tails; identity protected via Tor routing.
- **Environment Fallback**: Supports headless zero-disk authentication via `export JULY_API_KEY="<token>"`.

### 4.3 Native CLI Commands (Cross-Platform)

```bash
# 1. Start interactive session directly
july

# 2. Chat with genuine AI inference (one-off or interactive)
july chat "Explain quantum entanglement and Bell inequalities."

# 3. Launch autonomous cognitive agent with multi-step reasoning & tool calling
july agent "Find the derivative of x^3 + 4x^2 - 5x + 7 and evaluate at x=2"

# 4. Run system diagnostics & environment health check
july doctor

# 5. Display architecture, runtime, and OS telemetry
july version

# 6. List available foundation models (July LLM 3B, Gravity LLM 7B+)
july models

# 7. Authenticate with Clerk Identity & Access Management
july login

# 8. Log out and shred local cryptographic vault
july logout

# 9. View or modify configuration
july config
july config --set selected_model gravity

# 10. Check for model updates
july update

# 11. Comprehensive help reference
july help
```

---

## 5. Repository Structure

```
├── july_distribution/
│   ├── installer/               # Cross-Platform Remote Installers
│   │   ├── start.sh             # Linux & Tails OS one-liner autonomous runtime
│   │   ├── install.sh           # Linux & Tails OS native installer
│   │   ├── start.ps1            # Windows PowerShell all-in-one runtime
│   │   └── install.ps1          # Windows PowerShell client installer
│   ├── linux/                   # Native Linux Environment Package
│   │   ├── july                 # Native Linux executable launcher
│   │   ├── bootstrap.py         # Self-healing environment bootstrapper
│   │   └── requirements.txt     # Linux client Python dependencies
│   ├── cli/                     # CLI Package Entrypoints
│   │   ├── main.py              # CLI executable entrypoint
│   │   ├── __main__.py          # Module execution dispatcher
│   │   └── __init__.py          # Package initializer
│   ├── client/                  # Cross-Platform Client Runtime
│   │   ├── cli.py               # Main CLI engine, agent & REPL
│   │   ├── os_detector.py       # Tails OS & Linux distro detection
│   │   ├── runtime.py           # llama.cpp engine, genuine local inference
│   │   ├── storage.py           # Ephemeral RAM storage (FILE_ATTRIBUTE_TEMPORARY)
│   │   ├── downloader.py        # Resumable Range downloader with SHA-256
│   │   ├── hardware.py          # CPU / RAM / CUDA VRAM & privacy telemetry
│   │   ├── auth.py              # Client token manager
│   │   ├── clerk_auth.py        # Clerk IAM authentication & session vault
│   │   ├── customization.py     # Per-user system prompt & personality presets
│   │   └── config.py            # Client settings & persistence routing
│   ├── bin/                     # Windows Launchers
│   │   ├── july.ps1             # PowerShell executable
│   │   └── july.cmd             # Windows CMD launcher
│   └── tests/
│       ├── test_linux_tails.py  # Linux & Tails OS test suite (11/11 pass)
│       └── test_multi_computer_distribution.py
├── scripts/
│   └── test_r2_connection.py    # Cloudflare R2 connection diagnostic
├── render.yaml                  # Render Blueprint (Infrastructure-as-Code)
├── Dockerfile                   # Containerized cloud build
├── requirements.txt             # Lightweight backend dependencies
└── README.md
```

---

## 6. Physical Memory Security Notice

While ephemeral RAM storage prevents files from persisting to disk, users with local Windows administrative access (`SYSTEM` / `SeDebugPrivilege`) or kernel debuggers can inspect physical memory while weights are active. True zero-extraction guarantees on client hardware are fundamentally impossible once weights reside in host RAM/VRAM.
