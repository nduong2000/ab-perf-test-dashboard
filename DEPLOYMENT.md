# Deployment Guide for A/B Performance Test Dashboard

This guide will help you deploy your A/B testing dashboard to Google Cloud Run using GitHub Actions.

## Prerequisites

1. **Google Cloud CLI installed**: [Install gcloud CLI](https://cloud.google.com/sdk/docs/install)
2. **Docker installed**: [Install Docker](https://docs.docker.com/get-docker/)
3. **GitHub repository**: Your code should be in a GitHub repository

## Step 1: Setup Google Cloud Project

Run the automated setup script:

```bash
./setup-gcp.sh
```

This script will:
- Enable required APIs (Cloud Build, Cloud Run, Artifact Registry)
- Create an Artifact Registry repository
- Create a service account for GitHub Actions
- Grant necessary permissions
- Generate a service account key

## Step 2: Configure GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Create a secret named `GCP_SA_KEY`
5. Copy the entire contents of `github-actions-key.json` as the value
6. Save the secret

## Step 3: Deploy via GitHub Actions

Push your code to the `main` or `master` branch to trigger automatic deployment:

```bash
git add .
git commit -m "Deploy to Cloud Run"
git push origin main
```

The GitHub Actions workflow will:
- Build the Docker image
- Push it to Google Artifact Registry
- Deploy to Cloud Run with proper environment variables

## Manual Deployment (if needed)

If you need to deploy manually, you can use these CLI commands:

### Build and Push Docker Image

```bash
# Build the image
docker build -t us-central1-docker.pkg.dev/ab-perf-test-dashboard/ab-perf-test-dashboard/ab-perf-test-dashboard:latest .

# Push to registry
docker push us-central1-docker.pkg.dev/ab-perf-test-dashboard/ab-perf-test-dashboard/ab-perf-test-dashboard:latest
```

### Deploy to Cloud Run

```bash
gcloud run deploy ab-perf-test-dashboard \
  --image=us-central1-docker.pkg.dev/ab-perf-test-dashboard/ab-perf-test-dashboard/ab-perf-test-dashboard:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --set-env-vars=FLASK_ENV=production,PORT=8080,GRAPH_RAG_BASE_URL=https://aetraggraph-529012124872.us-central1.run.app
```

## Environment Variables

The following environment variables are automatically set during deployment:

- `FLASK_ENV=production`
- `PORT=8080`
- `GRAPH_RAG_BASE_URL=https://aetraggraph-529012124872.us-central1.run.app`
- `AB_TEST_TIMEOUT=60`
- `AB_TEST_DEFAULT_DELAY=2`
- `AB_TEST_MAX_CONCURRENT=3`
- `AB_TEST_DB_PATH=ab_testing/test_manager.db`
- `AB_TEST_CONFIG_DIR=ab_testing/configs`
- `AB_TEST_RESULTS_DIR=ab_testing/results`
- `LOG_LEVEL=INFO`

## Accessing Your Application

After deployment, your application will be available at:
```
https://ab-perf-test-dashboard-[hash]-uc.a.run.app
```

The exact URL will be shown in the GitHub Actions output or you can find it in the Google Cloud Console.

## Monitoring and Logs

- **Cloud Run Console**: https://console.cloud.google.com/run
- **View Logs**: Click on your service and go to the "Logs" tab
- **Metrics**: Monitor CPU, memory, and request metrics in the console

## Troubleshooting

### Common Issues

1. **Permission Denied**: Make sure your service account has the correct permissions
2. **Build Fails**: Check if all dependencies are in `requirements.txt`
3. **Container Won't Start**: Check the logs for startup errors

### Useful Commands

```bash
# Check service status
gcloud run services describe ab-perf-test-dashboard --region=us-central1

# View logs
gcloud logs read --project=ab-perf-test-dashboard --service=ab-perf-test-dashboard

# Update environment variables
gcloud run services update ab-perf-test-dashboard \
  --region=us-central1 \
  --set-env-vars=NEW_VAR=value

# Delete service (if needed)
gcloud run services delete ab-perf-test-dashboard --region=us-central1
```

## Security Notes

- The service is deployed with `--allow-unauthenticated` for easy access
- Consider adding authentication if handling sensitive data
- Service account keys should be kept secure and rotated regularly

## Cost Optimization

Cloud Run pricing is based on:
- CPU and memory allocation
- Number of requests
- Request processing time

The current configuration (512Mi memory, 1 CPU) should be cost-effective for development and testing. 