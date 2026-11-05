# Pinned to the python:3.12-slim image index as published on 2026-11-02.
FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# shortcut: Debian packages come from the current archive, pin them through a snapshot source once Docker can test it.
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

# requirements.txt names constraints/windows-py312.txt; its win32 markers keep those pins inactive here.
COPY requirements.txt /app/
COPY constraints/ /app/constraints/
RUN python -m pip install pip==26.2.2 \
    && python -m pip install -r /app/requirements.txt -c /app/constraints/linux-py312.txt

COPY . /app

# Compose mounts its named volumes on these folders; a new volume takes its owner from them.
RUN mkdir -p /app/artifacts /app/media /app/staticfiles /app/ml_models \
    && useradd --uid 10001 --create-home alfred \
    && chown -R alfred:alfred /app/artifacts /app/media /app/staticfiles /app/ml_models

USER alfred

EXPOSE 8000

CMD ["gunicorn", "alfred_ai.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
