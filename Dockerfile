FROM python:3.12-slim

# Installer juste ce qu'il faut pour pip + wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier seulement le strict nécessaire
COPY ./app /app
COPY requirements.txt .

# Installer les dépendances (en mode clean)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Exposer le port de l'API
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
