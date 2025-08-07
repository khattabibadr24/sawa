FROM python:3.12-slim-bullseye

# Mise à jour des paquets
RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copie des dépendances et installation
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip show uvicorn \
    && pip install --no-cache-dir pip-audit \
    && pip-audit || true

# Copie du code de l’application
COPY ./app ./app

# Création de l'utilisateur non-root
RUN useradd -m appuser
USER appuser

# Expose le port de l'API
EXPOSE 8000

# Commande de démarrage
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
