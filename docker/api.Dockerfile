FROM python:3.11-slim
RUN apt-get update && apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 git && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg[binary]
COPY backend/ /app/backend/
COPY config/ /app/config/
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
