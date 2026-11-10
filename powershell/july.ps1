<#
.SYNOPSIS
    JULY CLOUD AI - Standalone Windows PowerShell Client
.DESCRIPTION
    Interacts with the cloud-hosted JULY 3B LLM deployed on Render.
    Developed by HS AI Solutions | Founder: Harshan Seliyan
.EXAMPLE
    .\july.ps1 health
    .\july.ps1 ask "Explain the architecture of JULY LLM."
    .\july.ps1 chat
#>

[CmdletBinding()]
param (
    [Parameter(Position = 0, Mandatory = $false)]
    [ValidateSet("chat", "ask", "models", "status", "health", "config", "clear", "history", "stream", "help")]
    [string]$Command = "chat",

    [Parameter(Position = 1, Mandatory = $false, ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

# Configuration paths
$ConfigDir = Join-Path $HOME ".july"
$ConfigFile = Join-Path $ConfigDir "config.json"

function Get-JulyConfig {
    if (Test-Path $ConfigFile) {
        try {
            return (Get-Content $ConfigFile -Raw | ConvertFrom-Json)
        }
        catch {}
    }
    return [PSCustomObject]@{
        Endpoint = "https://july-cloud-inference.onrender.com"
        ApiKey = ""
        ConversationId = ""
        MaxTokens = 512
        Temperature = 0.7
    }
}

function Save-JulyConfig {
    param ($configObj)
    if (-not (Test-Path $ConfigDir)) {
        New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
    }
    $configObj | ConvertTo-Json -Depth 4 | Set-Content -Path $ConfigFile -Encoding UTF8
}

$Config = Get-JulyConfig
$BaseUrl = $Config.Endpoint.TrimEnd('/')
$ApiKey = $Config.ApiKey

function Show-Banner {
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "        JULY CLOUD AI               " -ForegroundColor Yellow
    Write-Host "         HS AI SOLUTIONS            " -ForegroundColor White
    Write-Host "     Founder: Harshan Seliyan       " -ForegroundColor DarkGray
    Write-Host "====================================" -ForegroundColor Cyan
}

function Invoke-JulyApi {
    param (
        [string]$Path,
        [string]$Method = "GET",
        [object]$Body = $null,
        [int]$MaxRetries = 2
    )

    $url = "$BaseUrl$Path"
    $headers = @{
        "Accept" = "application/json"
    }
    if ($ApiKey) {
        $headers["Authorization"] = "Bearer $ApiKey"
        $headers["X-API-Key"] = $ApiKey
    }

    $attempt = 0
    while ($attempt -le $MaxRetries) {
        try {
            $jsonBody = if ($Body) { $Body | ConvertTo-Json -Depth 6 } else { $null }
            $params = @{
                Uri = $url
                Method = $Method
                Headers = $headers
                ContentType = "application/json; charset=utf-8"
                UseBasicParsing = $true
            }
            if ($jsonBody) { $params["Body"] = $jsonBody }

            $response = Invoke-WebRequest @params
            if ($response.Content) {
                return ($response.Content | ConvertFrom-Json)
            }
            return $null
        }
        catch {
            $status = $_.Exception.Response.StatusCode.value__
            # Recoverable 502/503 (Render spinup or cold start)
            if (($status -eq 502 -or $status -eq 503) -and $attempt -lt $MaxRetries) {
                Write-Host "[WAIT] Cloud container is warming up (HTTP $status). Retrying in 5 seconds..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds 5
                $attempt++
                continue
            }
            Write-Error "API Request Failed: $($_.Exception.Message)"
            return $null
        }
    }
}

function Invoke-JulyStream {
    param (
        [string]$PromptText,
        [string]$ConvId
    )

    $url = "$BaseUrl/v1/chat"
    $payloadObj = @{
        message = $PromptText
        conversation_id = $ConvId
        stream = $true
        temperature = [double]$Config.Temperature
        max_tokens = [int]$Config.MaxTokens
    }
    $postData = [System.Text.Encoding]::UTF8.GetBytes(($payloadObj | ConvertTo-Json -Depth 4))

    $request = [System.Net.WebRequest]::Create($url)
    $request.Method = "POST"
    $request.ContentType = "application/json; charset=utf-8"
    if ($ApiKey) {
        $request.Headers.Add("Authorization", "Bearer $ApiKey")
        $request.Headers.Add("X-API-Key", "$ApiKey")
    }
    $request.Timeout = 120000 # 2 minutes

    try {
        $stream = $request.GetRequestStream()
        $stream.Write($postData, 0, $postData.Length)
        $stream.Close()

        $response = $request.GetResponse()
        $respStream = $response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($respStream, [System.Text.Encoding]::UTF8)

        $fullAnswer = ""
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            if ($line -like "data: *") {
                $rawChunk = $line.Substring(6).Trim()
                if ($rawChunk -eq "[DONE]") {
                    break
                }
                try {
                    $jsonChunk = $rawChunk | ConvertFrom-Json
                    if ($jsonChunk.token) {
                        Write-Host -NoNewline $jsonChunk.token -ForegroundColor Green
                        $fullAnswer += $jsonChunk.token
                    }
                    elseif ($jsonChunk.error) {
                        Write-Host "`n[Server Error]: $($jsonChunk.error)" -ForegroundColor Red
                    }
                }
                catch {
                    # Fallback plain text stream
                    Write-Host -NoNewline $rawChunk -ForegroundColor Green
                    $fullAnswer += $rawChunk
                }
            }
        }
        $reader.Close()
        $respStream.Close()
        $response.Close()
        Write-Host ""
        return $fullAnswer
    }
    catch {
        Write-Host "`n[Stream Error]: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# --- Command Router ---
switch ($Command) {
    "health" {
        Show-Banner
        Write-Host "Probing cloud endpoint: $BaseUrl/health ..." -ForegroundColor DarkGray
        $res = Invoke-JulyApi -Path "/health"
        if ($res) {
            Write-Host "Status:        $($res.status.ToUpper())" -ForegroundColor $(if ($res.status -eq "ready") { "Green" } else { "Yellow" })
            Write-Host "Model Loaded:  $($res.model_loaded)"
            Write-Host "Model Name:    $($res.model_name)"
            Write-Host "Mock Mode:     $($res.is_mock)"
            Write-Host "Memory Avail:  $($res.memory_available_mb) MB"
            Write-Host "CPU Usage:     $($res.cpu_percent) %"
            Write-Host "Uptime:        $($res.uptime_seconds) seconds"
        }
    }

    "status" {
        Show-Banner
        $res = Invoke-JulyApi -Path "/v1/status"
        if ($res) {
            Write-Host "Application:      $($res.app) v$($res.version)" -ForegroundColor Cyan
            Write-Host "Organization:     $($res.organization)"
            Write-Host "Founder:          $($res.founder)"
            Write-Host "Model Status:     $($res.model_status)" -ForegroundColor $(if ($res.model_status -eq "ready") { "Green" } else { "Yellow" })
            Write-Host "Architecture:     $($res.model_architecture)"
            Write-Host "Quantization:     $($res.quantization)"
            Write-Host "Parameters:       $($res.parameters)"
            Write-Host "Context Window:   $($res.context_length) tokens"
            Write-Host "CPU Threads:      $($res.threads)"
            Write-Host "Active Requests:  $($res.active_requests)"
            Write-Host "Total Requests:   $($res.total_requests)"
            Write-Host "Tokens Generated: $($res.total_tokens_generated)"
            Write-Host "Avg Latency:      $($res.average_latency_ms) ms"
            Write-Host "Generation Speed: $($res.generation_speed_tps) tokens/sec"
            Write-Host "Error Count:      $($res.error_count)"
        }
    }

    "models" {
        $res = Invoke-JulyApi -Path "/v1/models"
        if ($res -and $res.data) {
            Write-Host "`nAvailable Cloud Models:" -ForegroundColor Cyan
            foreach ($m in $res.data) {
                Write-Host " - $($m.id) (Owner: $($m.owned_by))" -ForegroundColor Green
            }
        }
    }

    "ask" {
        $prompt = ($Arguments -join " ").Trim()
        if (-not $prompt) {
            Write-Host "Usage: .\july.ps1 ask `"<your question>`"" -ForegroundColor Yellow
            exit 1
        }
        if (-not $Config.ConversationId) {
            $Config.ConversationId = [guid]::NewGuid().ToString()
            Save-JulyConfig $Config
        }
        Write-Host "JULY: " -ForegroundColor Yellow -NoNewline
        $ans = Invoke-JulyStream -PromptText $prompt -ConvId $Config.ConversationId
    }

    "stream" {
        $prompt = ($Arguments -join " ").Trim()
        if (-not $prompt) {
            Write-Host "Usage: .\july.ps1 stream `"<your prompt>`"" -ForegroundColor Yellow
            exit 1
        }
        if (-not $Config.ConversationId) {
            $Config.ConversationId = [guid]::NewGuid().ToString()
            Save-JulyConfig $Config
        }
        Write-Host "JULY (Streaming): " -ForegroundColor Yellow -NoNewline
        $null = Invoke-JulyStream -PromptText $prompt -ConvId $Config.ConversationId
    }

    "clear" {
        if ($Config.ConversationId) {
            $res = Invoke-JulyApi -Path "/v1/conversations/$($Config.ConversationId)" -Method "DELETE"
            Write-Host "[OK] Conversation session $($Config.ConversationId) cleared from cloud memory." -ForegroundColor Green
        }
        $Config.ConversationId = [guid]::NewGuid().ToString()
        Save-JulyConfig $Config
        Write-Host "[OK] Initialized new local session ID: $($Config.ConversationId)" -ForegroundColor Cyan
    }

    "history" {
        if (-not $Config.ConversationId) {
            Write-Host "No active conversation. Start one with: .\july.ps1 chat" -ForegroundColor Yellow
            exit 0
        }
        $res = Invoke-JulyApi -Path "/v1/conversations/$($Config.ConversationId)"
        if ($res -and $res.messages) {
            Write-Host "`n=== Conversation History ($($Config.ConversationId)) ===" -ForegroundColor Cyan
            foreach ($m in $res.messages) {
                $roleColor = if ($m.role -eq "user") { "Cyan" } else { "Green" }
                Write-Host "[$($m.role.ToUpper())] $($m.timestamp)" -ForegroundColor $roleColor
                Write-Host "$($m.content)`n"
            }
        } else {
            Write-Host "No messages found in cloud session $($Config.ConversationId)." -ForegroundColor Yellow
        }
    }

    "config" {
        & "$PSScriptRoot\config.ps1" -Show
    }

    "chat" {
        Show-Banner

        # Health check on startup
        Write-Host "Connecting to JULY Cloud ($BaseUrl)..." -ForegroundColor DarkGray
        $health = Invoke-JulyApi -Path "/health"
        if (-not $health) {
            Write-Host "[ERROR] Could not reach server at $BaseUrl" -ForegroundColor Red
            Write-Host "Check network or run: .\install.ps1" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "Status:     $($health.status.ToUpper())" -ForegroundColor $(if ($health.status -eq "ready") { "Green" } else { "Yellow" })
        Write-Host "Model:      $($health.model_name)" -ForegroundColor White
        Write-Host "Engine:     llama.cpp (GGUF CPU)" -ForegroundColor DarkCyan
        Write-Host "Deployment: RENDER CLOUD" -ForegroundColor DarkCyan
        Write-Host "------------------------------------" -ForegroundColor DarkGray
        Write-Host "Type '/exit' to quit, '/clear' to reset memory.`n" -ForegroundColor DarkGray

        if (-not $Config.ConversationId) {
            $Config.ConversationId = [guid]::NewGuid().ToString()
            Save-JulyConfig $Config
        }

        while ($true) {
            Write-Host "You: " -ForegroundColor Cyan -NoNewline
            $inputLine = [Console]::ReadLine()

            if ([string]::IsNullOrWhiteSpace($inputLine)) {
                continue
            }

            if ($inputLine.Trim() -in @("/exit", "exit", "quit", ":q")) {
                Write-Host "`nSession ended. Goodbye!" -ForegroundColor Yellow
                break
            }

            if ($inputLine.Trim() -eq "/clear") {
                if ($Config.ConversationId) {
                    $null = Invoke-JulyApi -Path "/v1/conversations/$($Config.ConversationId)" -Method "DELETE"
                }
                $Config.ConversationId = [guid]::NewGuid().ToString()
                Save-JulyConfig $Config
                Write-Host "[OK] Memory reset. New session started.`n" -ForegroundColor Green
                continue
            }

            Write-Host "`nJULY: " -ForegroundColor Yellow -NoNewline
            $null = Invoke-JulyStream -PromptText $inputLine -ConvId $Config.ConversationId
            Write-Host ""
        }
    }

    default {
        Show-Banner
        Write-Host "Commands:" -ForegroundColor Cyan
        Write-Host "  .\july.ps1 chat              - Interactive multi-turn chat"
        Write-Host "  .\july.ps1 ask `"<text>`"      - One-shot question"
        Write-Host "  .\july.ps1 stream `"<text>`"   - Stream token response"
        Write-Host "  .\july.ps1 status            - Inspect live model telemetry"
        Write-Host "  .\july.ps1 health            - Check Render service status"
        Write-Host "  .\july.ps1 models            - List registered models"
        Write-Host "  .\july.ps1 history           - Print current chat history"
        Write-Host "  .\july.ps1 clear             - Clear conversation memory"
        Write-Host "  .\july.ps1 config            - Show or update endpoint settings"
    }
}
