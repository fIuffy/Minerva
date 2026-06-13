# Tier 2 — State citizen portal (public edge, pivot bridge)
FROM python:3.12-slim

WORKDIR /app

# psycopg[binary] and PyMySQL are pure-wheel; no system build deps needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Landing zone for uploaded documents (the poisoning vector input).
RUN mkdir -p /app/uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
