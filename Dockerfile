# Utilise l'image officielle Python 3.12
FROM python:3.12

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie les dépendances et installe-les
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copie le code source dans le conteneur
COPY ./app ./app

# Expose le port FastAPI
EXPOSE 8000

# Lance FastAPI via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
