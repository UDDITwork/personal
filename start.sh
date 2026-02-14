#!/bin/bash

# Start script for PATMASTER Extraction Pipeline

echo "Starting PATMASTER Document Extraction Pipeline..."

# Start Redis in background
echo "Starting Redis..."
redis-server --daemonize yes --bind 127.0.0.1 --port 6379

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
until redis-cli ping > /dev/null 2>&1; do
  echo "Redis is unavailable - sleeping"
  sleep 1
done
echo "Redis is ready!"

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=10 \
  --logfile=logs/celery.log \
  --detach

# Wait a moment for Celery to initialize
sleep 2

# Start FastAPI with uvicorn
echo "Starting FastAPI application..."
uvicorn main:app \
  --host 0.0.0.0 \
  --port ${PORT:-8000} \
  --workers ${WORKERS:-4} \
  --log-level info \
  --access-log \
  --timeout-keep-alive 300
