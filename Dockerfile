FROM python:3.12-slim-bullseye

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ✅ Corrigé ici : on copie le contenu du dossier app/ dans /app
COPY ./app ./

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
