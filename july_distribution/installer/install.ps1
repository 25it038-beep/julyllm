# ================================================================================
# HS AI SOLUTIONS — JULY LLM WINDOWS INSTALLER
# Organization: HS AI Solutions
# Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
# One-liner execution:
# irm https://julyllm.onrender.com/install.ps1 | iex
# ================================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "     ██╗██╗   ██╗██╗  ██╗   ██╗    ██╗     ██╗     ███╗   ███╗" -ForegroundColor Cyan
Write-Host "     ██║██║   ██║██║  ╚██╗ ██╔╝    ██║     ██║     ████╗ ████║" -ForegroundColor Cyan
Write-Host "     ██║██║   ██║██║   ╚████╔╝     ██║     ██║     ██╔████╔██║" -ForegroundColor Cyan
Write-Host "██   ██║██║   ██║██║    ╚██╔╝      ██║     ██║     ██║╚██╔╝██║" -ForegroundColor Cyan
Write-Host "╚█████╔╝╚██████╔╝███████╗██║       ███████╗███████╗██║ ╚═╝ ██║" -ForegroundColor Cyan
Write-Host " ╚════╝  ╚═════╝ ╚══════╝╚═╝       ╚══════╝╚══════╝╚═╝     ╚═╝" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor DarkGray
Write-Host "            HS AI SOLUTIONS — AUTONOMOUS RUNTIME INSTALLER" -ForegroundColor White
Write-Host " Studio Portal : https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor DarkGray
Write-Host ""

$InstallRoot = Join-Path $env:LOCALAPPDATA "Programs\JulyRuntime"
$BinDir = Join-Path $InstallRoot "bin"
$ClientPackageDir = Join-Path $InstallRoot "july_distribution"

Write-Host "[1/4] Preparing Installation Directory: $InstallRoot" -ForegroundColor Green
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null

# Step 2: Acquire Client Distribution Files
Write-Host "[2/4] Downloading and Installing JULY Client Runtime..." -ForegroundColor Green

# Check if local source is present (e.g. running from repo clone on disk)
$LocalSourceFound = $false
if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $PotentialSource = Split-Path -Parent $PSScriptRoot -ErrorAction SilentlyContinue
    if ($PotentialSource -and (Test-Path (Join-Path $PotentialSource "client"))) {
        $TargetDist = Join-Path $InstallRoot "july_distribution"
        New-Item -ItemType Directory -Path $TargetDist -Force | Out-Null
        Copy-Item -Path "$PotentialSource\*" -Destination $TargetDist -Recurse -Force
        $LocalSourceFound = $true
    }
}

