FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY version.json /app/version.json
COPY backend/ /app/
RUN rm -rf /app/.venv /app/tests /app/data && mkdir -p /app/data

EXPOSE 8071

CMD ["python", "main.py"]
