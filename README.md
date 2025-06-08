# A/B Testing Application for Graph RAG Systems

A comprehensive A/B testing framework for evaluating Graph RAG system performance with different models, user types, and configurations.

## 🌟 Features

- **Web-based Dashboard**: Intuitive interface for managing and monitoring A/B tests
- **Multiple Test Types**: Model comparison, user type analysis, think mode evaluation
- **Real-time Monitoring**: Live execution tracking with progress indicators
- **Comprehensive Analysis**: Detailed performance metrics and AI-generated recommendations
- **Pre-configured Tests**: Ready-to-use test configurations for various scenarios
- **60-second Timeout**: Extended timeout for complex Graph RAG queries
- **Persistent Storage**: SQLite for local development, Google Cloud Firestore for production
- **Cloud-Native**: Seamless deployment to Google Cloud Run with persistent data storage

## 📁 Package Contents

```
ab_testing_package/
├── ab_testing/                    # Core A/B testing modules
│   ├── __init__.py               # Package initialization
│   ├── ab_test_app.py            # Main Flask application
│   ├── decorators.py             # A/B testing decorators and runners
│   ├── test_manager.py           # Test lifecycle management
│   ├── config_generator.py       # Test configuration generator
│   ├── templates/                # Web interface templates
│   │   ├── ab_test_dashboard.html
│   │   ├── ab_test_configurations.html
│   │   ├── ab_test_executions.html
│   │   └── ab_test_results.html
│   └── configs/                  # Pre-generated test configurations
├── app.py                        # Application entry point
├── Dockerfile                    # Container configuration
├── requirements.txt              # Python dependencies
├── env_template                  # Environment variables template
├── .github/workflows/            # GitHub Actions deployment
│   └── deploy-ab-testing.yml
└── README.md                     # This file
```

## 🚀 Quick Start

### Local Development

1. **Clone and Setup**:
   ```bash
   cd ab_testing_package
   pip install -r requirements.txt
   cp env_template .env
   # Edit .env with your settings
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Dashboard**:
   - **Main Dashboard**: http://localhost:8080/
   - **Configurations**: http://localhost:8080/configurations
   - **Executions**: http://localhost:8080/executions
   - **Results**: http://localhost:8080/results

### GCP Deployment with Firestore

1. **Setup Google Cloud Project**:
   ```bash
   # Run the setup script to configure GCP resources
   chmod +x setup-gcp.sh
   ./setup-gcp.sh
   ```

   This script will:
   - Enable required APIs (Cloud Run, Firestore, Artifact Registry)
   - Create Firestore database for persistent storage
   - Set up service account with proper permissions
   - Generate service account key for GitHub Actions

2. **Configure GitHub Secrets**:
   - `GCP_SA_KEY`: Copy the entire contents of `github-actions-key.json`
   
   Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

3. **Deploy**:
   ```bash
   git init
   git add .
   git commit -m "Initial A/B testing app with Firestore"
   git branch -M main
   git remote add origin https://github.com/yourusername/ab-testing-app.git
   git push -u origin main
   ```

   - Push to `main` branch triggers automatic deployment
   - Check Actions tab for deployment progress
   - Access deployed app at the provided Cloud Run URL

4. **Test Firestore Connection** (Optional):
   ```bash
   # Test locally with service account credentials
   export GOOGLE_APPLICATION_CREDENTIALS="github-actions-key.json"
   python test_firestore.py
   ```

## 🧪 Test Configurations

The package includes pre-configured A/B tests:

### Model Comparison Tests
- Compare different Gemini models (2.5 Pro, 2.5 Flash, 2.0 Flash, etc.)
- Performance benchmarking across model types
- Cost vs. quality analysis

### Think Mode Evaluation
- Think mode vs. regular mode performance
- Response quality comparison
- Processing time analysis

### User Type Testing
- Business vs. Technical response styles
- User-specific optimization
- Response relevance scoring

### Category-Specific Tests
- Claims processing queries
- Technical features evaluation
- Compliance requirement testing
- Data field analysis
- System architecture questions

## 📊 Dashboard Features

### 🏠 Main Dashboard
- System overview and quick stats
- Recent test executions
- Performance summaries
- Quick test launcher

### ⚙️ Configurations Page
- Browse available test configurations
- Create new test scenarios
- Edit existing configurations
- Configuration templates

### 🔄 Executions Page
- Real-time test monitoring
- Progress tracking with visual indicators
- Start/stop test controls
- Live execution logs
- Auto-refresh every 10 seconds

### 📈 Results Page
- Comprehensive test analysis
- Model performance comparisons
- User type effectiveness
- Think mode impact analysis
- AI-generated recommendations
- Export functionality

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAPH_RAG_BASE_URL` | Target Graph RAG system URL | `https://aetraggraph-529012124872.us-central1.run.app` |
| `AB_TEST_TIMEOUT` | Request timeout in seconds | `60` |
| `AB_TEST_DEFAULT_DELAY` | Delay between tests in seconds | `2` |
| `AB_TEST_MAX_CONCURRENT` | Maximum concurrent tests | `3` |
| `USE_FIRESTORE` | Enable Firestore for persistent storage | `false` |
| `GCP_PROJECT_ID` | Google Cloud Project ID for Firestore | `ab-perf-test-dashboard` |
| `PORT` | Application port | `8080` |

