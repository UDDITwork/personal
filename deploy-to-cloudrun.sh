#!/bin/bash

# Deploy PATMASTER Extraction to Cloud Run
# This script deploys the latest code with authentication to Cloud Run

set -e

echo "🚀 Deploying PATMASTER Extraction to Cloud Run..."
echo "================================================"

# Configuration
PROJECT_ID="patmaster-extraction-438822"
SERVICE_NAME="patmaster-extraction"
REGION="europe-west1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list 2>&1 | grep -q ACTIVE; then
    echo "❌ Error: Not logged in to gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "📦 Setting project: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

# Build and push Docker image
echo "🔨 Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "LLAMA_CLOUD_API_KEY=${LLAMA_CLOUD_API_KEY}" \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --set-env-vars "TURSO_DATABASE_URL=${TURSO_DATABASE_URL}" \
  --set-env-vars "TURSO_AUTH_TOKEN=${TURSO_AUTH_TOKEN}" \
  --set-env-vars "JWT_SECRET_KEY=${JWT_SECRET_KEY}" \
  --set-env-vars "CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME}" \
  --set-env-vars "CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY}" \
  --set-env-vars "CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET}" \
  --set-env-vars "ENVIRONMENT=production"

echo "✅ Deployment complete!"
echo ""
echo "📋 Service URL:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
echo ""
echo "🔍 Test the auth endpoint:"
echo "curl -X POST \$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')/api/v1/auth/register -H 'Content-Type: application/json' -d '{\"email\":\"test@test.com\",\"password\":\"test123\",\"full_name\":\"Test\"}'"
