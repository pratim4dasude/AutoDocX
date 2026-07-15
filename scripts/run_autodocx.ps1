$ErrorActionPreference = "Stop"

# Derive project root from the script location (scripts folder is one level below root)
$ProjectRoot = Split-Path -Parent $PSScriptRoot

$PythonExe    = "$ProjectRoot\runtime\python\python.exe"
$SetupScript  = "$ProjectRoot\scripts\setup_runtime.ps1"
$EnvFile      = "$ProjectRoot\.env"
$EnvExample   = "$ProjectRoot\.env.example"
$BackendPort  = 7832
$FrontendPort = 7833
$BackendUrl   = "http://127.0.0.1:$BackendPort"
$FrontendUrl  = "http://localhost:$FrontendPort"

$backend  = $null
$frontend = $null

function Write-Banner {
    Write-Host ""
    Write-Host "============================================"
    Write-Host "                 AutoDocX"
    Write-Host "============================================"
    Write-Host ""
}

function Stop-Servers {
    Write-Host ""
    Write-Host "Stopping AutoDocX..."

    if ($backend -ne $null) {
        try { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
    if ($frontend -ne $null) {
        try { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue } catch {}
    }

    foreach ($port in @($BackendPort, $FrontendPort)) {
        $pids = (
            netstat -aon |
            Select-String ":$port\s" |
            Select-String "LISTENING" |
            ForEach-Object { ($_ -split '\s+')[-1] }
        )
        foreach ($p in $pids) {
            if ($p -match '^\d+$') {
                try { Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue } catch {}
            }
        }
    }

    Write-Host "AutoDocX stopped."
    Start-Sleep -Seconds 1
}

# Show banner
Write-Banner

# Step 1: Install Python runtime on first run
if (-not (Test-Path $PythonExe)) {
    Write-Host "[Setup] First-time setup: installing AutoDocX private Python runtime."
    Write-Host "        This takes about 2 minutes and only happens once."
    Write-Host ""

    if (-not (Test-Path $SetupScript)) {
        Write-Host "[ERROR] Setup script not found: $SetupScript"
        exit 1
    }

    & $SetupScript

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Runtime setup failed. Check your internet connection and try again."
        exit 1
    }

    if (-not (Test-Path $PythonExe)) {
        Write-Host "[ERROR] Python runtime was not created at: $PythonExe"
        exit 1
    }

    Write-Host ""
    Write-Host "[Setup] Runtime ready."
    Write-Host ""
}

# Step 2: Create .env from example if missing. Streamlit will handle the API key setup.
if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvExample)) {
        Write-Host "[ERROR] .env.example not found."
        Write-Host "        Create a .env file in the project root with your LLM API key."
        pause
        exit 1
    }
    Copy-Item $EnvExample $EnvFile
    Write-Host "[Setup] .env file created. Streamlit will guide you to add your API key."
    Write-Host ""
}

# Step 3: Start both servers
Write-Host "[1/3] Starting FastAPI backend  (port $BackendPort)..."

$backend = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Minimized `
    -PassThru

Write-Host "[2/3] Starting Streamlit UI     (port $FrontendPort)..."

$frontend = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "-m streamlit run ui\streamlit_app.py --server.port $FrontendPort --server.headless true --server.fileWatcherType none" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Minimized `
    -PassThru

# Step 4: Wait for backend to be ready, then open browser
Write-Host "[3/3] Waiting for backend to be ready..."

$attempts = 0
$ready    = $false

while ($attempts -lt 40) {
    Start-Sleep -Seconds 1

    if ($backend.HasExited) {
        Write-Host ""
        Write-Host "[ERROR] Backend process exited unexpectedly (exit code $($backend.ExitCode))."
        Write-Host "        Check your .env file and make sure your API key is set correctly."
        Stop-Servers
        exit 1
    }

    try {
        $response = Invoke-WebRequest `
            -Uri "$BackendUrl/health" `
            -UseBasicParsing `
            -TimeoutSec 2 `
            -ErrorAction Stop

        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # Not ready yet, keep waiting
    }

    $attempts++
}

if (-not $ready) {
    Write-Host ""
    Write-Host "[ERROR] Backend did not respond after 40 seconds."
    Write-Host "        It may still be starting. Try opening $FrontendUrl manually."
    Write-Host ""
}

Write-Host ""
Write-Host "  AutoDocX is running."
Write-Host ""
Write-Host "  UI  : $FrontendUrl"
Write-Host "  API : $BackendUrl"
Write-Host "  Docs: $BackendUrl/docs"
Write-Host ""
Write-Host "  Close this window or press Ctrl+C to stop everything."
Write-Host ""

# Open Streamlit in the browser
Start-Process $FrontendUrl

# Step 5: Keep the window alive. Cleanup runs in finally when window closes.
try {
    while ($true) {
        Start-Sleep -Seconds 2

        if ($backend.HasExited -or $frontend.HasExited) {
            $which = if ($backend.HasExited) { "Backend" } else { "Streamlit UI" }
            Write-Host ""
            Write-Host "[$which] process exited unexpectedly. Shutting down."
            break
        }
    }
} finally {
    Stop-Servers
}
