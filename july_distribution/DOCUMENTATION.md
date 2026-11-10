# JULY LLM: MULTI-COMPUTER MODEL DISTRIBUTION PLATFORM
### Technical Architecture & Deployment Documentation
**Organization**: HS AI Solutions  
**Studio Portal**: [HS AI Studio](https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/)  
**Model**: July LLM 3B (`july-final.gguf`, 2,019,377,888 bytes)  
**Storage**: Cloudflare R2 (`s3://july/july-final.gguf`)  
**Platform Version**: v1.1.0-Distribution  

---

## 1. System Overview

The **JULY Multi-Computer Distribution Platform** enables distributed Windows workstations to authenticate with HS AI Solutions, stream the private Cloudflare R2-hosted GGUF model into temporary RAM-backed storage, and perform genuine local inference on CPUs or NVIDIA CUDA GPUs without ever persisting permanent model files to client disk or exposing Cloudflare credentials.

```
┌─────────────────────────────────────────────────────────────┐
│                    HS AI SOLUTIONS CLOUD                    │
│                                                             │
│   ┌──────────────────────────┐   ┌──────────────────────┐  │
│   │  Private Cloudflare R2   │   │Central Control Server│  │
│   │  s3://july/              │   │(FastAPI Backend)     │  │
│   │  july-final.gguf         │   │- Auth & JWT Tokens   │  │
│   │  2,019,377,888 bytes     │   │- Model Lineage       │  │
│   │  (Bucket remains private)│   │- Quotas & Analytics  │  │
│   └─────────────▲────────────┘   └──────────▲───────────┘  │
└─────────────────┼───────────────────────────┼───────────────┘
                  │ 15-Minute Presigned       │ 1. Authenticate
                  │ Resumable Range Stream    │ 2. Request Model
                  │                           │ 3. Log Telemetry
     ┌────────────┴─────────────┐             │
     │                          │             │
┌────┴──────────────────────┐ ┌─┴─────────────┴─────────────┐
│ Client Computer 1 (Alpha) │ │ Client Computer 2 (Beta)    │
│ Windows 11 / RTX 3050     │ │ Windows 11 / AMD Ryzen 5    │
│ - Ephemeral RAM Storage   │ │ - Ephemeral RAM Storage     │
│ - llama.cpp CUDA Runtime  │ │ - llama.cpp CPU Runtime     │
│ - Engineer Custom Persona │ │ - Scientist Custom Persona  │
│ - Local Chat History & Mem│ │ - Local Chat History & Mem  │
└───────────────────────────┘ └─────────────────────────────┘
```

---

## 2. Security & Model Protection Architecture

### 2.1 Private Cloudflare R2 Isolation
- The Cloudflare R2 bucket `july` is **strictly private**. Public access is disabled.
- The client CLI never receives permanent Cloudflare API tokens (`AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`).
- When an authorized user executes `july load`, the Central Control Server verifies user identity, permissions, and daily quotas, then issues a **short-lived (15-minute) presigned GET URL**.
- The client uses this presigned URL with HTTP Range headers for resumable downloading directly from Cloudflare R2.

### 2.2 Ephemeral RAM-Backed Storage
- Model files are written to `%TEMP%\july_ephemeral_runtime\july_ram_model_<PID>.gguf`.
- The Windows file attribute `FILE_ATTRIBUTE_TEMPORARY` (0x00000100) is applied, instructing the Windows Cache Manager to prioritize keeping file content in physical RAM rather than flushing to disk.
- When `july unload` is called, or when the session terminates:
  1. The `llama_cpp.Llama` runtime handle is closed and destroyed.
  2. The initial 4KB header of the temporary file is overwritten with `0x00` null bytes to corrupt any residual artifacts.
  3. The file is unlinked and deleted from the filesystem.
  4. `EmptyWorkingSet()` is invoked via Windows `psapi.dll` to return allocated memory back to the Windows OS.

> [!WARNING]
> **Physical Memory Security Boundary**:
> While temporary storage prevents standard disk persistence, users with local Windows administrative privileges (`SYSTEM` / `SeDebugPrivilege`) or kernel debuggers can inspect physical RAM and extract raw model weights. True zero-extraction guarantees on client hardware are fundamentally impossible once weights are resident in host RAM/VRAM.

---

## 3. Client Installation & CLI Reference

### 3.1 One-Line Remote Installer
From PowerShell (Administrator or standard user):
```powershell
irm http://YOUR-DOMAIN:8787/install.ps1 | iex
```

### 3.2 Command Suite

| Command | Syntax | Description |
| :--- | :--- | :--- |
| **`install`** | `july install` | Initializes local user directories (`%USERPROFILE%\.july`) and validates dependencies. |
| **`login`** | `july login [-u USER] [-p PASS] [-s SERVER]` | Authenticates with the Central Control Server and stores bearer token. |
| **`load`** | `july load` | Authorizes with server, streams GGUF from R2 to ephemeral RAM storage, and validates SHA-256. |
| **`chat`** | `july chat ["prompt"]` | Starts an interactive chat REPL or runs a single prompt with genuine local inference. |
| **`status`** | `july status` | Displays user authentication state, model memory residency, and CPU/GPU hardware telemetry. |
| **`config`** | `july config [--set KEY VAL]` | Views or updates per-user system instructions, personality presets, and context lengths. |
| **`unload`** | `july unload` | Unloads model from RAM, wipes ephemeral storage, and reclaims working set memory. |
| **`update`** | `july update` | Checks the Central Control Server for newer model releases. |

