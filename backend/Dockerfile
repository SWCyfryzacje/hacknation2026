# syntax=docker/dockerfile:1
# Oficjalny obraz Pythona na Alpine, wersja przypięta jawnie (bez tagu latest).
ARG PYTHON_IMAGE=python:3.14.9-alpine3.24

# ---------------------------------------------------------------- etap budowania
FROM ${PYTHON_IMAGE} AS build
# Narzędzia kompilacji na wypadek pakietów bez gotowych kół dla musl — nie trafiają do obrazu końcowego.
RUN apk add --no-cache build-base libxml2-dev libxslt-dev jpeg-dev zlib-dev
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /src
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# ---------------------------------------------------------------- obraz uruchomieniowy
FROM ${PYTHON_IMAGE} AS runtime
# LibreOffice jest potrzebny tylko do starego formatu .doc; można go pominąć: --build-arg WITH_LIBREOFFICE=false
ARG WITH_LIBREOFFICE=true
RUN apk add --no-cache libxml2 libxslt libjpeg zlib tesseract-ocr tesseract-ocr-data-pol \
 && if [ "$WITH_LIBREOFFICE" = "true" ]; then apk add --no-cache libreoffice-writer font-dejavu; fi \
 && addgroup -S app && adduser -S -D -G app -h /home/app app

COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app \
    TMPDIR=/tmp

WORKDIR /home/app
# Proces aplikacji działa na dedykowanym użytkowniku bez uprawnień administratora.
USER app
# 8000 — REST API
EXPOSE 8000 8100
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1
# Sekrety (JWT_SECRET, EDENAI_API_KEY) wyłącznie ze zmiennych środowiskowych przy uruchomieniu kontenera.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header"]
