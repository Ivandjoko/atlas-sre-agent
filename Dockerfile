# --- Étape 1 : construction (outils de build, pas copiés dans l'image finale)
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app
# Les dépendances d'abord : cette couche reste en cache tant qu'elles ne changent pas
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY main.py ./

# --- Étape 2 : exécution (image minimale)
FROM python:3.12-slim
RUN useradd --create-home --uid 10001 atlas
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/main.py ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
