$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:TINYFISH_API_KEY -ErrorAction SilentlyContinue

try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Start Docker Desktop, wait for Engine running, then run this again"
        exit 1
    }
} catch {
    Write-Host "Start Docker Desktop, wait for Engine running, then run this again"
    exit 1
}

if (-not (Test-Path "$root\backend\.venv")) {
    python -m venv "$root\backend\.venv"
    & "$root\backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$root\backend\.venv\Scripts\python.exe" -m pip install -r "$root\backend\requirements.txt"
}

if (-not (Test-Path "$root\frontend\node_modules")) {
    Push-Location "$root\frontend"
    npm install
    Pop-Location
}

docker compose -f "$root\docker-compose.yml" up -d --wait

Push-Location "$root\backend"
& "$root\backend\.venv\Scripts\python.exe" -m app.preflight
$preflightExit = $LASTEXITCODE
Pop-Location
if ($preflightExit -ne 0) {
    exit 1
}

function Start-TitledWindow($title, $cmd) {
    $fullCmd = "powershell.exe -NoExit -Command `"`$Host.UI.RawUI.WindowTitle = '$title'; $cmd`""
    $null = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $fullCmd }
}

Start-TitledWindow "SachCart API" "cd '$root\backend'; & '$root\backend\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-TitledWindow "SachCart Worker" "cd '$root\backend'; & '$root\backend\.venv\Scripts\python.exe' -m app.worker"
Start-TitledWindow "SachCart Frontend" "cd '$root\frontend'; npm run dev"

Write-Host "Waiting for http://127.0.0.1:3000/api/health to become healthy..."
$healthy = $false
$timeoutSeconds = 60
$elapsed = 0
while (-not $healthy -and $elapsed -lt $timeoutSeconds) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:3000/api/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
        if ($res.postgres -eq "up" -and $res.redis -eq "up" -and $res.minio -eq "up" -and $res.worker -eq "up") {
            $healthy = $true
        }
    } catch {}
}

if (-not $healthy) {
    Write-Host "Timed out waiting for http://127.0.0.1:3000/api/health to become healthy."
    exit 1
}

Start-Process "http://127.0.0.1:3000"

Write-Host "SachCart started successfully."
Write-Host "Windows:"
Write-Host "  1. [SachCart API]      - FastAPI backend on http://127.0.0.1:8000"
Write-Host "  2. [SachCart Worker]   - Background audit worker"
Write-Host "  3. [SachCart Frontend] - Next.js dev server on http://127.0.0.1:3000"
