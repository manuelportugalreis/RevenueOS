FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
COPY data/dashboard/ /build/data/dashboard/
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-build-isolation --no-deps .
COPY migrations/ migrations/
COPY alembic.ini ./
COPY data/dashboard/ data/dashboard/
COPY --from=frontend /build/frontend/dist/ frontend/dist/
RUN useradd --uid 10001 --create-home revenueos
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,urllib.request,urllib.parse; r=urllib.request.Request('http://127.0.0.1:8000/health/live',headers={'Host':urllib.parse.urlparse(os.environ['REVENUEOS_ORIGIN']).netloc}); urllib.request.urlopen(r)"
CMD ["uvicorn", "revenueos.web:application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
