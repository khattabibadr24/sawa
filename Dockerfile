FROM python:3.12-slim-bullseye

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 👇 Cette ligne copie ton dossier `app` dans /app/app
COPY ./app ./app

EXPOSE 8000

# 👇 Lancement de FastAPI depuis le bon chemin
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
