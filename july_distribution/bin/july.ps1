# HS AI SOLUTIONS — JULY LLM CLI PowerShell Launcher
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    $PythonExe = "C:\Python314\python.exe"
}

$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$env:PYTHONPATH = "$RootDir;$RootDir\july_distribution"

& $PythonExe -m july_distribution.client.cli @ScriptArgs
