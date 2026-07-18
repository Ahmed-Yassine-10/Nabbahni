# ---- SentinelleRx ML training/scoring image ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY ml/pyproject.toml ml/pyproject.toml
RUN pip install --no-cache-dir -e ml
# Backend package is imported for shared models/settings.
COPY backend backend
COPY ml ml
ENV PYTHONPATH=/workspace/backend:/workspace/ml
CMD ["python", "-m", "ml.score"]
