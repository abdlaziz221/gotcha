# Image de production : Serverless Datacloud (Docker accepté) ou VPS à Dakar.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    GOTCHA_ENV=prod

WORKDIR /srv

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY content ./content
COPY fixtures ./fixtures
COPY migrations ./migrations
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 gotcha
USER gotcha

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
