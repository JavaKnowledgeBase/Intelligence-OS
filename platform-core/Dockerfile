FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libcairo2-dev \
    pkg-config \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y --purge gcc g++ build-essential python3-dev \
    && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "until alembic upgrade head; do echo 'Waiting for PostgreSQL...'; sleep 2; done && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
