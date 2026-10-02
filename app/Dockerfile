# Briefato — portal image. Build context is the repo root:
#   docker build -f app/Dockerfile -t briefato:latest /mnt/fast/docker/briefato
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/briefato

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt /srv/briefato/app/requirements.txt
RUN pip install --no-cache-dir -r /srv/briefato/app/requirements.txt

# Same relative layout as the dev tree, so config.landing_dir resolves.
COPY app /srv/briefato/app
COPY landing /srv/briefato/landing

RUN useradd --system --uid 10001 --home /srv/briefato briefato \
 && mkdir -p /data && chown -R briefato:briefato /data /srv/briefato

USER briefato
EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=4)"

CMD ["uvicorn", "briefato.main:app", "--app-dir", "/srv/briefato/app", "--host", "0.0.0.0", "--port", "8080"]