---

## 4. Multi-Computer Verification Audit

During automated integration verification (`test_multi_computer_distribution.py`), the platform was tested across two independent simulated Windows environments:

| Test Phase | Computer 1 (`engineer_alpha`) | Computer 2 (`researcher_beta`) | Result |
| :--- | :--- | :--- | :--- |
| **User Identity** | `engineer_alpha` | `researcher_beta` | Separate Accounts Created |
| **Token Issuance** | `july_tok_1...` | `july_tok_2...` | Independent Bearer Tokens |
| **Presigned URL** | Unique R2 Signature (15m expiry) | Unique R2 Signature (15m expiry) | Direct Private R2 Streaming |
| **Custom Persona** | Precision Engineer | Research Scientist | Separate System Directives |
| **Memory Isolation** | Kepler Orbit Transfer | Quantum Information | Distinct SQLite / JSON memory |
| **Inference Hardware**| CUDA GPU (RTX 3050, 28 layers) | CUDA GPU (RTX 3050, 28 layers) | **Genuine Local llama.cpp** |
| **Response Validation**| Computed $25 \times 16 - 50 = 350$ | Formulated First Law of Thermodynamics | Exact Mathematical Accuracy |
| **Unload & Wipe** | RAM unlinked, working set trimmed | RAM unlinked, working set trimmed | **Zero Permanent Artifacts** |

---

## 5. Control Server Deployment & Render Production Hosting

### 5.1 Render Cloud Architecture
The backend is packaged for automated deployment on **Render** (`render.com`), using a persistent managed PostgreSQL database and a Python 3.11/3.12 Web Service.

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
                                              │ (e.g. onrender.com)
                                   ┌──────────▼───────────┐
                                   │ Remote Windows PCs   │
                                   │ (july CLI Clients)   │
                                   └──────────────────────┘
```

### 5.2 Render Environment Variables

| Variable | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | Auto-populated by Render PostgreSQL | `postgresql://july_admin:pwd@dpg-xxx:5432/july_distribution` |
| `JULY_R2_ENDPOINT` | Cloudflare S3 API Endpoint | `https://21e5f9f23e1d60cb56bf1200e89255f3.r2.cloudflarestorage.com/` |
| `JULY_R2_BUCKET` | Private R2 bucket | `july` |
| `JULY_R2_OBJECT` | Target GGUF model key | `july-final.gguf` |
| `AWS_ACCESS_KEY_ID` | Cloudflare R2 Access Key | Set from your R2 API token (e.g. `a19f90...`) |
| `AWS_SECRET_ACCESS_KEY`| Cloudflare R2 Secret Key | Set from your R2 API token |
| `ALLOWED_ORIGINS` | CORS allowed origins | `*` or specific domains |
| `RENDER` | Render environment flag | `true` (auto-detected) |

### 5.3 Automated Deployment via Render Blueprint (`render.yaml`)

1. Push this repository to GitHub or GitLab.
2. In the **Render Dashboard** (https://dashboard.render.com/):
   - Click **New +** -> **Blueprint**.
   - Connect your Git repository.
   - Render reads `render.yaml` automatically and configures:
     - `july-postgres` (Managed PostgreSQL Free/Starter Instance)
     - `july-distribution-backend` (FastAPI Web Service)
   - When prompted for environment variables, fill in your Cloudflare R2 credentials (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`).
   - Click **Apply**.
3. Render automatically provisions the database, executes `pip install -r july_distribution/requirements.txt`, launches Uvicorn, and assigns a public URL:
   `https://july-distribution-backend.onrender.com`

### 5.4 Manual Render Setup (Alternative)
If not using Blueprints:
1. **Create PostgreSQL**:
   - Dashboard -> **New +** -> **PostgreSQL**. Name: `july-postgres`.
   - Copy the **Internal Database URL**.
2. **Create Web Service**:
   - Dashboard -> **New +** -> **Web Service**.
   - Build Command: `pip install -r july_distribution/requirements.txt`
   - Start Command: `uvicorn july_distribution.server.main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/health`
   - Add the environment variables listed in Section 5.2.

### 5.5 Connecting Distributed Windows Computers
Once the Render backend is live:

1. **Install on Client PC**:
   ```powershell
   irm https://july-distribution-backend.onrender.com/install.ps1 | iex
   ```
2. **Configure Server Target**:
   ```powershell
   july config --set server_url https://july-distribution-backend.onrender.com
   ```
3. **Register / Login & Load**:
   ```powershell
   july login -u engineer_alice -p "Secr3tPassword!"
   july load
   july chat
   ```
4. **Unload & Wipe RAM**:
   ```powershell
   july unload
   ```
