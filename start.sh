#!/bin/bash
# Start script for PATMASTER Extraction Pipeline
echo "Starting PATMASTER Document Extraction Pipeline..."

# Start FastAPI with uvicorn on the Cloud Run PORT
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port ${PORT:-8080} \
  --workers 1 \
  --log-level info \
  --access-log \
  --timeout-keep-alive 300
