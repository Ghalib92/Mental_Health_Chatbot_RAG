# syntax=docker/dockerfile:1
#
# NOTE: the chatbot RAG dependencies (torch via sentence-transformers) make this
# image large. The Django API boots and serves without them; the chat endpoint
# reports 503 until they are installed and the API keys/index are configured.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --system --gid 1000 django && \
    adduser --system --uid 1000 --gid 1000 django

WORKDIR /app

# setup.py + src are needed for the editable `-e .` install.
COPY requirements.txt setup.py ./
COPY src ./src
RUN pip install -r requirements.txt

COPY --chown=django:django . .

RUN mkdir -p /app/Mental_Chatbot/staticfiles && chown -R django:django /app

USER django
WORKDIR /app/Mental_Chatbot

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "Mental_Chatbot.wsgi:application"]
