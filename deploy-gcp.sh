#!/bin/bash

# PATMASTER Document Extraction - Google Cloud Deployment Script
# This script deploys both backend (Cloud Run) and frontend (Firebase)

set -e  # Exit on error

echo "======================================================================"
echo "  PATMASTER Document Extraction - Google Cloud Deployment"
echo "======================================================================"

# Configuration
PROJECT_ID="patmaster-extraction"
REGION="us-central1"
SERVICE_NAME="patmaster-extraction-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Check if user is logged in
echo "Checking authentication..."
ACCOUNT=$(gcloud config get-value account)
if [ -z "$ACCOUNT" ]; then
    echo "Error: Not logged in to Google Cloud"
    echo "Please run: gcloud auth login"
    exit 1
fi
echo "✓ Logged in as: $ACCOUNT"

# Create project if it doesn't exist
echo ""
echo "Setting up GCP project..."
if gcloud projects describe $PROJECT_ID &>/dev/null; then
    echo "✓ Project '$PROJECT_ID' already exists"
else
    echo "Creating new project '$PROJECT_ID'..."
    gcloud projects create $PROJECT_ID --name="PATMASTER Extraction"
    echo "✓ Project created"
fi

# Set active project
gcloud config set project $PROJECT_ID
echo "✓ Active project: $PROJECT_ID"

# Enable required APIs
echo ""
echo "Enabling required APIs (this may take a few minutes)..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firebase.googleapis.com
echo "✓ APIs enabled"

# Check if .env file exists
if [ ! -f .env ]; then
    echo ""
    echo "Error: .env file not found!"
    echo "Please create .env file with your API keys:"
    echo "  cp .env.example .env"
    echo "  # Edit .env and add your LLAMA_CLOUD_API_KEY and GEMINI_API_KEY"
    exit 1
fi

# Load environment variables
source .env

if [ -z "$LLAMA_CLOUD_API_KEY" ] || [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: API keys not set in .env file"
    exit 1
fi
echo "✓ API keys loaded from .env"

# Create Redis instance (if not exists)
echo ""
echo "Setting up Redis instance..."
REDIS_INSTANCE="patmaster-redis"
if gcloud redis instances describe $REDIS_INSTANCE --region=$REGION &>/dev/null; then
    echo "✓ Redis instance '$REDIS_INSTANCE' already exists"
else
    echo "Creating Redis instance (this takes ~5 minutes)..."
    gcloud redis instances create $REDIS_INSTANCE \
        --size=1 \
        --region=$REGION \
        --redis-version=redis_6_x \
        --tier=basic
    echo "✓ Redis instance created"
fi

# Get Redis connection info
REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="get(host)")
REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="get(port)")
REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}"
echo "✓ Redis URL: $REDIS_URL"

# Build container image
echo ""
echo "Building Docker container..."
gcloud builds submit --tag $IMAGE_NAME
echo "✓ Container built and pushed to: $IMAGE_NAME"

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 600 \
    --max-instances 100 \
    --min-instances 0 \
    --set-env-vars "LLAMA_CLOUD_API_KEY=${LLAMA_CLOUD_API_KEY},GEMINI_API_KEY=${GEMINI_API_KEY},REDIS_URL=${REDIS_URL},ENVIRONMENT=production,MAX_CONCURRENT_EXTRACTIONS=50"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="get(status.url)")
echo ""
echo "======================================================================"
echo "  ✅ BACKEND DEPLOYMENT SUCCESSFUL!"
echo "======================================================================"
echo "Backend API URL: $SERVICE_URL"
echo "API Docs: ${SERVICE_URL}/docs"
echo "Health Check: ${SERVICE_URL}/health"
echo ""

# Update frontend with backend URL
echo "Updating frontend with backend URL..."
sed -i "s|http://localhost:8000|${SERVICE_URL}|g" frontend/index.html
echo "✓ Frontend updated with backend URL"

# Deploy frontend to Firebase
echo ""
echo "======================================================================"
echo "  Deploying Frontend to Firebase..."
echo "======================================================================"

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "Firebase CLI not found. Installing..."
    npm install -g firebase-tools
fi

# Initialize Firebase (if not already)
if [ ! -f "firebase.json" ]; then
    echo "Initializing Firebase..."
    cat > firebase.json <<EOF
{
  "hosting": {
    "public": "frontend",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
EOF
    echo "✓ Firebase config created"
fi

# Deploy to Firebase
echo "Deploying frontend..."
firebase deploy --only hosting --project $PROJECT_ID

FRONTEND_URL="https://${PROJECT_ID}.web.app"

echo ""
echo "======================================================================"
echo "  ✅ FULL DEPLOYMENT COMPLETE!"
echo "======================================================================"
echo ""
echo "📱 FRONTEND URL: $FRONTEND_URL"
echo "🔌 BACKEND API: $SERVICE_URL"
echo ""
echo "Test your deployment:"
echo "  1. Visit: $FRONTEND_URL"
echo "  2. Upload a PDF or DOCX file"
echo "  3. Watch the magic happen! ✨"
echo ""
echo "API Documentation: ${SERVICE_URL}/docs"
echo "Health Check: ${SERVICE_URL}/health"
echo ""
echo "======================================================================"
echo "  Cost Estimate (approximate):"
echo "  - Cloud Run: ~\$5-10/month (free tier available)"
echo "  - Redis: ~\$30/month"
echo "  - Firebase Hosting: Free (10GB/month)"
echo "  - Cloud Build: Free tier (120 min/day)"
echo "  Total: ~\$35-40/month"
echo "======================================================================"
