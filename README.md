# 🏦 BankAssistant

Assistant bancaire IA self-hosted connecté au **Crédit Agricole**. Scraping automatique des transactions, analyse financière par IA, budgets style enveloppes, notifications push Android — entièrement déployé via Docker sur votre serveur personnel.

---

## ✨ Fonctionnalités

| Domaine | Fonctionnalités |
|---|---|
| **Données** | Scraping automatique CA (woob), import CSV/OFX fallback, déduplication |
| **Analyse** | Dashboard soldes + dépenses, graphiques ECharts, export CSV |
| **IA** | Chat bancaire (Groq/Mistral/Ollama), prévisions fin de mois, suggestions budget |
| **Budgets** | Enveloppes style YNAB, assignation partielle de transactions, multi-budgets |
| **Catégories** | 17 catégories système + personnalisées, règles de catégorisation auto (regex/contains/…) |
| **Sécurité** | 2FA TOTP (Authy/Google Auth), JWT, rate limiting, chiffrement Fernet, audit log |
| **Notifications** | Push Android via ntfy self-hosted (budget dépassé, rapport journalier) |
| **Mobile** | PWA installable sur Android (plein écran, icône bureau) |
| **Config** | Tout paramétrable depuis l'IHM — aucun fichier à modifier après déploiement |

---

## 🏗️ Architecture

```
Internet / réseau local
        │
   ┌────▼────┐
   │  Caddy  │  HTTPS + reverse proxy
   └────┬────┘
        │
   ┌────▼────┐    ┌─────────────┐
   │Frontend │    │   Backend   │  FastAPI + woob + APScheduler
   │ Vue.js  │◄──►│   FastAPI   │
   │  (PWA)  │    └──────┬──────┘
   └─────────┘           │
                    ┌─────▼──────┐
                    │  SQLite    │  WAL mode, chiffrement Fernet
                    └────────────┘
        │
   ┌────▼────┐
   │  ntfy   │  Push notifications Android
   └─────────┘
```

**Stack :** FastAPI · SQLAlchemy · Alembic · woob/cragr · LiteLLM · Vue.js 3 · Naive UI · ECharts · Pinia · Caddy · ntfy

---

## 🚀 Démarrage rapide

### Option A — Sans Docker (recommandé pour tester en local)

