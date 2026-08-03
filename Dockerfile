FROM node:24.18.1-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INTUNE_AUDITOR_DATA_DIR_OVERRIDE=/data
WORKDIR /app
RUN groupadd --gid 10001 auditor && useradd --uid 10001 --gid auditor --create-home auditor
COPY backend/ ./backend/
COPY knowledge-packs/ ./knowledge-packs/
COPY samples/ ./samples/
COPY organization/ ./organization/
COPY README.md LICENSE-NOTICE.md ./
COPY --from=frontend-build /build/frontend/dist ./frontend/dist
RUN python -m pip install --no-cache-dir --editable ./backend && \
    mkdir -p /data && chown -R auditor:auditor /app /data
USER auditor
VOLUME ["/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health', timeout=3).read()"]
CMD ["python", "-m", "uvicorn", "intune_auditor.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8765"]
