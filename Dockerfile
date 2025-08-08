FROM python:3.12-slim

WORKDIR /app

# Copier tout le dossier app/ y compris main.py, data_preparation.py, query_processor.py...
COPY ./app ./app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
