FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends clamav && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV CFS_ENV=production CFS_ANTIVIRUS_REQUIRED=true
CMD ["uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"]
