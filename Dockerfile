FROM python:3.12-slim

# Crée le répertoire de travail
WORKDIR /app

# Copier le dossier app dans /app/app
COPY ./app ./app

# Copier les dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Exposer le port
EXPOSE 8000

# Lancer uvicorn en pointant vers app.main
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
