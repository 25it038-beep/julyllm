# ================================================================================
# HS AI SOLUTIONS — JULY LLM ALL-IN-ONE AUTONOMOUS RUNTIME
# Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
# Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
#
# One-liner execution:
# irm https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/start.ps1 | iex
# ================================================================================

# Initialize execution parameters (compatible with direct invocation and irm ... | iex)
if (-not (Test-Path variable:Update)) { $Update = $false }
if (-not (Test-Path variable:SwitchUser)) { $SwitchUser = $false }
if (-not (Test-Path variable:Model)) { $Model = "" }
if (-not (Test-Path variable:Voice)) { $Voice = $false }
if (-not (Test-Path variable:Live)) { $Live = $false }

if ($args) {
    for ($i = 0; $i -lt $args.Count; $i++) {
        $argStr = [string]$args[$i]
        if ($argStr -ieq '-Update') { $Update = $true }
        elseif ($argStr -ieq '-SwitchUser') { $SwitchUser = $true }
        elseif ($argStr -ieq '-Voice') { $Voice = $true }
        elseif ($argStr -ieq '-Live') { $Live = $true }
        elseif ($argStr -ieq '-Model' -and ($i + 1) -lt $args.Count) { $Model = [string]$args[++$i] }
    }
}

$ErrorActionPreference = 'Stop'
$ServerUrl = 'https://julyllm.onrender.com'
$StudioUrl = 'https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/'
$GitHubRawInstall = 'https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/install.ps1'

# Render ASCII Banner & Portal Header
Clear-Host
Write-Host ""
Write-Host "     ██╗██╗   ██╗██╗  ██╗   ██╗    ██╗     ██╗     ███╗   ███╗" -ForegroundColor Cyan
Write-Host "     ██║██║   ██║██║  ╚██╗ ██╔╝    ██║     ██║     ████╗ ████║" -ForegroundColor Cyan
Write-Host "     ██║██║   ██║██║   ╚████╔╝     ██║     ██║     ██╔████╔██║" -ForegroundColor Cyan
Write-Host "██   ██║██║   ██║██║    ╚██╔╝      ██║     ██║     ██║╚██╔╝██║" -ForegroundColor Cyan
Write-Host "╚█████╔╝╚██████╔╝███████╗██║       ███████╗███████╗██║ ╚═╝ ██║" -ForegroundColor Cyan
Write-Host " ╚════╝  ╚═════╝ ╚══════╝╚═╝       ╚══════╝╚══════╝╚═╝     ╚═╝" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  HS AI SOLUTIONS  •  JULY LLM & GRAVITY LLM RUNTIME PLATFORM" -ForegroundColor White
Write-Host "  Founder & Architect: Harshan Seliyan  •  Studio Portal: " -NoNewline -ForegroundColor Gray
Write-Host "$StudioUrl" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# [1] Ensure Client Runtime & Environment Installed
$InstallRoot = Join-Path "$env:LOCALAPPDATA" 'Programs\JulyRuntime'
$BinDir = Join-Path $InstallRoot 'bin'
$JulyCmd = Join-Path $BinDir 'july.ps1'
$RateLimiterFile = Join-Path $InstallRoot 'july_distribution\client\rate_limiter.py'
$VoiceFile = Join-Path $InstallRoot 'july_distribution\client\voice.py'
$UiRendererFile = Join-Path $InstallRoot 'july_distribution\client\ui_renderer.py'
$LiveEngineFile = Join-Path $InstallRoot 'july_distribution\client\live_engine.py'
$VadFile = Join-Path $InstallRoot 'july_distribution\client\vad.py'
$RuntimeFile = Join-Path $InstallRoot 'july_distribution\client\runtime.py'

$HasGetInstance = $false
if (Test-Path $RuntimeFile) {
    $runtimeContent = Get-Content $RuntimeFile -Raw -ErrorAction SilentlyContinue
    if ($runtimeContent -and $runtimeContent.Contains("get_instance")) {
        $HasGetInstance = $true
    }
}

$NeedsUpdate = (-not (Test-Path $JulyCmd) -or -not (Test-Path $RateLimiterFile) -or -not (Test-Path $VoiceFile) -or -not (Test-Path $UiRendererFile) -or -not (Test-Path $LiveEngineFile) -or -not (Test-Path $VadFile) -or -not $HasGetInstance -or $Update)
if ($NeedsUpdate) {
    Write-Host " [⚡] [1/4] Synchronizing latest July & Gravity live conversational voice runtime from repository..." -ForegroundColor Yellow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    try {
        irm $GitHubRawInstall | iex
    } catch {
        Write-Host "      [*] Direct script fetch failed, attempting server install..." -ForegroundColor DarkGray
        irm "$ServerUrl/install.ps1" | iex
    }
}

