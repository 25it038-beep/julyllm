# ==============================================================================
# HS AI SOLUTIONS - JULY CLOUD AI
# Configuration Management Script for PowerShell
# Founder: Harshan Seliyan
# ==============================================================================

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [string]$Endpoint,

    [Parameter(Mandatory = $false)]
    [string]$ApiKey,

    [Parameter(Mandatory = $false)]
    [switch]$Show,

    [Parameter(Mandatory = $false)]
    [switch]$Reset
)

$ConfigDir = Join-Path $HOME ".july"
$ConfigFile = Join-Path $ConfigDir "config.json"

function Get-JulyConfig {
    if (Test-Path $ConfigFile) {
        try {
            $raw = Get-Content $ConfigFile -Raw | ConvertFrom-Json
            return $raw
        }
        catch {
            Write-Warning "Could not parse $ConfigFile. Using defaults."
        }
    }
    return [PSCustomObject]@{
        Endpoint = "https://july-cloud-inference.onrender.com"
        ApiKey = ""
        ConversationId = ""
        MaxTokens = 512
        Temperature = 0.7
    }
}

function Set-JulyConfig {
    param ($configObj)
    if (-not (Test-Path $ConfigDir)) {
        New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
    }
    $json = $configObj | ConvertTo-Json -Depth 4
    Set-Content -Path $ConfigFile -Value $json -Encoding UTF8
    Write-Host "[OK] Configuration saved to $ConfigFile" -ForegroundColor Green
}

if ($Reset) {
    if (Test-Path $ConfigFile) {
        Remove-Item $ConfigFile -Force
        Write-Host "[OK] Configuration reset." -ForegroundColor Yellow
    }
    exit 0
}

$currentConfig = Get-JulyConfig

if ($Endpoint) {
    # Strip trailing slash
    $currentConfig.Endpoint = $Endpoint.TrimEnd('/')
}

if ($ApiKey) {
    $currentConfig.ApiKey = $ApiKey
}

if ($Endpoint -or $ApiKey) {
    Set-JulyConfig $currentConfig
}

if ($Show -or (-not $Endpoint -and -not $ApiKey -and -not $Reset)) {
    Write-Host "`n=== JULY CLOUD CONFIGURATION ===" -ForegroundColor Cyan
    Write-Host "Config File:    $ConfigFile"
    Write-Host "Endpoint:       $($currentConfig.Endpoint)"
    $maskedKey = if ($currentConfig.ApiKey) {
        if ($currentConfig.ApiKey.Length -gt 8) {
            $currentConfig.ApiKey.Substring(0, 4) + "..." + $currentConfig.ApiKey.Substring($currentConfig.ApiKey.Length - 4)
        } else {
            "****"
        }
    } else {
        "(none set)"
    }
    Write-Host "API Key:        $maskedKey"
    Write-Host "Active Conv ID: $(if ($currentConfig.ConversationId) { $currentConfig.ConversationId } else { '(new session on next chat)' })"
    Write-Host "================================`n"
}
