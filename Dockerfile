FROM python:3.13.15-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/overlays \
    GIVEAWAY_CONFIG_FILE=/var/lib/overlays/settings.json

RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home \
        --home-dir /var/lib/overlays overlays \
    && mkdir -p /var/lib/overlays \
    && chown overlays:overlays /var/lib/overlays

WORKDIR /opt/overlays
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

USER overlays:overlays
WORKDIR /var/lib/overlays
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
