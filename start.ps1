# ============================================================
#  BankAssistant - Script de demarrage local (Windows)
#  Executer depuis la racine du projet :
#    powershell -ExecutionPolicy Bypass -File .\start.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Write-Step($msg) { Write-Host "" ; Write-Host ">>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "    [X]  $msg" -ForegroundColor Red }

# ── 1. Verifier Python ──────────────────────────────────────────────────
Write-Step "Verification de Python..."
try {
    $pyver = python --version 2>&1
    Write-OK $pyver
} catch {
    Write-Fail "Python introuvable. Installez Python 3.10+ depuis https://www.python.org/downloads/"
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# ── 2. Verifier Node.js ─────────────────────────────────────────────────
Write-Step "Verification de Node.js..."
try {
    $nodever = node --version 2>&1
    Write-OK "Node.js $nodever"
} catch {
    Write-Fail "Node.js introuvable. Installez Node.js 18+ depuis https://nodejs.org/"
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# ── 3. Creer les repertoires necessaires ────────────────────────────────
Write-Step "Creation des repertoires..."
foreach ($d in @("data", "woob-data")) {
    $path = Join-Path $ProjectRoot $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-OK "Cree : $d/"
    }
}

# ── 4. Environnement virtuel Python ─────────────────────────────────────
# Le venv est cree HORS OneDrive pour eviter les conflits de synchronisation
Write-Step "Configuration de l'environnement Python..."
$venvPath = Join-Path $env:USERPROFILE ".bankassistant_venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "    Creation du venv dans $venvPath ..."
    python -m venv $venvPath
    Write-OK "Venv cree"
} else {
    Write-OK "Venv existant : $venvPath"
}

$python = Join-Path $venvPath "Scripts\python.exe"

# ── 5. Installer les dependances Python ─────────────────────────────────
Write-Step "Installation des dependances Python..."
$reqFile = Join-Path $ProjectRoot "backend\requirements.txt"
Write-Host "    pip install -r requirements.txt..."
Write-Host "    (premiere installation : 3-10 min selon votre connexion et Python version)"
Write-Host ""
& $python -m pip install -r $reqFile --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Erreur lors de l'installation des dependances."
    Write-Warn "Si vous utilisez Python 3.14, certains packages peuvent ne pas etre compatibles."
    Write-Warn "Essayez avec Python 3.11 ou 3.12 depuis https://www.python.org/downloads/"
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}
Write-OK "Dependances installees"

# Tenter woob separement (optionnel, peut echouer sur Windows)
Write-Host ""
Write-Host "    Tentative d'installation de woob (optionnel, peut echouer sur Windows)..."
$prevEA = $ErrorActionPreference ; $ErrorActionPreference = 'SilentlyContinue'
& $python -m pip install woob --no-warn-script-location *>$null
$woobExit = $LASTEXITCODE ; $ErrorActionPreference = $prevEA
if ($woobExit -eq 0) {
    Write-OK "woob installe - scraping automatique disponible"
} else {
    Write-Warn "woob non installe (optionnel - utilisez l'import CSV/OFX depuis l'interface)"
}

