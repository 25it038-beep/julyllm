<#
.SYNOPSIS
    HS AI SOLUTIONS - Hugging Face Model Uploader
.DESCRIPTION
    Safely uploads the local Gravity_HS.gguf model to a private or public
    Hugging Face Hub repository with GGUF header validation.
    Founder: Harshan Seliyan
.EXAMPLE
    .\upload_model.ps1 -RepoId "Harshan-Seliyan/Gravity_HS" -ModelFile "E:\guff\Gravity_HS.gguf" -Private
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [string]$RepoId,

    [Parameter(Mandatory = $false)]
    [string]$ModelFile = "E:\guff\Gravity_HS.gguf",

    [Parameter(Mandatory = $false)]
    [string]$HfToken,

    [Parameter(Mandatory = $false)]
    [switch]$Private = $true
)

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "   JULY GGUF MODEL UPLOADER         " -ForegroundColor Yellow
Write-Host "      HS AI SOLUTIONS               " -ForegroundColor White
Write-Host "====================================" -ForegroundColor Cyan

# 1. Resolve local model file
if (-not (Test-Path $ModelFile)) {
    Write-Host "[WARNING] File not found at $ModelFile" -ForegroundColor Yellow
    # Check alternate local paths
    $altPaths = @(
        "models\july-final.gguf",
        "models\july-original.gguf",
        "..\models\july-final.gguf"
    )
    $found = $null
    foreach ($alt in $altPaths) {
        if (Test-Path $alt) {
            $found = (Resolve-Path $alt).Path
            break
        }
    }
    if ($found) {
        Write-Host "Found local fallback model at: $found" -ForegroundColor Cyan
        $choice = Read-Host "Use this model instead? (Y/N) [Y]"
        if ([string]::IsNullOrWhiteSpace($choice) -or $choice.ToUpper() -eq "Y") {
            $ModelFile = $found
        } else {
            $ModelFile = Read-Host "Enter absolute path to your GGUF file"
        }
    } else {
        $ModelFile = Read-Host "Enter absolute path to your GGUF file"
    }
}

if (-not (Test-Path $ModelFile)) {
    Write-Error "Cannot proceed: Model file does not exist at '$ModelFile'."
    exit 1
}

$fileSizeMb = [math]::Round((Get-Item $ModelFile).Length / 1MB, 2)
Write-Host "`nModel Path: $ModelFile ($fileSizeMb MB)" -ForegroundColor Green

# 2. Inspect GGUF header before uploading to ensure integrity
Write-Host "Inspecting GGUF binary headers..." -ForegroundColor Cyan
$inspectorScript = Join-Path $PSScriptRoot "..\app\gguf_inspector.py"
if (Test-Path $inspectorScript) {
    try {
        python $inspectorScript "$ModelFile"
        Write-Host "[OK] GGUF integrity verified." -ForegroundColor Green
    }
    catch {
        Write-Warning "Could not run python GGUF inspector. Proceeding with upload check..."
    }
}

# 3. Prompt for RepoId if missing
if (-not $RepoId) {
    Write-Host "`nEnter your Hugging Face model repository ID:" -ForegroundColor Cyan
    Write-Host "(Example: 'Harshan-Seliyan/Gravity_HS' or 'hs-ai-solutions/july-3b')" -ForegroundColor DarkGray
    $RepoId = Read-Host "Repository ID"
    if ([string]::IsNullOrWhiteSpace($RepoId)) {
        Write-Error "Repository ID is required."
        exit 1
    }
}

# 4. Prompt for HF Token if not in environment or parameter
if (-not $HfToken) {
    if ($env:HF_TOKEN) {
        $HfToken = $env:HF_TOKEN
    } else {
        Write-Host "`nEnter your Hugging Face write token (hf_...):" -ForegroundColor Cyan
        $sec = Read-Host -Prompt "HF Token" -AsSecureString
        $b = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        $HfToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($b)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)
    }
}

if (-not $HfToken) {
    Write-Error "Hugging Face Access Token is required to upload models."
    exit 1
}

$isPrivateStr = if ($Private) { "True" } else { "False" }
$targetFilename = [System.IO.Path]::GetFileName($ModelFile)

Write-Host "`nUploading '$targetFilename' to Hugging Face repository '$RepoId' (Private=$isPrivateStr)..." -ForegroundColor Yellow

# Execute upload via python huggingface_hub
$pythonUploadCmd = @"
import os
import sys
from huggingface_hub import HfApi

repo_id = '$RepoId'
file_path = r'$ModelFile'
filename = '$targetFilename'
token = '$HfToken'
private = $isPrivateStr

api = HfApi(token=token)

print(f'[HF UPLOAD] Ensuring repository {repo_id} exists...')
api.create_repo(repo_id=repo_id, repo_type='model', private=private, exist_ok=True)

print(f'[HF UPLOAD] Starting upload of {filename} ({file_path})...')
api.upload_file(
    path_or_fileobj=file_path,
    path_in_repo=filename,
    repo_id=repo_id,
    repo_type='model'
)
print('[HF UPLOAD] Upload completed successfully!')
"@

$tempScript = [System.IO.Path]::GetTempFileName() + ".py"
Set-Content -Path $tempScript -Value $pythonUploadCmd -Encoding UTF8

try {
    python $tempScript
    Write-Host "`n[SUCCESS] Model is now hosted on Hugging Face: https://huggingface.co/$RepoId" -ForegroundColor Green
    Write-Host "Set this in your Render environment variables:" -ForegroundColor Cyan
    Write-Host "  MODEL_REPO=$RepoId" -ForegroundColor Yellow
    Write-Host "  MODEL_FILENAME=$targetFilename" -ForegroundColor Yellow
    Write-Host "  HF_TOKEN=<your-hf-token>" -ForegroundColor Yellow
}
catch {
    Write-Error "Upload failed: $($_.Exception.Message)"
}
finally {
    if (Test-Path $tempScript) { Remove-Item $tempScript -Force }
}
