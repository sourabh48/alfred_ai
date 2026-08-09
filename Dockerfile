FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        g++ \
        gcc \
        libpq-dev \
        portaudio19-dev \
        postgresql-client \
        redis-tools \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/artifacts /app/media /app/staticfiles

EXPOSE 8000

CMD ["gunicorn", "alfred_ai.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