### Supported Models
- `gemini-2.5-pro-preview-05-06` (with Think Mode)
- `gemini-2.5-flash-preview-05-20` (with Think Mode)
- `gemini-2.5-pro` (with Think Mode)
- `gemini-2.5-flash` (with Think Mode)
- `gemini-2.0-flash-exp`
- `gemini-2.0-flash-001`
- `gemini-1.5-flash-001`
- `gemini-1.5-pro-001`

## 💾 Data Persistence

The application supports two storage backends:

### Local Development (SQLite)
- **Default**: SQLite database for local development
- **Location**: `ab_testing/test_manager.db`
- **Features**: Full functionality, file-based storage
- **Setup**: No additional configuration required

### Production (Google Cloud Firestore)
- **Cloud-Native**: Firestore for production deployments
- **Features**: Scalable, managed NoSQL database
- **Collections**:
  - `test_executions`: Test run metadata and status
  - `test_results_summary`: Aggregated performance metrics
  - `test_configurations`: Saved test configurations
- **Setup**: Enabled automatically when `USE_FIRESTORE=true`

### Data Migration
When switching from SQLite to Firestore, existing data remains in SQLite. The application will start fresh with Firestore. To migrate data:

1. Export existing results from SQLite
2. Use the Firestore admin interface to import data
3. Or run tests again to populate Firestore

## 🛠️ Development

### Adding New Test Types

1. **Create Configuration Template**:
   ```python
   # In config_generator.py
   def generate_custom_test_config(self):
       return {
           "name": "custom_test",
           "description": "Custom test description",
           "models_to_test": ["gemini-2.0-flash-exp"],
           "user_types": ["business"],
           "think_mode_options": [False],
           "questions": ["Your custom questions here"]
       }
   ```

2. **Add Route Handler**:
   ```python
   # In ab_test_app.py
   @app.route('/api/custom-test', methods=['POST'])
   def create_custom_test():
       # Implementation here
   ```

### Custom Question Sets

Edit the question categories in `config_generator.py`:

```python
"claims_processing": [
    "How to identify Dental Claims?",
    "Your custom claims questions..."
],
"custom_category": [
    "Your custom questions here..."
]
```

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/configurations` | GET | Test configurations page |
| `/executions` | GET | Test executions monitoring |
| `/results` | GET | Test results analysis |
| `/api/status` | GET | System status |
| `/api/quick-test` | POST | Run quick test |
| `/api/configurations` | GET | List configurations |
| `/api/configurations` | POST | Create configuration |
| `/api/executions` | GET | List executions |
| `/api/executions` | POST | Start test execution |
| `/api/executions/<id>/stop` | POST | Stop execution |
| `/api/results/<id>` | GET | Get test results |
| `/api/results/<id>/analyze` | GET | Get analysis |

## 🔍 Troubleshooting

### Common Issues

1. **Connection Timeout**:
   - Increase `AB_TEST_TIMEOUT` environment variable
   - Check target Graph RAG system availability

2. **Database Issues**:
   - Ensure SQLite database permissions
   - Check disk space for results storage

3. **Memory Issues**:
   - Adjust Cloud Run memory allocation
   - Limit concurrent test executions

### Logging

Application logs include:
- Test execution progress
- API request/response details
- Error diagnostics
- Performance metrics

## 📜 License

This A/B testing framework is part of the Healthcare Graph RAG system and follows the same licensing terms.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the GitHub Issues page
- Review the troubleshooting section
- Examine application logs for error details

---

**🎉 Happy A/B Testing!** 

Monitor your Graph RAG system performance and optimize your AI applications with comprehensive testing and analysis. 