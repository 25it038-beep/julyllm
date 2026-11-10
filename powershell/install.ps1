# ==============================================================================
# HS AI SOLUTIONS - JULY CLOUD AI INSTALLER & SETUP
# Windows PowerShell Quick Setup & Configuration
# Founder: Harshan Seliyan
# ==============================================================================

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "   JULY CLOUD CLIENT SETUP          " -ForegroundColor Yellow
Write-Host "      HS AI SOLUTIONS               " -ForegroundColor White
Write-Host "====================================" -ForegroundColor Cyan

$ConfigDir = Join-Path $HOME ".july"
$ConfigFile = Join-Path $ConfigDir "config.json"

if (-not (Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
}

# Prompt 1: Render Endpoint URL
Write-Host "`nEnter your Render Web Service HTTPS URL:" -ForegroundColor Cyan
Write-Host "(Example: https://july-cloud-inference.onrender.com or http://localhost:8000 for local testing)" -ForegroundColor DarkGray
$defaultUrl = "http://localhost:8000"
$endpointInput = Read-Host "Endpoint [$defaultUrl]"
$endpoint = if ([string]::IsNullOrWhiteSpace($endpointInput)) { $defaultUrl } else { $endpointInput.Trim() }
$endpoint = $endpoint.TrimEnd('/')

# Prompt 2: API Key
Write-Host "`nEnter your JULY API Key (configured in Render Environment Variables):" -ForegroundColor Cyan
Write-Host "(Press Enter to use default dev key: 'july-hs-secret-key-2026')" -ForegroundColor DarkGray
$secureKey = Read-Host -Prompt "API Key" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
$plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

if ([string]::IsNullOrWhiteSpace($plainKey)) {
    $plainKey = "july-hs-secret-key-2026"
}

# Save configuration
$configObj = [PSCustomObject]@{
    Endpoint = $endpoint
    ApiKey = $plainKey
    ConversationId = [guid]::NewGuid().ToString()
    MaxTokens = 512
    Temperature = 0.7
}

$configObj | ConvertTo-Json -Depth 4 | Set-Content -Path $ConfigFile -Encoding UTF8
Write-Host "`n[OK] Configuration successfully saved to: $ConfigFile" -ForegroundColor Green

# Test Connectivity
Write-Host "`nTesting connection to $endpoint/health ..." -ForegroundColor Cyan
try {
    $headers = @{}
    if ($plainKey) {
        $headers["Authorization"] = "Bearer $plainKey"
    }
    $res = Invoke-RestMethod -Uri "$endpoint/health" -Headers $headers -TimeoutSec 10
    Write-Host "[SUCCESS] Connected to JULY Cloud!" -ForegroundColor Green
    Write-Host "  Service Status: $($res.status)" -ForegroundColor White
    Write-Host "  Model Loaded:   $($res.model_loaded)" -ForegroundColor White
    Write-Host "  Model Name:     $($res.model_name)" -ForegroundColor White
    Write-Host "  Mock Mode:      $($res.is_mock)" -ForegroundColor White
}
catch {
    Write-Host "[WARNING] Could not immediately reach endpoint: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "If deploying to Render, the container may still be starting or building." -ForegroundColor DarkGray
}

# Optional PowerShell Profile alias
Write-Host "`nDo you want to add the 'july' command alias to your PowerShell profile? (Y/N)" -ForegroundColor Cyan
$addAlias = Read-Host "Choice [Y]"
if ([string]::IsNullOrWhiteSpace($addAlias) -or $addAlias.ToUpper() -eq "Y") {
    $scriptPath = (Resolve-Path "$PSScriptRoot\july.ps1").Path
    $profilePath = $PROFILE
    if (-not (Test-Path $profilePath)) {
        $profileDir = Split-Path $profilePath
        if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Path $profileDir -Force | Out-Null }
        New-Item -ItemType File -Path $profilePath -Force | Out-Null
    }

    $aliasFunction = "`nfunction july { & '$scriptPath' @args }`n"
    $existing = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if ($existing -notlike "*function july*") {
        Add-Content -Path $profilePath -Value $aliasFunction
        Write-Host "[OK] Added 'july' function to $profilePath" -ForegroundColor Green
    } else {
        Write-Host "[OK] 'july' command is already registered in your PowerShell profile." -ForegroundColor Green
    }
}

Write-Host "`n====================================" -ForegroundColor Cyan
Write-Host "   SETUP COMPLETED SUCCESSFULLY!    " -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "You can now run:" -ForegroundColor White
Write-Host "   .\july.ps1 chat" -ForegroundColor Yellow
Write-Host "   .\july.ps1 ask `"Hello July`"" -ForegroundColor Yellow
Write-Host "   .\july.ps1 status`n" -ForegroundColor Yellow