# ── 6. Creer .env si absent ─────────────────────────────────────────────
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Step "Creation du fichier .env (premiere utilisation)..."

    $encKey    = & $python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $jwtKey    = & $python -c "import secrets; print(secrets.token_hex(32))"
    $adminPwd  = & $python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#') for _ in range(16)))"
    $adminEmail = "admin@bankassistant.local"

    $lines = @(
        "# Genere automatiquement par start.ps1 - NE PAS COMMITTER",
        "DB_PATH=./data/bankassistant.db",
        "ENCRYPTION_KEY=$encKey",
        "SECRET_KEY=$jwtKey",
        "ADMIN_EMAIL=$adminEmail",
        "ADMIN_PASSWORD=$adminPwd",
        "JWT_ALGORITHM=HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES=60",
        "REFRESH_TOKEN_EXPIRE_DAYS=30",
        "MAX_LOGIN_ATTEMPTS=5",
        "LOCKOUT_DURATION_MINUTES=15",
        "WOOB_DATA_DIR=./woob-data",
        "DEFAULT_LLM_PROVIDER=groq",
        "DEFAULT_LLM_MODEL=llama-3.3-70b-versatile",
        "GROQ_API_KEY=",
        "MISTRAL_API_KEY=",
        "OLLAMA_BASE_URL=",
        "NTFY_URL=http://localhost:80",
        "NTFY_TOPIC=bankassistant",
        "NTFY_TOKEN=",
        "APP_URL=http://localhost:8000",
        "LOG_LEVEL=INFO",
        "DEBUG=false"
    )
    $lines | Out-File -FilePath $envFile -Encoding utf8
    Write-OK ".env cree avec des cles generees automatiquement"
    Write-Host ""
    Write-Host "    ============================================" -ForegroundColor Yellow
    Write-Host "    IDENTIFIANTS DE CONNEXION (premiere fois) :" -ForegroundColor Yellow
    Write-Host "      Email    : $adminEmail"                    -ForegroundColor White
    Write-Host "      Password : $adminPwd"                     -ForegroundColor White
    Write-Host "    Notez-les ! Modifiables dans Parametres."   -ForegroundColor Yellow
    Write-Host "    ============================================" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-OK ".env existant trouve"
}

# ── 7. Build du frontend Vue.js ─────────────────────────────────────────
$frontendDist = Join-Path $ProjectRoot "frontend\dist"
$needBuild = $false

if (-not (Test-Path $frontendDist)) {
    $needBuild = $true
    Write-Step "Build du frontend Vue.js (premiere fois ~1-2 min)..."
} else {
    $srcDir  = Join-Path $ProjectRoot "frontend\src"
    $srcLast = (Get-ChildItem $srcDir -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    $dstLast = (Get-ChildItem $frontendDist -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    if ($srcLast -gt $dstLast) {
        $needBuild = $true
        Write-Step "Sources modifiees - rebuild du frontend..."
    } else {
        Write-Step "Frontend a jour"
        Write-OK "Utilisation du build existant"
    }
}

if ($needBuild) {
    $frontendDir = Join-Path $ProjectRoot "frontend"
    Push-Location $frontendDir
    try {
        $nodeModules = Join-Path $frontendDir "node_modules"
        if (-not (Test-Path $nodeModules)) {
            Write-Host "    npm install..."
            $prevEA = $ErrorActionPreference ; $ErrorActionPreference = 'SilentlyContinue'
            npm install --silent *>$null
            $ErrorActionPreference = $prevEA
        }
        Write-Host "    npm run build..."
        $prevEA = $ErrorActionPreference ; $ErrorActionPreference = 'SilentlyContinue'
        npm run build *>$null
        $ErrorActionPreference = $prevEA
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "Build frontend echoue. Lancez 'npm run build' dans le dossier frontend/ pour voir les erreurs."
            Pop-Location
            Read-Host "Appuyez sur Entree pour quitter"
            exit 1
        }
        Write-OK "Frontend build avec succes"
    } finally {
        Pop-Location
    }
}

# ── 8. Migrations Alembic ───────────────────────────────────────────────
Write-Step "Verification de la base de donnees..."
Push-Location (Join-Path $ProjectRoot "backend")
try {
    $prevEA = $ErrorActionPreference ; $ErrorActionPreference = 'SilentlyContinue'
    & $python -m alembic upgrade head *>$null
    $alembicExit = $LASTEXITCODE ; $ErrorActionPreference = $prevEA
    if ($alembicExit -eq 0) { Write-OK "Base de donnees prete" } else { throw "alembic exit $alembicExit" }
} catch {
    Write-Warn "Migration ignoree (sera appliquee au demarrage)"
} finally {
    Pop-Location
}

# ── 9. Lancement ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  BankAssistant est pret !" -ForegroundColor Green
Write-Host "  Ouvrez votre navigateur : http://localhost:8000" -ForegroundColor Green
Write-Host "  Arret : Ctrl+C" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Push-Location (Join-Path $ProjectRoot "backend")
& $python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Pop-Location
