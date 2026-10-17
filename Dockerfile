# Image de base minimale et épinglée (réduit la surface d'attaque)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Exécution en utilisateur non privilégié
RUN useradd --system --uid 10001 --no-create-home appuser
USER 10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app.main:app"]