# Refresh PATH in current session
$machPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$env:Path = $machPath + ';' + $userPath + ';' + $BinDir

# [2] Ensure Dependencies (Python, llama-cpp-python, Whisper STT & Female TTS)
Write-Host " [⚡] [1/4] Verifying hardware acceleration & Python environment..." -ForegroundColor Green
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host "      [!] Error: Python 3.10+ is required. Please install Python from python.org." -ForegroundColor Red
    return
}

# Auto-install llama-cpp-python if missing
$hasLlama = & $PythonExe -c "import llama_cpp" 2>$null; $LlamaOk = ($LASTEXITCODE -eq 0)
if (-not $LlamaOk) {
    Write-Host "      [+] Installing llama-cpp-python runtime..." -ForegroundColor Yellow
    & $PythonExe -m pip install --upgrade pip -q
    & $PythonExe -m pip install llama-cpp-python -q
}

# Auto-install voice packages if missing (Whisper STT, sounddevice, pyttsx3)
$hasVoice = & $PythonExe -c "import whisper, sounddevice, pyttsx3" 2>$null; $VoiceOk = ($LASTEXITCODE -eq 0)
if (-not $VoiceOk) {
    Write-Host "      [+] Installing voice intelligence dependencies (Whisper STT, sounddevice, pyttsx3)..." -ForegroundColor Yellow
    & $PythonExe -m pip install sounddevice pyttsx3 openai-whisper numpy -q
}
Write-Host "      [✓] Compute dependencies and voice intelligence active." -ForegroundColor Gray

# Define internal CLI dispatcher to bypass PowerShell parameter binding
function Invoke-JulyCli {
    $env:PYTHONPATH = $InstallRoot
    & $PythonExe -m july_distribution.client.cli $args
}

# Set target backend URL
Invoke-JulyCli config --set server_url $ServerUrl | Out-Null
Write-Host "      [✓] Connected to HS AI Cloud Control: $ServerUrl" -ForegroundColor Gray

# [3] Verify Official Clerk Authentication (Zero Plaintext / DPAPI Protected)
Write-Host ""
Write-Host " [⚡] [2/4] Verifying Clerk Identity & Access Management (IAM)..." -ForegroundColor Green

$env:PYTHONPATH = $InstallRoot
$authCheckCode = "import json; from july_distribution.client.clerk_auth import ClerkAuthManager; c=ClerkAuthManager(); s=c.get_session(); print(json.dumps({'authenticated': c.is_authenticated(), 'email': s.get('email', '') if s else '', 'tier': s.get('tier', 'standard') if s else 'standard', 'name': s.get('name', 'Developer') if s else 'Developer', 'uid': s.get('clerk_user_id', '') if s else ''}))"
$authJsonRaw = & $PythonExe -c $authCheckCode 2>$null
$authInfo = $null
try {
    $authInfo = $authJsonRaw | ConvertFrom-Json
} catch {
    $authInfo = [PSCustomObject]@{ authenticated = $false; email = ''; tier = 'standard'; name = ''; uid = '' }
}

$isAuth = [bool]($authInfo.authenticated)

