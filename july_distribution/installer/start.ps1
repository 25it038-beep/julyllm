# ================================================================================
# HS AI SOLUTIONS — JULY LLM ALL-IN-ONE AUTOMATED RUNTIME
# Founder & Chief Architect: Harshan Seliyan
# Organization: HS AI Solutions
# One-liner execution:
# irm https://julyllm.onrender.com/start.ps1 | iex
# ================================================================================

$ErrorActionPreference = 'Stop'
$ServerUrl = 'https://julyllm.onrender.com'

Write-Host ''
Write-Host '================================================================================' -ForegroundColor Cyan
Write-Host '                HS AI SOLUTIONS — JULY LLM AUTONOMOUS RUNTIME                    ' -ForegroundColor Cyan
Write-Host '                           Founder: Harshan Seliyan                             ' -ForegroundColor Cyan
Write-Host '================================================================================' -ForegroundColor Cyan
Write-Host ''

# [1] Ensure Client Runtime & Environment Installed
$InstallRoot = Join-Path $env:LOCALAPPDATA 'Programs\JulyRuntime'
$BinDir = Join-Path $InstallRoot 'bin'
$JulyCmd = Join-Path $BinDir 'july.ps1'

if (-not (Test-Path $JulyCmd)) {
    Write-Host '[1/5] Client runtime not found. Initializing installation...' -ForegroundColor Yellow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    irm "$ServerUrl/install.ps1" | iex
}

# Refresh PATH in current session
$machPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$env:Path = $machPath + ';' + $userPath + ';' + $BinDir

# [2] Ensure Dependencies (Python & llama-cpp-python)
Write-Host '[2/5] Verifying dependencies and environment...' -ForegroundColor Green
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host '      [!] Error: Python 3.10+ is required. Please install Python from python.org.' -ForegroundColor Red
    return
}

# Auto-install llama-cpp-python if missing
$hasLlama = & $PythonExe -c "import llama_cpp" 2>$null; $LlamaOk = ($LASTEXITCODE -eq 0)
if (-not $LlamaOk) {
    Write-Host '      [+] Installing llama-cpp-python for local inference...' -ForegroundColor Yellow
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install llama-cpp-python -q
}
Write-Host '      [+] Dependencies verified and ready.' -ForegroundColor Gray

# Set target backend URL
& "$JulyCmd" config --set server_url $ServerUrl | Out-Null
Write-Host "      [+] Connected client to: $ServerUrl" -ForegroundColor Gray

# [3] Interactive Login or Register Selection
Write-Host ''
Write-Host 'Please choose an action:' -ForegroundColor White
Write-Host '  [1] Login (Existing user)' -ForegroundColor Cyan
Write-Host '  [2] Register (New account)' -ForegroundColor Cyan
$choice = Read-Host 'Select [1 or 2]'

if ($choice -eq '2') {
    Write-Host ''
    Write-Host '--- ACCOUNT REGISTRATION ---' -ForegroundColor Yellow
    $username = Read-Host 'Choose Username'
    $email = Read-Host 'Enter Email'
    $password = Read-Host 'Choose Password' -AsSecureString
    $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
    $pwd = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

    Write-Host 'Registering account on HS AI Solutions Cloud...' -ForegroundColor Gray
    & "$JulyCmd" register -u $username -e $email -p $pwd
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[!] Registration failed or user already exists. Proceeding to login...' -ForegroundColor Yellow
    }
    & "$JulyCmd" login -u $username -p $pwd
} else {
    Write-Host ''
    Write-Host '--- USER AUTHENTICATION ---' -ForegroundColor Yellow
    $username = Read-Host 'Username'
    $password = Read-Host 'Password' -AsSecureString
    $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
    $pwd = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

    & "$JulyCmd" login -u $username -p $pwd
}

if ($LASTEXITCODE -ne 0) {
    Write-Host '[!] Authentication failed. Please check credentials.' -ForegroundColor Red
    return
}

# [4] Register Auto-Unload Handlers on Exit
# Handles window close event
Register-EngineEvent -SourceIdentifier 'PowerShell.Exiting' -Action {
    & "$env:LOCALAPPDATA\Programs\JulyRuntime\bin\july.ps1" unload | Out-Null
} -ErrorAction SilentlyContinue | Out-Null

# [5] Load Model into RAM and Run Chat with Guaranteed Unload Finally
Write-Host ''
Write-Host '[4/5] Loading JULY LLM 3B into ephemeral RAM-backed storage...' -ForegroundColor Green
& "$JulyCmd" load
if ($LASTEXITCODE -ne 0) {
    Write-Host '[!] Failed to load model from Cloudflare R2.' -ForegroundColor Red
    return
}

Write-Host ''
Write-Host '[5/5] Model active in physical RAM. Entering chat session...' -ForegroundColor Green
Write-Host 'NOTE: When you close PowerShell or exit chat, the model will be automatically wiped from RAM.' -ForegroundColor DarkYellow
Write-Host ''

try {
    & "$JulyCmd" chat
} finally {
    Write-Host ''
    Write-Host '[+] Session ended. Safely unloading model and wiping RAM...' -ForegroundColor Yellow
    & "$JulyCmd" unload
    Unregister-Event -SourceIdentifier 'PowerShell.Exiting' -ErrorAction SilentlyContinue
    Write-Host '[+] RAM storage wiped and memory reclaimed successfully.' -ForegroundColor Green
}
