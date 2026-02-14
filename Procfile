web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4
worker: celery -A workers.celery_app worker --loglevel=info --concurrency=10
