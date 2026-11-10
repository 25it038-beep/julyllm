# HS AI SOLUTIONS — JULY LLM CLI PowerShell Launcher
# Founder & Chief Architect: Harshan Seliyan

$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python.exe" }

$InstallRoot = Join-Path $env:LOCALAPPDATA "Programs\JulyRuntime"
if (Test-Path (Join-Path $InstallRoot "july_distribution")) {
    $env:PYTHONPATH = $InstallRoot
} else {
    $RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $env:PYTHONPATH = "$RootDir;$RootDir\july_distribution"
}

& $PythonExe -m july_distribution.client.cli $args