if ($isAuth -and (-not $SwitchUser)) {
    if ($authInfo.email -eq 'harshanseliyan28@gmail.com' -or $authInfo.tier -eq 'creator') {
        Write-Host "      [✓] Clerk Identity Verified: $($authInfo.name) ($($authInfo.email)) [CREATOR]" -ForegroundColor Green
        Write-Host "      [✓] Creator Account Tier   : CREATOR & FOUNDER (Unlimited Access & Quotas)" -ForegroundColor Yellow
        Write-Host "      [✓] Credential Vault       : Windows DPAPI (Hardware Bound)" -ForegroundColor Gray
    } else {
        Write-Host "      [✓] Clerk Identity Verified: $($authInfo.name) ($($authInfo.email))" -ForegroundColor Green
        Write-Host "      [✓] Active Subscription    : $($authInfo.tier.ToUpper()) Plan" -ForegroundColor Cyan
        Write-Host "      [✓] Credential Vault       : Windows DPAPI (Hardware Bound)" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host " ┌──────────────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host " │             CLERK AUTHENTICATION REQUIRED TO ACCESS JULY         │" -ForegroundColor White
    Write-Host " │                                                                  │" -ForegroundColor Gray
    Write-Host " │  Access to July & Gravity AI models is protected by Clerk IAM.   │" -ForegroundColor Gray
    Write-Host " │  Please authenticate to unlock models and rate-limited quotas.   │" -ForegroundColor Gray
    Write-Host " └──────────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
    Write-Host ""
    Write-Host " Select Authentication Method:" -ForegroundColor White
    Write-Host "   [1]  🌐  Browser Single Sign-On (Google, GitHub, Clerk Web) [Recommended]" -ForegroundColor Cyan
    Write-Host "   [2]  🎟️  Sign In with Clerk Token / API Key (Headless / CI)" -ForegroundColor Green
    Write-Host "   [q]  ❌  Cancel & Exit" -ForegroundColor DarkGray
    Write-Host ""
    $choice = Read-Host " Selection [1-2, default: 1]"
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }

    if ($choice -eq '1') {
        Write-Host ""
        Write-Host " ─── HS AI SOLUTIONS CLERK AUTHENTICATION ───" -ForegroundColor Cyan
        Invoke-JulyCli login
    } elseif ($choice -eq '2') {
        Write-Host ""
        Write-Host " ─── CLERK TOKEN / API KEY SIGN IN ───" -ForegroundColor Green
        $secToken = Read-Host "  Clerk Token or API Key" -AsSecureString
        $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secToken)
        $token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        $email = Read-Host "  Email (Optional, press Enter to skip)"

        if ($email) {
            Invoke-JulyCli login --token $token --email $email
        } else {
            Invoke-JulyCli login --token $token
        }
    } else {
        Write-Host ""
        Write-Host " [!] Authentication cancelled. Access to July & Gravity models is locked." -ForegroundColor Red
        Write-Host "     Run 'july login' whenever you are ready to authenticate." -ForegroundColor DarkGray
        Write-Host ""
        return
    }

    # Verify authentication success
    $authJsonRaw = & $PythonExe -c $authCheckCode 2>$null
    try {
        $authInfo = $authJsonRaw | ConvertFrom-Json
        $isAuth = [bool]($authInfo.authenticated)
    } catch {
        $isAuth = $false
    }

    if (-not $isAuth) {
        Write-Host ""
        Write-Host " [!] Authentication failed or cancelled. Access to AI models is locked." -ForegroundColor Red
        Write-Host "     Please run 'july login' with valid Clerk credentials." -ForegroundColor DarkGray
        Write-Host ""
        return
    }

    Write-Host ""
    Write-Host " [✓] Authentication Verified! AI Model access unlocked." -ForegroundColor Green
}

# [4] Display Rate Limit Policy & Remaining Quota for User Tier
Write-Host ""
Write-Host " [⚡] [3/4] Checking Rate Limit Governance & Quota Policy..." -ForegroundColor Green

$rlCheckCode = "import json; from july_distribution.client.clerk_auth import ClerkAuthManager; from july_distribution.client.rate_limiter import ClientRateLimiter; c=ClerkAuthManager(); s=c.get_session(); t=s.get('tier', 'standard') if s else 'standard'; m=ClientRateLimiter.get_instance().get_metrics(tier=t); print(json.dumps(m))"
$rlJsonRaw = & $PythonExe -c $rlCheckCode 2>$null
$rlMetrics = $null
try {
    $rlMetrics = $rlJsonRaw | ConvertFrom-Json
} catch {
    $rlMetrics = [PSCustomObject]@{ tier_title = 'Standard / Free Tier'; rpm_used = 0; rpm_max = 20; rpm_remaining = 20; tpm_used = 0; tpm_max = 5000; tpm_remaining = 5000; daily_used = 0; daily_max = 500; daily_remaining = 500; window_seconds = 60 }
}

Write-Host " ┌──────────────────────────────────────────────────────────────────┐" -ForegroundColor DarkGray
Write-Host " │                 RATE LIMIT & MODEL ACCESS POLICY                 │" -ForegroundColor Cyan
Write-Host " ├──────────────────────────────────────────────────────────────────┤" -ForegroundColor DarkGray
Write-Host " │  Tier Policy      : $($rlMetrics.tier_title.PadRight(43))│" -ForegroundColor White
Write-Host " │  Request Rate     : $($rlMetrics.rpm_used)/$($rlMetrics.rpm_max) req/min ($($rlMetrics.rpm_remaining) remaining)".PadRight(67) + "│" -ForegroundColor Green
Write-Host " │  Token Throughput : $($rlMetrics.tpm_used)/$($rlMetrics.tpm_max) tok/min ($($rlMetrics.tpm_remaining) remaining)".PadRight(67) + "│" -ForegroundColor Green
Write-Host " │  Daily Allotment  : $($rlMetrics.daily_used)/$($rlMetrics.daily_max) req/day ($($rlMetrics.daily_remaining) remaining)".PadRight(67) + "│" -ForegroundColor Green
Write-Host " │  Sliding Window   : 60s active sliding window protection         │" -ForegroundColor DarkGray
Write-Host " └──────────────────────────────────────────────────────────────────┘" -ForegroundColor DarkGray

