FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code (includes the trained model in src/models/) and the DuckDB/CSV data
COPY src/ ./src/
COPY data/ ./data/

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# The API by default. compose.yaml runs the Celery worker from the same image
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
