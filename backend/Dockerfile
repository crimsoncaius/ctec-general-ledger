FROM python:3.12.5-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir .

USER app
EXPOSE 8000
CMD ["sh", "-c", "if [ \"${SERVICE_ROLE:-api}\" = \"worker\" ]; then exec python -m app.worker; else alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\"; fi"]
