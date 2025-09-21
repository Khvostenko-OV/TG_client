FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app/log/gunicorn
WORKDIR /app

RUN apt-get update -y && \
    apt-get install -y postgresql-client libpq-dev gettext && \
    apt-get install --no-install-recommends -y gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

ARG ENVIRONMENT
RUN pip install -r /app/requirements.txt

COPY . /app