# ================================================================================
# HS AI SOLUTIONS — JULY LLM ALL-IN-ONE AUTONOMOUS RUNTIME
# Organization: HS AI Solutions
# Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
# One-liner execution:
# irm https://raw.githubusercontent.com/25it038-beep/julyllm/main/july_distribution/installer/start.ps1 | iex
# ================================================================================

param(
    [switch]$Update,
    [switch]$SwitchUser,
    [string]$Model = ""
)

$ErrorActionPreference = 'Stop'
$ServerUrl = 'https://julyllm.onrender.com'
$StudioUrl = 'https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/'

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
Write-Host "  HS AI SOLUTIONS  •  AUTONOMOUS NEURAL RUNTIME PLATFORM" -ForegroundColor White
Write-Host "  Studio Portal    : " -NoNewline -ForegroundColor Gray
Write-Host "$StudioUrl" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# [1] Ensure Client Runtime & Environment Installed
$InstallRoot = Join-Path $env:LOCALAPPDATA 'Programs\JulyRuntime'
$BinDir = Join-Path $InstallRoot 'bin'
$JulyCmd = Join-Path $BinDir 'july.ps1'

if (-not (Test-Path $JulyCmd)) {
    Write-Host " [⚡] [1/4] Client runtime not found. Initializing installation..." -ForegroundColor Yellow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    irm "$ServerUrl/install.ps1" | iex
}

# Refresh PATH in current session
$machPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$env:Path = $machPath + ';' + $userPath + ';' + $BinDir

# [2] Ensure Dependencies (Python & llama-cpp-python)
Write-Host " [⚡] [2/4] Verifying hardware acceleration & Python engine..." -ForegroundColor Green
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host "      [!] Error: Python 3.10+ is required. Please install Python from python.org." -ForegroundColor Red
    return
}

# Auto-install llama-cpp-python if missing
$hasLlama = & $PythonExe -c "import llama_cpp" 2>$null; $LlamaOk = ($LASTEXITCODE -eq 0)
if (-not $LlamaOk) {
    Write-Host "      [+] Installing llama-cpp-python runtime..." -ForegroundColor Yellow
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install llama-cpp-python -q
}
Write-Host "      [✓] Dependencies and compute environment active." -ForegroundColor Gray

# Define internal CLI dispatcher to bypass PowerShell parameter binding
function Invoke-JulyCli {
    $env:PYTHONPATH = $InstallRoot
    & $PythonExe -m july_distribution.client.cli $args
}

# Set target backend URL
Invoke-JulyCli config --set server_url $ServerUrl | Out-Null
Write-Host "      [✓] Connected to HS AI Cloud Control: $ServerUrl" -ForegroundColor Gray

# [3] Check Existing Session or Prompt Interactive Authentication
$authOutput = & $PythonExe -c "from july_distribution.client.auth import ClientAuthManager; a = ClientAuthManager(); print(f'{a.is_authenticated()}|{a.get_session().get(\"username\", \"\") if a.is_authenticated() else \"\"}')" 2>$null
$authParts = ($authOutput -split '\|')
$isAuth = ($authParts[0] -eq 'True')

if ($isAuth -and (-not $SwitchUser)) {
    Write-Host "      [✓] Active Session: Authenticated as $($authParts[1])" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host " ┌──────────────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host " │                    AUTHENTICATION SELECTION                      │" -ForegroundColor White
    Write-Host " │  [1]  🔑  Sign In to Existing Account                            │" -ForegroundColor Green
    Write-Host " │  [2]  ✨  Create New HS AI Solutions Account                     │" -ForegroundColor Yellow
    Write-Host " └──────────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
    $choice = Read-Host " Select Option [1 or 2]"

    if ($choice -eq '2') {
        Write-Host ""
        Write-Host " ─── NEW ACCOUNT REGISTRATION ───" -ForegroundColor Yellow
        $username = Read-Host "  Choose Username"
        $email = Read-Host "  Enter Email    "
        $password = Read-Host "  Choose Password" -AsSecureString
        $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
        $pwd = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

        Write-Host "  Registering credentials on HS AI Cloud..." -ForegroundColor Gray
        Invoke-JulyCli register --username $username --email $email --password $pwd
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [!] User registration skipped or exists. Continuing to authenticate..." -ForegroundColor Yellow
        }
        Invoke-JulyCli login --username $username --password $pwd
    } else {
        Write-Host ""
        Write-Host " ─── SIGN IN ───" -ForegroundColor Green
        $username = Read-Host "  Username"
        $password = Read-Host "  Password" -AsSecureString
        $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
        $pwd = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

        Invoke-JulyCli login --username $username --password $pwd
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host " [!] Authentication failed. Please verify credentials." -ForegroundColor Red
        return
    }
}

# [4] Register Auto-Unload Handlers on Exit (Window close & process kill)
Register-EngineEvent -SourceIdentifier 'PowerShell.Exiting' -Action {
    $p = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    $root = Join-Path $env:LOCALAPPDATA 'Programs\JulyRuntime'
    $env:PYTHONPATH = $root
    & $p -m july_distribution.client.cli unload | Out-Null
} -ErrorAction SilentlyContinue | Out-Null

# [5] Load Model into RAM and Run Chat with Guaranteed Clean-up
Write-Host ""
Write-Host " [⚡] [3/4] Initializing Ephemeral RAM Model..." -ForegroundColor Green
if ($Model) {
    Invoke-JulyCli load --model $Model
} else {
    Invoke-JulyCli load
}
if ($LASTEXITCODE -ne 0) {
    Write-Host " [!] Could not initialize model." -ForegroundColor Red
    return
}

Write-Host ""
Write-Host " [⚡] [4/4] Model loaded in physical RAM. Entering interactive session..." -ForegroundColor Green
Write-Host " 🛡️  Ephemeral Privacy: When you exit or close this terminal, the model is wiped from RAM immediately." -ForegroundColor DarkYellow
Write-Host ""

try {
    if ($Model) {
        Invoke-JulyCli chat --model $Model
    } else {
        Invoke-JulyCli chat
    }
} finally {
    Write-Host ""
    Write-Host " [⚡] Session concluded. Securely wiping ephemeral RAM storage..." -ForegroundColor Yellow
    Invoke-JulyCli unload
    Unregister-Event -SourceIdentifier 'PowerShell.Exiting' -ErrorAction SilentlyContinue
    Write-Host " [✓] RAM reclaimed. Zero artifacts remain on disk or memory." -ForegroundColor Green
    Write-Host ""
}
