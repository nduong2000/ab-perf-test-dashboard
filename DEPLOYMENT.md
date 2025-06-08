# Deployment Guide - A/B Testing Dashboard with Firestore

This guide walks you through deploying the A/B Testing Dashboard to Google Cloud Run with persistent Firestore storage.

## 🚀 Quick Deployment

### Prerequisites
- Google Cloud SDK installed and configured
- GitHub repository for your project
- Google Cloud Project with billing enabled

### Step 1: Setup Google Cloud Resources

Run the automated setup script:

```bash
chmod +x setup-gcp.sh
./setup-gcp.sh
```

This script will:
- ✅ Enable required APIs (Cloud Run, Firestore, Artifact Registry, Cloud Build)
- ✅ Create Firestore database in native mode
- ✅ Set up Artifact Registry repository
- ✅ Create service account with proper permissions
- ✅ Generate service account key for GitHub Actions

### Step 2: Configure GitHub Actions

1. **Add GitHub Secret**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `GCP_SA_KEY`
   - Value: Copy the entire contents of `github-actions-key.json`

2. **Verify Workflow Configuration**:
   The `.github/workflows/deploy-to-cloudrun.yml` is pre-configured with:
   - Firestore environment variables
   - Proper service account permissions
   - Automatic deployment on push to main

### Step 3: Deploy

```bash
git add .
git commit -m "Deploy A/B Testing Dashboard with Firestore"
git push origin main
```

The GitHub Actions workflow will:
1. Build the Docker container
2. Push to Google Artifact Registry
3. Deploy to Cloud Run with Firestore enabled
4. Provide the deployment URL

## 🔧 Manual Deployment (Alternative)

If you prefer manual deployment:

### Build and Push Container

```bash
# Set variables
PROJECT_ID="ab-perf-test-dashboard"
REGION="us-central1"
SERVICE_NAME="ab-perf-test-dashboard"

# Build and push
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest
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
  --set-env-vars=FLASK_ENV=production,GRAPH_RAG_BASE_URL=https://aetraggraph-529012124872.us-central1.run.app,USE_FIRESTORE=true,GCP_PROJECT_ID=ab-perf-test-dashboard
```

## 🧪 Testing the Deployment

### 1. Test Firestore Connection

```bash
# Set credentials for local testing
export GOOGLE_APPLICATION_CREDENTIALS="github-actions-key.json"
export USE_FIRESTORE=true
export GCP_PROJECT_ID=ab-perf-test-dashboard

# Run the test script
python test_firestore.py
```

Expected output:
```
✅ Successfully imported Firestore manager
🔥 Testing Firestore connection...
✅ Firestore connection successful
📝 Testing basic operations...
✅ Save operation successful
✅ Retrieve operation successful
✅ Update operation successful
✅ List operation successful
✅ All tests passed! Firestore is ready for use.
```

### 2. Test the Deployed Application

Visit your Cloud Run URL and verify:
- ✅ Dashboard loads successfully
- ✅ Can create test configurations
- ✅ Can start test executions
- ✅ Data persists between sessions
- ✅ Results are stored in Firestore

## 📊 Monitoring and Maintenance

### View Firestore Data

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to Firestore → Data
3. Browse collections:
   - `test_executions`: Test run metadata
   - `test_results_summary`: Performance metrics
   - `test_configurations`: Saved configurations

### Monitor Cloud Run

1. Go to Cloud Run in Google Cloud Console
2. Click on your service
3. View metrics, logs, and revisions
4. Monitor CPU, memory, and request metrics

### Cleanup Old Data

The application includes automatic cleanup:
```python
# Cleanup executions older than 30 days
manager.cleanup_old_executions(days_old=30)
```

Or manually via Firestore console.

## 🔒 Security Considerations

### Service Account Permissions

The setup script grants minimal required permissions:
- `roles/run.admin`: Deploy and manage Cloud Run services
- `roles/storage.admin`: Access Cloud Storage (for build artifacts)
- `roles/artifactregistry.writer`: Push container images
- `roles/datastore.user`: Read/write Firestore data
- `roles/iam.serviceAccountUser`: Use service account

### Network Security

- Cloud Run service allows unauthenticated access (for dashboard)
- Consider adding Cloud IAP for additional security
- Firestore uses Google Cloud's built-in security

### Data Privacy

- Test results may contain sensitive information
- Consider implementing data retention policies
- Use Firestore security rules for fine-grained access control

## 🛠️ Troubleshooting

### Common Issues

**1. Firestore Permission Denied**
```bash
# Check service account permissions
gcloud projects get-iam-policy ab-perf-test-dashboard
```

**2. Container Build Fails**
```bash
# Check build logs
gcloud builds list --limit=5
gcloud builds log [BUILD_ID]
```

**3. Cloud Run Deployment Fails**
```bash
# Check service logs
gcloud run services logs read ab-perf-test-dashboard --region=us-central1
```

**4. GitHub Actions Fails**
- Verify `GCP_SA_KEY` secret is correctly set
- Check that service account has required permissions
- Ensure project ID matches in all configurations

### Getting Help

1. Check Cloud Run logs for application errors
2. Verify Firestore connection with test script
3. Review GitHub Actions workflow logs
4. Check Google Cloud Console for service status

## 🔄 Updates and Maintenance

### Updating the Application

1. Make changes to your code
2. Commit and push to main branch
3. GitHub Actions automatically deploys updates
4. Zero-downtime deployment with Cloud Run

### Scaling

Cloud Run automatically scales based on traffic:
- Minimum instances: 0 (cost-effective)
- Maximum instances: 100 (configurable)
- Concurrent requests: 80 per instance
- CPU allocation: Only during request processing

### Backup Strategy

Firestore provides automatic backups:
- Point-in-time recovery
- Export to Cloud Storage
- Cross-region replication available

For critical data, consider:
```bash
# Export Firestore data
gcloud firestore export gs://your-backup-bucket
```

## 📈 Performance Optimization

### Firestore Best Practices

1. **Efficient Queries**: Use indexed fields for filtering
2. **Batch Operations**: Group multiple writes together
3. **Connection Pooling**: Reuse Firestore client instances
4. **Pagination**: Limit query results for large datasets

### Cloud Run Optimization

1. **Memory Allocation**: Start with 512Mi, adjust based on usage
2. **CPU Allocation**: Use 1 CPU for most workloads
3. **Concurrency**: Default 80 concurrent requests per instance
4. **Cold Starts**: Consider minimum instances for high-traffic apps

This completes your deployment setup! Your A/B Testing Dashboard is now running on Google Cloud with persistent Firestore storage. 