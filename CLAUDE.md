# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application locally
python app.py

# Run with environment variables
export FLASK_ENV=development
export PORT=8080
python app.py
```

### Testing Cloud Services
```bash
# Test Firestore connection (requires GOOGLE_APPLICATION_CREDENTIALS)
python test_firestore.py

# Test Cloud Tasks connection (requires GOOGLE_APPLICATION_CREDENTIALS)
python test_cloud_tasks.py
```

### Docker Development
```bash
# Build container
docker build -t ab-perf-test-dashboard .

# Run container
docker run -p 8080:8080 ab-perf-test-dashboard
```

### GCP Deployment
```bash
# Setup GCP resources (run once)
chmod +x setup-gcp.sh
./setup-gcp.sh

# Setup Cloud Workflows for parallel test execution
chmod +x setup-workflows.sh
./setup-workflows.sh

# Deploy via GitHub Actions (automatic on push to main)
git push origin main
```

## Architecture Overview

This is an A/B testing framework for evaluating Graph RAG system performance across different models, user types, and configurations.

### Core Components

- **Flask Application** (`ab_testing/ab_test_app.py`): Main web interface with REST API endpoints for managing tests and workflow coordination
- **Test Manager** (`ab_testing/test_manager.py`): Orchestrates test lifecycle, handles SQLite/Firestore storage, manages long-running tests via Cloud Workflows
- **Test Runner** (`ab_testing/decorators.py`): Core A/B testing engine that executes requests against the target Graph RAG system
- **Configuration Generator** (`ab_testing/config_generator.py`): Creates predefined test scenarios (model comparisons, user type tests, think mode evaluation)
- **Firestore Manager** (`ab_testing/firestore_manager.py`): Cloud-native persistence layer for production deployments with workflow progress tracking
- **Cloud Workflows Manager** (`ab_testing/workflows_manager.py`): Handles parallel execution of tests using Google Cloud Workflows
- **Cloud Tasks Manager** (`ab_testing/cloud_tasks_manager.py`): Legacy fallback for tests exceeding Cloud Run's 60-minute timeout

### Data Flow
1. User creates/selects test configuration via web UI
2. Test Manager queues execution (local SQLite or Firestore)
3. For complex/long tests (>30min estimated), automatically uses Cloud Workflows for parallel execution
4. Cloud Workflows splits tests into parallel batches (minimum 2 workers, auto-scaled based on duration)
5. Each worker executes tests against target Graph RAG system with progress tracking
6. Results aggregated and stored in Firestore with AI-generated recommendations

### Storage Strategy
- **Local Development**: SQLite database (`ab_testing/test_manager.db`)
- **Production**: Google Cloud Firestore with collections for executions, results, configurations, and workflow events
- **Parallel Execution**: Google Cloud Workflows (`workflows/ab-test-parallel.yaml`) for tests requiring parallel processing
- **Legacy Support**: Google Cloud Tasks queue (`ab-test-queue`) for backward compatibility

### Target System Integration
- Connects to Graph RAG system at `GRAPH_RAG_BASE_URL` (default: https://aetraggraph-529012124872.us-central1.run.app)
- Tests different Gemini models with/without Think Mode
- Evaluates responses for business vs technical user types
- 60-second timeout per request with configurable delays

### Web Interface Endpoints
- `/` - Main dashboard with system overview
- `/configurations` - Manage test configurations
- `/executions` - Monitor running tests with real-time progress
- `/results` - Analyze completed tests with AI recommendations

## Environment Configuration

### Required Variables
- `GRAPH_RAG_BASE_URL`: Target Graph RAG system URL
- `PORT`: Application port (default: 8080)

### Optional Cloud Features
- `USE_FIRESTORE=true`: Enable Firestore persistence
- `USE_CLOUD_WORKFLOWS=true`: Enable Cloud Workflows for parallel test execution
- `USE_CLOUD_TASKS=true`: Enable Cloud Tasks for long-running tests (legacy)
- `GCP_PROJECT_ID`: Google Cloud Project ID
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key

### Cloud Workflows Configuration
- `WORKFLOWS_LOCATION`: Cloud Workflows region (default: us-central1)
- `WORKFLOWS_NAME`: Workflow name (default: ab-test-parallel)
- `WORKFLOWS_SERVICE_ACCOUNT`: Service account for workflow execution

### Performance Tuning
- `AB_TEST_TIMEOUT`: Request timeout in seconds (default: 60)
- `AB_TEST_DEFAULT_DELAY`: Delay between tests (default: 2s)
- `AB_TEST_MAX_CONCURRENT`: Max concurrent tests (default: 3)

## Supported Models
- Gemini 2.5 Pro/Flash (with Think Mode support)
- Gemini 2.0 Flash variants
- Gemini 1.5 Pro/Flash

## Test Categories
- Model performance comparison
- Think Mode vs regular evaluation
- Business vs technical user response optimization
- Claims processing, compliance, and technical feature testing