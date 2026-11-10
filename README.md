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

## 4. Windows Client Commands

### 4.1 One-Line Remote Installer
Run from Windows PowerShell:
```powershell
irm https://july-distribution-backend.onrender.com/install.ps1 | iex
```

### 4.2 CLI Usage Suite

```powershell
# 1. Initialize local configuration
july install

# 2. Configure target backend server
july config --set server_url https://july-distribution-backend.onrender.com

# 3. Register user account (new users)
july register -u harshan -e harshan@hs-ai-solutions.internal -p "SecurePassword123!"

# 4. Authenticate & register local device hardware ID
july login -u harshan -p "SecurePassword123!"

# 5. Check authentication state & hardware detection (CPU/RAM/GPU VRAM)
july status

# 6. Stream model from Cloudflare R2 into ephemeral RAM storage (verifies SHA-256)
july load

# 7. Perform genuine local llama.cpp inference
july chat "Explain the principles of orbital mechanics and Hohmann transfer."

# 8. Unload model, wipe ephemeral storage, and reclaim physical RAM
july unload

# 9. Check for model updates
july update
```

---

## 5. Repository Structure

```
├── july_distribution/
│   ├── server/                  # FastAPI Distribution Backend
│   │   ├── main.py              # Endpoints, rate limiting, logging
│   │   ├── database.py          # PostgreSQL / SQLite dialect-agnostic models
│   │   ├── security.py          # PBKDF2 auth, device registration, tokens
│   │   └── r2_manager.py        # Cloudflare R2 S3 gateway, presigned URLs
│   ├── client/                  # Distributable Windows Client
│   │   ├── cli.py               # PowerShell / CMD entry points
│   │   ├── runtime.py           # llama.cpp engine, genuine local inference
│   │   ├── storage.py           # Ephemeral RAM storage (FILE_ATTRIBUTE_TEMPORARY)
│   │   ├── downloader.py        # Resumable Range downloader with SHA-256
│   │   ├── hardware.py          # CPU / RAM / CUDA VRAM telemetry
│   │   ├── auth.py              # Client token manager
│   │   ├── customization.py     # Per-user system prompt & personality presets
│   │   └── config.py            # Client settings
│   ├── installer/
│   │   └── install.ps1          # Dynamic PowerShell client installer
│   ├── bin/
│   │   ├── july.ps1             # PowerShell executable
│   │   └── july.cmd             # Windows CMD launcher
│   └── tests/
│       └── test_multi_computer_distribution.py  # Multi-computer test suite (100% pass)
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
