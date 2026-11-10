# ================================================================================
# HS AI SOLUTIONS — JULY LLM WINDOWS INSTALLER
# Founder & Chief Architect: Harshan Seliyan
# Organization: HS AI Solutions
# One-liner execution:
# irm https://YOUR-DOMAIN/install.ps1 | iex
# ================================================================================

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "              JULY LLM: MULTI-COMPUTER DISTRIBUTION INSTALLER" -ForegroundColor Cyan
Write-Host "                             HS AI SOLUTIONS" -ForegroundColor Cyan
Write-Host "                      Founder: Harshan Seliyan" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$InstallRoot = Join-Path $env:LOCALAPPDATA "Programs\JulyRuntime"
$BinDir = Join-Path $InstallRoot "bin"
$ClientDir = Join-Path $InstallRoot "july_distribution"

Write-Host "[1/4] Preparing Installation Directory: $InstallRoot" -ForegroundColor Green
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
New-Item -ItemType Directory -Path $ClientDir -Force | Out-Null

# Identify current distribution source
$SourceRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$SourceRoot\client")) {
    $SourceRoot = "C:\Users\BS.Harshan seliyan\OneDrive\Desktop\collab-editor\july_distribution"
}

Write-Host "[2/4] Deploying JULY Client Files..." -ForegroundColor Green
Copy-Item "$SourceRoot\client" -Destination $ClientDir -Recurse -Force
Copy-Item "$SourceRoot\bin\*" -Destination $BinDir -Force

# Create root package __init__.py if needed
New-Item -ItemType File -Path "$ClientDir\__init__.py" -Force | Out-Null

Write-Host "[3/4] Registering User Environment PATH..." -ForegroundColor Green
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    $NewPath = "$UserPath;$BinDir"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    $env:Path += ";$BinDir"
    Write-Host "      Added $BinDir to User PATH." -ForegroundColor Gray
} else {
    Write-Host "      $BinDir already present in User PATH." -ForegroundColor Gray
}

Write-Host "[4/4] Verifying Python and llama.cpp runtime..." -ForegroundColor Green
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host "      Warning: python.exe not found on PATH. Please ensure Python 3.10+ is installed." -ForegroundColor Yellow
} else {
    Write-Host "      Python located at: $PythonExe" -ForegroundColor Gray
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "                    INSTALLATION COMPLETED SUCCESSFULLY!" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Available Commands:" -ForegroundColor White
Write-Host "  july install   - Initialize local environment and verify dependencies" -ForegroundColor Gray
Write-Host "  july login     - Authenticate with HS AI Solutions control server" -ForegroundColor Gray
Write-Host "  july load      - Retrieve GGUF model into temporary RAM-backed storage" -ForegroundColor Gray
Write-Host "  july chat      - Start interactive chat running genuine local inference" -ForegroundColor Gray
Write-Host "  july status    - Display authentication, model state, and hardware telemetry" -ForegroundColor Gray
Write-Host "  july config    - View and customize system instructions & persona" -ForegroundColor Gray
Write-Host "  july unload    - Safely unload model and wipe RAM storage" -ForegroundColor Gray
Write-Host "  july update    - Check for updated model versions on server" -ForegroundColor Gray
Write-Host ""
Write-Host "To begin, run: july login" -ForegroundColor Yellow