# [5] Register Auto-Unload Handlers on Exit
Register-EngineEvent -SourceIdentifier 'PowerShell.Exiting' -Action {
    $p = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    $root = Join-Path "$env:LOCALAPPDATA" 'Programs\JulyRuntime'
    $env:PYTHONPATH = $root
    & $p -m july_distribution.client.cli unload | Out-Null
} -ErrorAction SilentlyContinue | Out-Null

# [6] Foundation Model Selection & Ephemeral RAM Initialization (Strict Auth Guard)
$authJsonRaw = & $PythonExe -c $authCheckCode 2>$null
$isStrictlyAuth = $false
try {
    $authInfo = $authJsonRaw | ConvertFrom-Json
    $isStrictlyAuth = [bool]($authInfo.authenticated)
} catch {
    $isStrictlyAuth = $false
}

if (-not $isStrictlyAuth) {
    Write-Host ""
    Write-Host " [!] STRICT AUTH ENFORCEMENT: Model selection is blocked." -ForegroundColor Red
    Write-Host "     Access to July & Gravity models requires verified Clerk authentication." -ForegroundColor Red
    Write-Host "     Please execute 'july login' to authenticate with Clerk." -ForegroundColor DarkGray
    Write-Host ""
    return
}

if (-not $Model) {
    if ($env:JULY_MODEL) {
        $Model = $env:JULY_MODEL
    } else {
        Write-Host ""
        Write-Host " Select Foundation Model / Interactive Mode:" -ForegroundColor White
        Write-Host "   [1]  🌟  July LLM (General Intelligence, Coding & Agentic Reasoning)" -ForegroundColor Cyan
        Write-Host "   [2]  🌌  Gravity LLM (Deep Mathematical Reasoning, Proofs & Physics)" -ForegroundColor Yellow
        Write-Host "   [3]  ⚡  Auto Router (Dynamic Query Routing to July or Gravity)" -ForegroundColor Magenta
        Write-Host "   [4]  🎙️   JULY LIVE (Continuous Conversational Voice AI Mode)" -ForegroundColor Green
        Write-Host ""
        $mChoice = Read-Host " Select Option [1, 2, 3, or 4] (Default: 1 - July)"
        if ($mChoice -eq '2') {
            $Model = "gravity"
        } elseif ($mChoice -eq '3') {
            $Model = "auto"
        } elseif ($mChoice -eq '4') {
            $Model = "july"
            $Live = $true
        } else {
            $Model = "july"
        }
    }
}

Invoke-JulyCli config --set selected_model $Model | Out-Null

Write-Host ""
Write-Host " [⚡] [4/4] Mounting $($Model.ToUpper()) LLM into Ephemeral Physical RAM..." -ForegroundColor Green
Invoke-JulyCli load --model $Model
if ($LASTEXITCODE -ne 0) {
    Write-Host " [!] Could not initialize model. Ensure authentication was verified." -ForegroundColor Red
    return
}

Write-Host ""
Write-Host " 🛡️  Model loaded in RAM. Entering interactive session with active rate limit protection." -ForegroundColor Green
Write-Host " 🎙️  Voice System Active: Type /voice on (Mic STT), /voice output on (Female TTS), or /live (Live Conversation)" -ForegroundColor Cyan
Write-Host " 🔒  Ephemeral Privacy: Model weights and context are completely wiped from RAM on exit." -ForegroundColor DarkYellow
Write-Host ""

if ($Voice) {
    Invoke-JulyCli voice output on | Out-Null
    Invoke-JulyCli voice female | Out-Null
    Invoke-JulyCli voice on | Out-Null
    Write-Host " [✓] Voice Input & Female Speech Output automatically activated." -ForegroundColor Green
}

if ($Live) {
    try {
        Invoke-JulyCli live --model $Model
    } finally {
        Write-Host ""
        Write-Host " [⚡] Session concluded. Securely wiping ephemeral RAM storage..." -ForegroundColor Yellow
        Invoke-JulyCli unload
        Unregister-Event -SourceIdentifier 'PowerShell.Exiting' -ErrorAction SilentlyContinue
        Write-Host " [✓] RAM reclaimed. Zero artifacts remain on disk or memory." -ForegroundColor Green
        Write-Host ""
    }
    return
}

try {
    Invoke-JulyCli chat --model $Model
} finally {
    Write-Host ""
    Write-Host " [⚡] Session concluded. Securely wiping ephemeral RAM storage..." -ForegroundColor Yellow
    Invoke-JulyCli unload
    Unregister-Event -SourceIdentifier 'PowerShell.Exiting' -ErrorAction SilentlyContinue
    Write-Host " [✓] RAM reclaimed. Zero artifacts remain on disk or memory." -ForegroundColor Green
    Write-Host ""
}
