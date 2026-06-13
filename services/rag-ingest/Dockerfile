# RAG ingestion job — MySQL document store -> pgvector embeddings
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ingest.py .
# One-shot job: `docker compose run --rm rag-ingest`
CMD ["python", "ingest.py"]
