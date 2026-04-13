FROM python:3.12-slim
WORKDIR /app

# curl is needed so Coolify's in-container healthcheck can hit /health.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# This line copies everything, INCLUDING the templates folder
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
