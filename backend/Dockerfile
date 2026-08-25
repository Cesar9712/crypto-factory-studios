FROM python:3.13-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV CFS_ENV=production CFS_ANTIVIRUS_REQUIRED=false PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD sh -c 'curl -fsS http://127.0.0.1:${PORT:-8000}/health || exit 1'
CMD ["sh","-c","uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
