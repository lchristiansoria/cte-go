FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY migrations ./migrations

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic -c migrations/alembic.ini upgrade head && ctg-go-seed && uvicorn ctg_go.main:app --host 0.0.0.0 --port 8000"]
