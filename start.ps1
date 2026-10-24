$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

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
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    exit 1
}
Pop-Location

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; & '$root\backend\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; & '$root\backend\.venv\Scripts\python.exe' -m app.worker"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"
