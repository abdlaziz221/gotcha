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
# Date de construction : une image plus ancienne qui redémarre ne recharge pas son contenu.
RUN date -u +%s > BUILD_TIME

RUN useradd --create-home --uid 10001 gotcha
USER gotcha

EXPOSE 8000
# Avant le site : schéma à jour et contenu de l'image chargé en base (scripts/release.py).
# --no-proxy-headers : l'adresse du visiteur est lue par l'application, selon le nombre de
# proxys de confiance (GOTCHA_PROXY_HOPS), jamais en croyant n'importe quel X-Forwarded-For.
# Le protocole d'origine (X-Forwarded-Proto) suit la même règle : app/security/proxy.py.
CMD ["sh", "-c", "python scripts/release.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-proxy-headers"]
