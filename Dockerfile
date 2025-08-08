FROM python:3.12-slim

WORKDIR /app

COPY ./app ./app
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
