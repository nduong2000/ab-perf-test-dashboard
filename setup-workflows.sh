#!/bin/bash

# Setup Cloud Workflows for A/B Testing Dashboard
# This script deploys the Cloud Workflows definition and sets up necessary permissions

set -e

# Get current project from gcloud config
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
PROJECT_ID="${GCP_PROJECT_ID:-$CURRENT_PROJECT}"
REGION="${WORKFLOWS_LOCATION:-us-central1}"
WORKFLOW_NAME="${WORKFLOWS_NAME:-ab-test-parallel}"
SERVICE_ACCOUNT="${WORKFLOWS_SERVICE_ACCOUNT:-workflows-sa@${PROJECT_ID}.iam.gserviceaccount.com}"
CLOUD_RUN_SERVICE_URL="${CLOUD_RUN_SERVICE_URL:-https://ab-perf-test-dashboard-929371999924.us-central1.run.app}"

echo "🔄 Setting up Cloud Workflows for A/B Testing Dashboard"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Workflow Name: $WORKFLOW_NAME"

# Enable required APIs
echo "📋 Enabling required Google Cloud APIs..."
gcloud services enable workflows.googleapis.com --project=$PROJECT_ID
gcloud services enable workflowexecutions.googleapis.com --project=$PROJECT_ID
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable firestore.googleapis.com --project=$PROJECT_ID

# Create service account for workflows if it doesn't exist
echo "👤 Setting up service account for workflows..."
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID >/dev/null 2>&1; then
    gcloud iam service-accounts create workflows-sa \
        --display-name="Cloud Workflows Service Account" \
        --description="Service account for A/B testing workflows" \
        --project=$PROJECT_ID
    echo "✅ Created service account: $SERVICE_ACCOUNT"
else
    echo "📋 Service account already exists: $SERVICE_ACCOUNT"
fi

# Grant necessary permissions to the service account
echo "🔐 Setting up IAM permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/workflows.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/logging.logWriter"

# Deploy the workflow
echo "🚀 Deploying Cloud Workflow..."
if gcloud workflows describe $WORKFLOW_NAME --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "📋 Updating existing workflow: $WORKFLOW_NAME"
    gcloud workflows deploy $WORKFLOW_NAME \
        --source=workflows/ab-test-parallel.yaml \
        --location=$REGION \
        --service-account=$SERVICE_ACCOUNT \
        --project=$PROJECT_ID
else
    echo "📋 Creating new workflow: $WORKFLOW_NAME"
    gcloud workflows deploy $WORKFLOW_NAME \
        --source=workflows/ab-test-parallel.yaml \
        --location=$REGION \
        --service-account=$SERVICE_ACCOUNT \
        --project=$PROJECT_ID
fi

echo "✅ Cloud Workflow deployed successfully!"

# Test the workflow deployment
echo "🧪 Testing workflow deployment..."
WORKFLOW_URL="https://workflowexecutions.googleapis.com/v1/projects/$PROJECT_ID/locations/$REGION/workflows/$WORKFLOW_NAME"
echo "Workflow URL: $WORKFLOW_URL"

# Set environment variables for the application
echo "🔧 Setting up environment variables..."
echo "Add these environment variables to your Cloud Run service:"
echo "USE_CLOUD_WORKFLOWS=true"
echo "GCP_PROJECT_ID=$PROJECT_ID"
echo "WORKFLOWS_LOCATION=$REGION"
echo "WORKFLOWS_NAME=$WORKFLOW_NAME"
echo "WORKFLOWS_SERVICE_ACCOUNT=$SERVICE_ACCOUNT"

# Update Cloud Run service with new environment variables
echo "🔄 Updating Cloud Run service environment..."
CLOUD_RUN_SERVICE_NAME=$(gcloud run services list --platform=managed --region=$REGION --filter="metadata.name~ab-perf-test-dashboard" --format="value(metadata.name)" --limit=1 --project=$PROJECT_ID)

if [ -n "$CLOUD_RUN_SERVICE_NAME" ]; then
    echo "📋 Found Cloud Run service: $CLOUD_RUN_SERVICE_NAME"
    
    gcloud run services update $CLOUD_RUN_SERVICE_NAME \
        --set-env-vars="USE_CLOUD_WORKFLOWS=true,GCP_PROJECT_ID=$PROJECT_ID,WORKFLOWS_LOCATION=$REGION,WORKFLOWS_NAME=$WORKFLOW_NAME" \
        --region=$REGION \
        --project=$PROJECT_ID
    
    echo "✅ Updated Cloud Run service with workflow environment variables"
else
    echo "⚠️ Cloud Run service not found. Please manually set these environment variables:"
    echo "USE_CLOUD_WORKFLOWS=true"
    echo "GCP_PROJECT_ID=$PROJECT_ID"
    echo "WORKFLOWS_LOCATION=$REGION"
    echo "WORKFLOWS_NAME=$WORKFLOW_NAME"
fi

echo ""
echo "🎉 Cloud Workflows setup completed!"
echo ""
echo "Next steps:"
echo "1. Deploy your application with the new environment variables"
echo "2. Test the comprehensive_test configuration to verify parallel execution"
echo "3. Monitor workflow executions in the Google Cloud Console"
echo ""
echo "To execute a workflow manually:"
echo "gcloud workflows execute $WORKFLOW_NAME \\"
echo "  --data='{\"execution_id\":\"test-123\",\"config_name\":\"comprehensive_test\",\"service_url\":\"$CLOUD_RUN_SERVICE_URL\",\"parallel_workers\":2}' \\"
echo "  --location=$REGION \\"
echo "  --project=$PROJECT_ID"