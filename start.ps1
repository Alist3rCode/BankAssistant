# ============================================================
#  BankAssistant — Script de démarrage local (Windows)
#  Exécuter depuis la racine du projet :
#    powershell -ExecutionPolicy Bypass -File .\start.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "    [X]  $msg" -ForegroundColor Red }

# ── 1. Vérifier Python ────────────────────────────────────────────────────
Write-Step "Vérification de Python..."
try {
    $pyver = python --version 2>&1
    Write-OK $pyver
} catch {
    Write-Fail "Python introuvable. Installez Python 3.10+ depuis https://www.python.org/downloads/"
    exit 1
}

# ── 2. Vérifier Node.js ───────────────────────────────────────────────────
Write-Step "Vérification de Node.js..."
try {
    $nodever = node --version 2>&1
    Write-OK "Node.js $nodever"
} catch {
    Write-Fail "Node.js introuvable. Installez Node.js 18+ depuis https://nodejs.org/"
    exit 1
}

# ── 3. Créer .env si absent ───────────────────────────────────────────────
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Step "Création du fichier .env (première utilisation)..."

    $encKey = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>$null
    if (-not $encKey) {
        # cryptography pas encore installé — on génère une clé temporaire
        $encKey = "CHANGER_MOI_" + [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString("N") + [System.Guid]::NewGuid().ToString("N"))).Substring(0, 32)
    }
    $jwtKey = -join ((1..64) | ForEach-Object { [char](Get-Random -Min 97 -Max 123) })

    $envContent = @"
# Généré automatiquement par start.ps1 — NE PAS COMMITTER
DB_PATH=./data/bankassistant.db
ENCRYPTION_KEY=$encKey
SECRET_KEY=$jwtKey
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15
WOOB_DATA_DIR=./woob-data
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=
MISTRAL_API_KEY=
OLLAMA_BASE_URL=
NTFY_URL=http://localhost:80
NTFY_TOPIC=bankassistant
NTFY_TOKEN=
APP_URL=http://localhost:8000
LOG_LEVEL=INFO
DEBUG=false
"@
    $envContent | Out-File -FilePath $envFile -Encoding utf8
    Write-OK ".env créé avec des clés générées automatiquement"
    Write-Warn "Vous pourrez saisir votre clé Groq depuis l'interface (Paramètres → IA)"
} else {
    Write-OK ".env existant trouvé"
}

# ── 4. Régénérer ENCRYPTION_KEY proprement (si pas encore fait) ───────────
# (La clé temporaire ci-dessus peut être courte si cryptography n'était pas dispo)
# On remet à jour après l'install pip
$needKeyRegen = (Get-Content $envFile | Select-String "CHANGER_MOI").Count -gt 0

# ── 5. Créer les répertoires nécessaires ──────────────────────────────────
Write-Step "Création des répertoires..."
$dirs = @("data", "woob-data")
foreach ($d in $dirs) {
    $path = Join-Path $ProjectRoot $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-OK "Créé : $d/"
    }
}

# ── 6. Environnement virtuel Python ───────────────────────────────────────
Write-Step "Configuration de l'environnement Python..."
$venvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "    Création du venv..."
    python -m venv $venvPath
    Write-OK "Venv créé"
}

$pip    = Join-Path $venvPath "Scripts\pip.exe"
$python = Join-Path $venvPath "Scripts\python.exe"

# ── 7. Installer les dépendances Python ───────────────────────────────────
Write-Step "Installation des dépendances Python..."
$reqFile = Join-Path $ProjectRoot "backend\requirements.txt"

# Installer sans woob d'abord (plus rapide, woob optionnel)
Write-Host "    Installation des dépendances principales..."
& $pip install -r $reqFile --quiet --no-warn-script-location 2>&1 | Where-Object { $_ -match "ERROR|error" } | ForEach-Object { Write-Warn $_ }

# Tenter woob séparément (peut échouer sur Windows sans build tools)
Write-Host "    Tentative d'installation de woob (optionnel)..."
try {
    & $pip install woob --quiet --no-warn-script-location 2>&1 | Out-Null
    Write-OK "woob installé — scraping automatique disponible"
} catch {
    Write-Warn "woob non installé (normal sur Windows sans Visual C++ Build Tools)"
    Write-Warn "Le scraping automatique sera désactivé. Utilisez l'import CSV/OFX."
}

# Régénérer la clé Fernet proprement si nécessaire
if ($needKeyRegen) {
    $properKey = & $python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $envContent = Get-Content $envFile -Raw
    $envContent = $envContent -replace "ENCRYPTION_KEY=.*", "ENCRYPTION_KEY=$properKey"
    $envContent | Out-File -FilePath $envFile -Encoding utf8 -NoNewline
    Write-OK "Clé de chiffrement Fernet régénérée correctement"
}

Write-OK "Dépendances Python installées"

# ── 8. Build du frontend Vue.js ───────────────────────────────────────────
$frontendDist = Join-Path $ProjectRoot "frontend\dist"
$rebuildFrontend = $false

if (-not (Test-Path $frontendDist)) {
    $rebuildFrontend = $true
    Write-Step "Build du frontend Vue.js (première fois ~1-2 min)..."
} else {
    # Vérifier si des sources ont changé depuis le dernier build
    $srcFiles = Get-ChildItem (Join-Path $ProjectRoot "frontend\src") -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $distFiles = Get-ChildItem $frontendDist -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($srcFiles -and $distFiles -and $srcFiles.LastWriteTime -gt $distFiles.LastWriteTime) {
        $rebuildFrontend = $true
        Write-Step "Sources modifiées — rebuild du frontend..."
    } else {
        Write-Step "Frontend déjà buildé"
        Write-OK "Utilisation du build existant"
    }
}

if ($rebuildFrontend) {
    Push-Location (Join-Path $ProjectRoot "frontend")
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Host "    npm install..."
            npm install --silent 2>&1 | Out-Null
        }
        Write-Host "    npm run build..."
        npm run build 2>&1 | Tee-Object -Variable buildOutput | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "Build frontend échoué :"
            $buildOutput | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" }
            exit 1
        }
        Write-OK "Frontend buildé avec succès"
    } finally {
        Pop-Location
    }
}

# ── 9. Migrations Alembic ─────────────────────────────────────────────────
Write-Step "Application des migrations de base de données..."
Push-Location (Join-Path $ProjectRoot "backend")
try {
    & $python -m alembic upgrade head 2>&1 | ForEach-Object { Write-Host "    $_" }
    Write-OK "Base de données prête"
} catch {
    Write-Warn "Erreur migration (si première fois c'est normal, le démarrage s'en chargera)"
} finally {
    Pop-Location
}

# ── 10. Lancement ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  BankAssistant est prêt !" -ForegroundColor Green
Write-Host "  Ouvrez votre navigateur : http://localhost:8000" -ForegroundColor Green
Write-Host "  Arrêt : Ctrl+C" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Push-Location (Join-Path $ProjectRoot "backend")
try {
    & $python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
} finally {
    Pop-Location
}
