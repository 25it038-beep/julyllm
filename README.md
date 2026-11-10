# JULY 3B — CLOUD AI INFRASTRUCTURE
### HS AI SOLUTIONS | Founder: Harshan Seliyan

Production-grade cloud AI inference infrastructure designed to host and execute a pretrained 3 Billion parameter GGUF model (`Gravity_HS.gguf`) on Render cloud servers with persistent disk storage, FastAPI backend, llama.cpp CPU inference engine, and a standalone Windows PowerShell CLI client.

---

## Architecture Overview

```
       +---------------------------------------------+
       |           WINDOWS CLIENT COMPUTER           |
       |  (Any PC - Zero CUDA / Python requirements) |
       +---------------------------------------------+
                              |
                              | HTTPS (SSE Streaming)
                              v
       +---------------------------------------------+
       |             RENDER WEB SERVICE              |
       |               (Docker Runtime)              |
       |  +---------------------------------------+  |
       |  |            FastAPI Backend            |  |
       |  |  - OpenAI-compatible API              |  |
       |  |  - Native JULY Chat & SSE Streaming   |  |
       |  |  - Token Rate Limiting & Auth         |  |
       |  |  - SQLite Conversation Memory         |  |
       |  |  - Real-time System Telemetry         |  |
       |  +---------------------------------------+  |
       |                      |                      |
       |                      v                      |
       |  +---------------------------------------+  |
       |  |       llama.cpp Engine (CPU-Only)     |  |
       |  |  - Thread-optimized inference         |  |
       |  |  - Memory-aware context budgeting     |  |
       |  |  - Sequential request lock queue      |  |
       |  +---------------------------------------+  |
       |                      ^                      |
       |                      | Weights in RAM       |
       +----------------------|----------------------+
                              |
                     +-----------------+
                     | Persistent Disk |
                     |     /models     |
                     +-----------------+
                              ^
                              | Secure atomic download
                              |
                 +--------------------------+
                 |   HUGGING FACE HUB       |
                 | (Private Model Checkpoint|
                 |    Gravity_HS.gguf)      |
                 +--------------------------+
```

---

## Repository Structure

```
july-cloud-inference/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI server with OpenAI & Native endpoints
│   ├── config.py                # Environment configuration & settings
│   ├── model_loader.py          # Atomic HF synchronizer & llama.cpp loader
│   ├── gguf_inspector.py        # Binary GGUF metadata & tensor parser
│   ├── inference.py             # Inference engine, request queue & SSE streamer
│   ├── security.py              # API key verification & rate limiter
│   ├── conversations.py         # SQLite persistent multi-turn memory
│   ├── monitoring.py            # Operational telemetry & hardware metrics
│   └── schemas.py               # Pydantic request/response data contracts
│
├── powershell/
│   ├── july.ps1                 # Standalone PowerShell interactive client
│   ├── install.ps1              # One-click client installer & config setup
│   ├── config.ps1               # Client configuration manager
│   └── upload_model.ps1         # Secure Hugging Face GGUF uploader
│
├── scripts/
│   ├── download_model.py        # Standalone model downloader with validation
│   ├── benchmark.py             # Empirical TPS and latency benchmarking suite
│   └── health_check.py          # Container liveness & readiness probe
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py              # API endpoint & chat integration tests
│   ├── test_model.py            # GGUF header inspection & corrupted file tests
│   └── test_security.py         # Auth, admin verification & rate limiting tests
│
├── Dockerfile                   # Production container definition for Render
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render Blueprint (Infrastructure-as-Code)
├── .dockerignore                # Container build exclusions
├── .gitignore                   # Git exclusions (blocks GGUF weights & keys)
├── .env.example                 # Environment variables template
└── README.md                    # Complete deployment guide
```

---

## 10-Phase End-to-End Deployment Guide

### PHASE 1: Inspect the Existing GGUF Model

Before uploading or deploying, verify that your model file (`Gravity_HS.gguf` or local equivalent) contains valid GGUF binary headers, compatible architecture, and correct quantization.

Run the inspection tool from PowerShell:

```powershell
# Navigate to the repository
cd july-cloud-inference

# Inspect your model file (e.g. E:\guff\Gravity_HS.gguf)
python app/gguf_inspector.py "E:\guff\Gravity_HS.gguf"
```

Expected Output:
```json
{
  "status": "valid",
  "file_name": "Gravity_HS.gguf",
  "architecture": "llama",
  "model_name": "JULY LLM",
  "quantization": "MOSTLY_Q4_K_M",
  "estimated_parameters": 3212749888,
  "parameter_label": "3B",
  "context_length": 131072,
  "embedding_length": 3072,
  "vocabulary_size": 128256,
  "is_compatible": true
}
```

