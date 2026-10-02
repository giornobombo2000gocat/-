FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY engine ./engine
COPY backend/app ./backend/app
COPY backend/__init__.py ./backend/__init__.py
RUN python -m pip install --no-cache-dir '.[api]' \
    && useradd --create-home --uid 10001 scopa

USER scopa
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
