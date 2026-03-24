# setup_full.ps1
$ErrorActionPreference = "Stop"

Write-Host "== AlphaForge full setup ==" -ForegroundColor Cyan

# 1) Detect Python
$PY = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PY = "py -3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PY = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PY = "python3"
} else {
    Write-Host "Python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python command: $PY"

# 2) Create + activate venv
if (!(Test-Path ".venv")) {
    Invoke-Expression "$PY -m venv .venv"
}
& ".\.venv\Scripts\Activate.ps1"

# 3) Install deps
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4) Ensure Ollama installed
if (!(Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama not found. Trying winget install..." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "winget not found. Install Ollama manually from https://ollama.com/download/windows" -ForegroundColor Red
        exit 1
    }
}

# 5) Start Ollama service (background)
$ollamaRunning = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaRunning) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 6) Pull model(s)
ollama pull phi3
# Optional fallback model:
ollama pull mistral

# 7) Optional .env (only if missing)
if (!(Test-Path ".env")) {
@"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_PRIMARY_MODEL=phi3
OLLAMA_FALLBACK_MODEL=mistral
OLLAMA_TIMEOUT_SECONDS=25
ALPHAFORGE_DB_PATH=data/alphaforge.db
"@ | Set-Content .env -Encoding UTF8
}

# 8) Run app
python app.py