---

### PHASE 2: Create a Hugging Face Model Repository

1. Sign in to [Hugging Face](https://huggingface.co).
2. Click **New Model** (`https://huggingface.co/new`).
3. Set:
   - **Model Name**: `Gravity_HS`
   - **Owner**: Your Hugging Face username (e.g., `Harshan-Seliyan`)
   - **Visibility**: `Private` *(Recommended to protect proprietary weights)*.
4. Go to **Settings > Access Tokens** (`https://huggingface.co/settings/tokens`).
5. Create a token with **Write** permission (e.g. `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`).

---

### PHASE 3: Upload Gravity_HS.gguf from Windows PowerShell

Use the provided automated PowerShell upload script. It validates GGUF binary integrity before uploading and guarantees your model remains private:

```powershell
cd july-cloud-inference\powershell

.\upload_model.ps1 `
    -RepoId "YOUR_HF_USERNAME/Gravity_HS" `
    -ModelFile "E:\guff\Gravity_HS.gguf" `
    -Private
```

> **Credential Note**: When prompted, securely paste your Hugging Face write token (`hf_...`). The script will verify the GGUF file, create the repository if needed, and upload the file with progress tracking.

---

### PHASE 4: Create the GitHub Application Repository

> **Critical Rule**: Never commit large `.gguf` files, `.env` files, or API credentials to GitHub. The included `.gitignore` automatically blocks them.

```powershell
cd july-cloud-inference

# Initialize git repository
git init
git add .
git commit -m "feat: JULY 3B Cloud AI Infrastructure - HS AI SOLUTIONS"

# Add your GitHub remote and push
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/july-cloud-inference.git
git branch -M main
git push -u origin main
```

---

### PHASE 5: Connect GitHub to Render

1. Sign in to the [Render Dashboard](https://dashboard.render.com).
2. Click **New +** > **Web Service**.
3. Select **Build and deploy from a Git repository**.
4. Connect your GitHub account and select `july-cloud-inference`.
5. Configure the base settings:
   - **Name**: `july-cloud-inference`
   - **Region**: `Oregon (US West)` or closest region
   - **Branch**: `main`
   - **Runtime**: `Docker`

---

### PHASE 6: Configure the Render Persistent Disk

Render containers have an ephemeral filesystem. If you do not attach a persistent disk, the 2GB model weights would be re-downloaded on every deployment or server restart.

1. In the Web Service settings on Render, scroll to **Disks**.
2. Click **Add Disk**:
   - **Name**: `july-models`
   - **Mount Path**: `/models`
   - **Size**: `10 GB` (provides ample room for `Gravity_HS.gguf` + SQLite conversation database).

---

### PHASE 7: Configure Environment Variables

In the Render Web Service settings, navigate to **Environment** and configure the following variables:

| Variable Name | Value / Description | Required |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Yes |
| `PORT` | `8000` | Yes |
| `MODELS_DIR` | `/models` | Yes |
| `MODEL_REPO` | `YOUR_HF_USERNAME/Gravity_HS` | Yes |
| `MODEL_FILENAME` | `Gravity_HS.gguf` | Yes |
| `MODEL_PATH` | `/models/Gravity_HS.gguf` | Yes |
| `HF_TOKEN` | `hf_xxxxxxxxxxxxxxxxxxxxxx` *(Hugging Face read token)* | Yes (if private) |
| `API_KEY` | `your-secure-custom-api-key` *(Used by PowerShell client)* | Yes |
| `ADMIN_KEY` | `your-secure-admin-key` *(Used for /admin endpoints)* | Yes |
| `N_THREADS` | `2` *(Optimized for CPU instance)* | Yes |
| `N_CTX` | `2048` *(Optimal memory-aware context length)* | Yes |
| `N_BATCH` | `512` | Yes |
| `RATE_LIMIT_RPM` | `60` | Yes |
| `MOCK_INFERENCE` | `false` | Yes |

---

### PHASE 8: Deploy the Docker Application

1. Click **Create Web Service** (or **Manual Deploy > Deploy latest commit**).
2. Render will build the Docker container using `Dockerfile`:
   - Installs Debian build dependencies.
   - Compiles `llama-cpp-python` with CPU optimizations.
   - Sets up the `/models` volume.
   - Starts FastAPI with Uvicorn on port `8000`.

---

### PHASE 9: Verify Model Downloading and Loading

Monitor the **Logs** tab in Render:

1. **Download Phase**:
   ```
   [HS JULY LOADER] Initiating secure download from HF: YOUR_HF_USERNAME/Gravity_HS / Gravity_HS.gguf...
   [HS JULY LOADER] Model successfully stored and verified at /models/Gravity_HS.gguf
   ```
2. **Inspection Phase**:
   ```
   [HS JULY LOADER] Inspecting GGUF binary: /models/Gravity_HS.gguf...
   [HS JULY LOADER] Architecture: llama | Quantization: MOSTLY_Q4_K_M | Params: 3B | Native Context: 131072
   ```
3. **RAM Initialization Phase**:
   ```
   [HS JULY LOADER] Loading GGUF into llama.cpp (Threads=2, Context=2048, Batch=512, CPU-Only=True)...
   [HS JULY LOADER] JULY LLM loaded successfully in 4.12s.
   ```
4. **Health Check Readiness**:
   Test from any browser or terminal:
   ```bash
   curl https://july-cloud-inference.onrender.com/health
   ```
   Response:
   ```json
   {
     "status": "ready",
     "model_loaded": true,
     "model_name": "JULY-3B",
     "uptime_seconds": 128.4,
     "is_mock": false
   }
   ```

---

### PHASE 10: Connect Through Windows PowerShell

On any Windows computer (no Python, no CUDA, no local models required):

1. Run the interactive installer:
   ```powershell
   cd july-cloud-inference\powershell
   .\install.ps1
   ```
   - Enter your Render endpoint: `https://july-cloud-inference.onrender.com`
   - Enter your `API_KEY`.

2. Start the interactive chat:
   ```powershell
   .\july.ps1 chat
   ```

```
====================================
        JULY CLOUD AI
         HS AI SOLUTIONS
     Founder: Harshan Seliyan
====================================
Connecting to JULY Cloud (https://july-cloud-inference.onrender.com)...
Status:     READY
Model:      JULY-3B
Engine:     llama.cpp (GGUF CPU)
Deployment: RENDER CLOUD
------------------------------------
Type '/exit' to quit, '/clear' to reset memory.

You: Hello July, what is your identity and mission?

JULY: Hello! I am JULY, the AI assistant developed by HS AI Solutions,
founded by Harshan Seliyan. I am designed for reasoning, programming,
research, and technical problem-solving. How can I assist you today?
```

3. One-shot questions:
   ```powershell
   .\july.ps1 ask "Explain quicksort in Python"
   ```

4. Stream tokens directly to terminal:
   ```powershell
   .\july.ps1 stream "Write a short poem about space exploration"
   ```

5. Telemetry & performance metrics:
   ```powershell
   .\july.ps1 status
   ```

---

## Hardware & Cost Optimization Guide

### Memory & Instance Sizing

| Render Instance Type | RAM | vCPU | Suitability for JULY 3B (Q4_K_M) | Estimated Monthly Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Free** | 512 MB | Shared | **Incompatible** (OOM crash on model load) | \$0 |
| **Starter** | 512 MB | 0.5 vCPU | **Incompatible** (OOM crash on model load) | \$7 |
| **Standard** | 2 GB | 1 vCPU | **Functional** (Requires `N_CTX=1024` or `2048`) | \$25 |
| **Pro (Recommended)** | 4 GB | 2 vCPU | **Optimal** (Full 4K context headroom, smooth generation) | \$85 |

> **Important Architecture Note**: A persistent disk stores file weights across reboots, but it **does not substitute for RAM**. The model weights (~1.9 GB) and KV cache must be loaded directly into physical system memory.

### CPU Performance & Generation Throughput

- **Prompt Evaluation**: 40–80 tokens/second on 2 vCPUs.
- **Generation Speed**: 8–16 tokens/second (comfortable reading speed for human interaction).
- **Concurrency Control**: CPU inference on 2 vCPUs cannot parallelize multiple generations efficiently without thread thrashing. The application enforces a strict async queue lock so requests execute sequentially with sub-second queuing.

---

## Testing & Quality Assurance

Run the automated test suite locally:

```powershell
cd july-cloud-inference
python -m pytest tests/ -v
```

All 21 integration and unit tests cover:
- Binary GGUF inspection & validation.
- OpenAI-compatible chat completions and raw text completions.
- Native JULY chat and Server-Sent Event streaming.
- SQLite multi-session memory and deletion.
- API key authentication, rate limiting, and prompt sanitization.
- Mock mode simulation.

---

## Author & Copyright

**HS AI SOLUTIONS**  
**Founder & Chief Architect**: Harshan Seliyan  
*All Rights Reserved © 2026*
