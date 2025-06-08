#!/bin/bash

# Setup script for Google Cloud Run deployment
# Run this script to set up your GCP project for deployment

set -e

PROJECT_ID="ab-perf-test-dashboard"
REGION="us-central1"
SERVICE_NAME="ab-perf-test-dashboard"

echo "🚀 Setting up Google Cloud Project: $PROJECT_ID"

# Set the project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable firestore.googleapis.com

# Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository..."
gcloud artifacts repositories create $SERVICE_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for AB Performance Test Dashboard" \
    --quiet || echo "Repository already exists"

# Initialize Firestore database
echo "🔥 Initializing Firestore database..."
gcloud firestore databases create \
    --location=$REGION \
    --type=firestore-native \
    --quiet || echo "Firestore database already exists"

# Configure Docker authentication
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Create service account for GitHub Actions
echo "👤 Creating service account for GitHub Actions..."
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Service Account" \
    --description="Service account for GitHub Actions deployments" \
    --quiet || echo "Service account already exists"

# Grant necessary permissions to the service account
echo "🔑 Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

# Grant Firestore permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

# Create and download service account key
echo "🗝️  Creating service account key..."
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions@${PROJECT_ID}.iam.gserviceaccount.com

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add the contents of 'github-actions-key.json' as a GitHub secret named 'GCP_SA_KEY'"
echo "2. Go to your GitHub repository settings > Secrets and variables > Actions"
echo "3. Click 'New repository secret'"
echo "4. Name: GCP_SA_KEY"
echo "5. Value: Copy and paste the entire contents of github-actions-key.json"
echo ""
echo "🔥 Manual deployment command (if needed):"
echo "gcloud run deploy $SERVICE_NAME \\"
echo "  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest \\"
echo "  --region=$REGION \\"
echo "  --platform=managed \\"
echo "  --allow-unauthenticated \\"
echo "  --port=8080 \\"
echo "  --memory=512Mi \\"
echo "  --cpu=1 \\"
echo "  --set-env-vars=FLASK_ENV=production,GRAPH_RAG_BASE_URL=https://aetraggraph-529012124872.us-central1.run.app,USE_FIRESTORE=true,GCP_PROJECT_ID=${PROJECT_ID}"
echo ""
echo "🐳 Manual Docker build and push (if needed):"
echo "docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest ."
echo "docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest" 