if (-not $LocalSourceFound) {
    # Downloading directly from official GitHub repository
    $ZipUrl = "https://github.com/25it038-beep/julyllm/archive/refs/heads/main.zip"
    $ZipFile = Join-Path $env:TEMP "julyllm_install_$(Get-Random).zip"
    $ExtractDir = Join-Path $env:TEMP "julyllm_extract_$(Get-Random)"

    try {
        Write-Host "      Fetching release archive from repository..." -ForegroundColor Gray
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile -UseBasicParsing
        Expand-Archive -Path $ZipFile -DestinationPath $ExtractDir -Force

        $SourceDist = Join-Path $ExtractDir "julyllm-main\july_distribution"
        if (Test-Path $SourceDist) {
            $TargetDist = Join-Path $InstallRoot "july_distribution"
            New-Item -ItemType Directory -Path $TargetDist -Force | Out-Null
            Copy-Item -Path "$SourceDist\*" -Destination $TargetDist -Recurse -Force
        } else {
            throw "Failed to locate july_distribution in downloaded archive."
        }
    } finally {
        Remove-Item -Path $ZipFile -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Generate executable launchers in bin directory
$CmdLauncher = @"
@echo off
set PYTHONPATH=%LOCALAPPDATA%\Programs\JulyRuntime
python -m july_distribution.client.cli %*
"@
Set-Content -Path (Join-Path $BinDir "july.cmd") -Value $CmdLauncher -Encoding ASCII

$PsLauncher = @"
param(
    [Parameter(ValueFromRemainingArguments = `$true)]
    [string[]]`$ScriptArgs
)
`$InstallRoot = Join-Path `$env:LOCALAPPDATA "Programs\JulyRuntime"
`$env:PYTHONPATH = `$InstallRoot
python -m july_distribution.client.cli @ScriptArgs
"@
Set-Content -Path (Join-Path $BinDir "july.ps1") -Value $PsLauncher -Encoding ASCII

# Step 3: Register PATH
Write-Host "[3/4] Registering User Environment PATH..." -ForegroundColor Green
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    $NewPath = if ([string]::IsNullOrWhiteSpace($UserPath)) { $BinDir } else { "$UserPath;$BinDir" }
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    $env:Path += ";$BinDir"
    Write-Host "      Added $BinDir to User PATH." -ForegroundColor Gray
} else {
    Write-Host "      $BinDir already present in User PATH." -ForegroundColor Gray
}

# Configure default server URL
$JulyConfigDir = Join-Path $env:USERPROFILE ".july"
New-Item -ItemType Directory -Path $JulyConfigDir -Force | Out-Null
$ConfigFile = Join-Path $JulyConfigDir "config.json"
$ConfigObj = @{
    server_url = "https://julyllm.onrender.com"
    hardware_mode = "auto"
    context_length = 2048
    n_threads = 4
    n_batch = 64
    n_gpu_layers = 0
    temperature = 0.7
    top_p = 0.9
    max_tokens = 512
    personality = "precision_engineer"
    system_prompt = "You are JULY LLM, an advanced autonomous neural model developed by HS AI Solutions. Deliver accurate, rigorous, and helpful answers."
    chunk_size_bytes = 8388608
}
if (Test-Path $ConfigFile) {
    try {
        $Existing = Get-Content $ConfigFile -Raw | ConvertFrom-Json
        foreach ($prop in $Existing.PSObject.Properties) {
            $ConfigObj[$prop.Name] = $prop.Value
        }
    } catch {}
}
$ConfigObj["server_url"] = "https://julyllm.onrender.com"
$ConfigObj | ConvertTo-Json -Depth 4 | Set-Content -Path $ConfigFile -Encoding UTF8
Write-Host "      Configured backend server: https://julyllm.onrender.com" -ForegroundColor Gray

# Step 4: Validate local Python & dependencies
Write-Host "[4/4] Verifying Python, llama.cpp and Voice runtime..." -ForegroundColor Green
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host "      Warning: python.exe not found on PATH. Please install Python 3.10+ from python.org." -ForegroundColor Yellow
} else {
    Write-Host "      Python located: $PythonExe" -ForegroundColor Gray
    try {
        $hasLlama = & $PythonExe -c "import llama_cpp; print('v' + llama_cpp.__version__)" 2>$null
        if ($hasLlama) {
            Write-Host "      llama-cpp-python engine: INSTALLED ($hasLlama)" -ForegroundColor Gray
        } else {
            Write-Host "      llama-cpp-python: Installing..." -ForegroundColor Yellow
            & $PythonExe -m pip install llama-cpp-python -q
        }
    } catch {
        Write-Host "      llama-cpp-python: Run 'pip install llama-cpp-python' for local inference." -ForegroundColor Yellow
    }

    try {
        $hasVoice = & $PythonExe -c "import whisper, sounddevice, pyttsx3; print('Ready')" 2>$null
        if ($hasVoice) {
            Write-Host "      Voice STT & Female TTS engines: INSTALLED" -ForegroundColor Gray
        } else {
            Write-Host "      Voice STT & Female TTS: Installing dependencies..." -ForegroundColor Yellow
            & $PythonExe -m pip install sounddevice pyttsx3 openai-whisper numpy -q
            Write-Host "      Voice STT & Female TTS engines: INSTALLED" -ForegroundColor Gray
        }
    } catch {
        Write-Host "      Voice dependencies: Run 'pip install sounddevice pyttsx3 openai-whisper' to enable voice." -ForegroundColor Yellow
    }
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "                    INSTALLATION COMPLETED SUCCESSFULLY!" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Available Commands:" -ForegroundColor White
Write-Host "  july install   - Initialize local environment and verify dependencies" -ForegroundColor Gray
Write-Host "  july register  - Register account: july register -u USER -e EMAIL -p PASS" -ForegroundColor Gray
Write-Host "  july login     - Authenticate with HS AI Solutions: july login -u USER -p PASS" -ForegroundColor Gray
Write-Host "  july status    - Display authentication, model state, and hardware telemetry" -ForegroundColor Gray
Write-Host "  july load      - Retrieve GGUF model into temporary RAM-backed storage" -ForegroundColor Gray
Write-Host "  july chat      - Start interactive chat running genuine local inference" -ForegroundColor Gray
Write-Host "  july live      - Launch real-time conversational voice AI companion session" -ForegroundColor Cyan
Write-Host "  july voice     - Configure Whisper speech-to-text and female TTS audio synthesis" -ForegroundColor Gray
Write-Host "  july config    - View and customize system instructions & persona" -ForegroundColor Gray
Write-Host "  july unload    - Safely unload model and wipe RAM storage" -ForegroundColor Gray
Write-Host "  july update    - Check for updated model versions on server" -ForegroundColor Gray
Write-Host ""
Write-Host "To begin, run: july login" -ForegroundColor Yellow
