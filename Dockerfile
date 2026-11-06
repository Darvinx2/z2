# syntax=docker/dockerfile:1

# --- Стадия 1: сборка зависимостей и колеса приложения -----------------------
FROM python:3.13-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir build==1.3.0

COPY requirements.txt pyproject.toml ./
COPY app ./app

# зависимости ставятся в отдельный префикс, который копируется в финальный образ
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && python -m build --wheel --outdir /dist \
    && pip install --no-cache-dir --prefix=/install --no-deps /dist/*.whl

# --- Стадия 2: минимальный рантайм -------------------------------------------
FROM python:3.13-slim AS runtime

# непривилегированный пользователь: приложение не должно работать от root
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser alembic.ini ./alembic.ini

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STORAGE_ROOT=/data

RUN mkdir -p /data && chown appuser:appuser /data

USER appuser
VOLUME ["/data"]
EXPOSE 8080

CMD ["python", "-m", "app.main"]