**Prérequis :** [Python 3.10+](https://www.python.org/downloads/) · [Node.js 18+](https://nodejs.org/)

```powershell
# Cloner le projet
git clone https://github.com/Alist3rCode/BankAssistant.git
cd BankAssistant

# Lancer (première fois : installe tout automatiquement ~3 min)
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Ou double-cliquer sur **`start.bat`**.

Le script fait tout automatiquement :
- Crée le `.env` avec des clés générées
- Crée le venv Python et installe les dépendances
- Builde le frontend Vue.js
- Applique les migrations de base de données
- Lance le serveur sur **[http://localhost:8000](http://localhost:8000)**

> Au prochain démarrage, il suffit de relancer `start.ps1` — tout est déjà installé, ça prend 5 secondes.

---

### Option B — Avec Docker

**Prérequis :** [Docker](https://docs.docker.com/engine/install/) + [Docker Compose](https://docs.docker.com/compose/install/) (v2)

```bash
git clone https://github.com/Alist3rCode/BankAssistant.git
cd BankAssistant
cp .env.example .env
# Générer et remplir ENCRYPTION_KEY et SECRET_KEY dans .env (voir .env.example)
docker compose up -d --build
```

Accès : **[https://localhost](https://localhost)** (certificat auto-signé → accepter l'avertissement).

---

### Créer votre compte

Lors de la première visite, l'interface propose de créer le compte administrateur (email + mot de passe). Un seul compte est supporté (mono-utilisateur).

---

## ⚙️ Configuration depuis l'IHM

Tout se configure depuis **Paramètres** dans l'application :

### Onglet Crédit Agricole
1. Choisir votre caisse régionale
2. Saisir votre numéro de compte et code confidentiel (chiffrés à la sauvegarde)
3. Cliquer **Tester la connexion**
4. Activer le scraping automatique (heure paramétrable)

### Onglet IA
1. Choisir le provider : **Groq** (recommandé, gratuit) / Mistral / Ollama
2. Saisir votre clé API Groq — obtenir sur [console.groq.com](https://console.groq.com) (gratuit, sans carte)
3. Choisir le modèle (défaut : `llama-3.3-70b-versatile`)

### Onglet Notifications
1. Installer l'app [ntfy](https://ntfy.sh) sur Android (F-Droid ou Play Store)
2. S'abonner au topic `bankassistant` dans l'app
3. Renseigner l'URL ntfy et activer les alertes souhaitées

### Onglet Sécurité
Activer la double authentification TOTP (Authy, Google Authenticator, Bitwarden…)

---

## 📱 Installation Android (PWA)

1. Ouvrir l'application dans **Chrome Android**
2. Menu ⋮ → **Ajouter à l'écran d'accueil**
3. L'app s'installe comme une application native (plein écran, icône bureau)

---

## 🔧 Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f backend

# Redémarrer après modification de .env
docker compose restart backend

# Arrêter tous les services
docker compose down

# Mise à jour (pull + rebuild)
git pull && docker compose up -d --build
```

---

## 🔒 Sécurité

| Mécanisme | Détail |
|---|---|
| **Chiffrement** | Identifiants CA + clés API chiffrés en base (Fernet AES-128) |
| **Authentification** | bcrypt + JWT (access 60min + refresh 30j) + TOTP 2FA |
| **Rate limiting** | 10 req/min sur login, 5/heure sur register (slowapi) |
| **Verrouillage** | Compte verrouillé 15 min après 5 tentatives échouées |
| **Audit** | Toutes les connexions et actions sensibles loguées |
| **HTTPS** | Obligatoire via Caddy (cert auto-signé en local) |
| **CORS** | Restreint à l'URL de l'application |
| **PIN CA** | Jamais stocké en clair — chiffré en mémoire, supprimé après scraping |

---

## 📁 Structure du projet

```
BankAssistant/
├── docker-compose.yml
├── Caddyfile                    # Reverse proxy HTTPS
├── .env.example                 # Template de configuration
│
├── backend/
│   ├── main.py                  # FastAPI app + lifespan
│   ├── models/models.py         # SQLAlchemy ORM
│   ├── migrations/              # Alembic (appliqué auto au démarrage)
│   ├── routers/                 # Endpoints REST
│   │   ├── auth.py              # Login, 2FA, refresh, password
│   │   ├── accounts.py          # Comptes bancaires
│   │   ├── transactions.py      # Transactions + filtres
│   │   ├── budgets.py           # Enveloppes budgétaires
│   │   ├── categories.py        # Catégories
│   │   ├── category_rules.py    # Règles de catégorisation auto
│   │   ├── ai.py                # Chat, prévisions, suggestions
│   │   ├── export.py            # Export CSV
│   │   ├── scraper.py           # Scraping + import CSV/OFX
│   │   ├── settings.py          # Paramètres (clé-valeur chiffrable)
│   │   ├── notifications.py     # Test ntfy
│   │   └── audit.py             # Journal d'audit
│   ├── services/
│   │   ├── sync_service.py      # Orchestration scraping
│   │   ├── categorization_service.py  # Moteur de règles
│   │   └── notification_service.py    # ntfy HTTP client
│   └── scraper/
│       ├── ca_scraper.py        # woob/cragr wrapper
│       ├── ca_regions.py        # 37 caisses régionales CA
│       └── csv_import.py        # Import CSV/OFX
│
└── frontend/
    └── src/
        ├── views/               # Pages Vue.js
        │   ├── DashboardView.vue
        │   ├── TransactionsView.vue
        │   ├── BudgetsView.vue
        │   ├── ChatView.vue
        │   ├── SettingsView.vue
        │   └── SecurityView.vue
        ├── stores/              # Pinia state management
        └── api/                 # Clients Axios typés
```

---

## ⚠️ Avertissements

- **Légalité** : le scraping CA via woob est en zone grise des CGU. Usage strictement personnel.
- **Données** : vos identifiants et transactions restent sur votre serveur. Aucune donnée n'est envoyée à des tiers sauf les requêtes IA (Groq/Mistral si activé).
- **woob** : le module `cragr` peut se casser après une mise à jour du site CA. Solution : importer manuellement un CSV depuis le site CA.
- **Clés** : si vous perdez `ENCRYPTION_KEY`, les identifiants CA et clés API stockés en base seront illisibles (à resaisir depuis l'IHM).

---

## 📄 Licence

Usage personnel uniquement.
