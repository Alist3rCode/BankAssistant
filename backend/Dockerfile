FROM python:3.12-slim

WORKDIR /app

# Dépendances système pour woob et cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pré-télécharger les modules woob (dont cragr pour Crédit Agricole)
RUN woob update || true

COPY . .

# Répertoire pour les données persistantes (monté en volume)
RUN mkdir -p /app/data /app/woob-data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
