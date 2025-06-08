"""
Standalone A/B Testing Flask Application
Runs independently on port 5004 with UI for managing test configurations and executions.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, abort
from flask_cors import CORS

# Import our A/B testing components
from .test_manager import ABTestManager
from .config_generator import ABTestConfigGenerator
from .decorators import ABTestRunner, TestConfiguration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global test manager
test_manager = None

class ABTestConfig:
    """Configuration for the A/B testing application."""
    def __init__(self):
        self.port = int(os.getenv("PORT", 8080))
        self.main_app_url = os.getenv("GRAPH_RAG_BASE_URL", "https://aetraggraph-529012124872.us-central1.run.app")
        self.debug = os.getenv("FLASK_ENV", "production") == "development"
        
        # Use paths from environment variables or fall back to defaults
        self.database_path = os.getenv("AB_TEST_DB_PATH", "ab_testing/test_manager.db")
        self.config_dir = os.getenv("AB_TEST_CONFIG_DIR", "ab_testing/configs")
        self.results_dir = os.getenv("AB_TEST_RESULTS_DIR", "ab_testing/results")

config = ABTestConfig()

def initialize_test_manager():
    """Initialize the test manager."""
    global test_manager
    
    try:
        test_manager = ABTestManager(
            database_path=config.database_path,
            config_dir=config.config_dir,
            results_dir=config.results_dir,
            base_url=config.main_app_url
        )
        
        logger.info("✅ A/B Test Manager initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing test manager: {str(e)}")
        return False

# Initialize test manager when module is imported
logger.info(f"🔧 Initializing A/B Test Manager...")
logger.info(f"💾 Database: {config.database_path}")
logger.info(f"📁 Config Dir: {config.config_dir}")
logger.info(f"📈 Results Dir: {config.results_dir}")
logger.info(f"🔗 Base URL: {config.main_app_url}")

if not initialize_test_manager():
    logger.error("❌ Failed to initialize test manager - API endpoints will return errors")

# Web Routes
@app.route('/')
def index():
    """Main dashboard."""
    return render_template('ab_test_dashboard.html')

@app.route('/configurations')
def configurations():
    """Configuration management page."""
    return render_template('ab_test_configurations.html')

@app.route('/executions')
def executions():
    """Test execution monitoring page."""
    return render_template('ab_test_executions.html')

@app.route('/results')
def results():
    """Results analysis page."""
    return render_template('ab_test_results.html')

# API Endpoints

@app.route('/api/status')
def api_status():
    """Get system status."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        # Get recent executions
        recent_executions = test_manager.list_test_executions(limit=5)
        
        # Get configuration count
        configs = test_manager.list_configurations()
        
        status = {
            "system_ready": True,
            "total_configurations": len(configs),
            "recent_executions": len(recent_executions),
            "active_tests": len([e for e in recent_executions if e.status == "running"]),
            "main_app_url": config.main_app_url,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/configurations', methods=['GET'])
def api_list_configurations():
    """List all test configurations."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        configs = test_manager.list_configurations()
        return jsonify({"configurations": configs})
        
    except Exception as e:
        logger.error(f"Error listing configurations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/configurations', methods=['POST'])
def api_create_configuration():
    """Create a new test configuration."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        config_type = data.get('config_type')
        name = data.get('name')
        
        if not config_type:
            return jsonify({"error": "config_type is required"}), 400
        
        # Extract additional parameters
        kwargs = {k: v for k, v in data.items() if k not in ['config_type', 'name']}
        
        filename = test_manager.create_test_configuration(
            config_type=config_type,
            name=name,
            **kwargs
        )
        
        return jsonify({
            "status": "success",
            "message": "Configuration created successfully",
            "filename": filename
        })
        
    except Exception as e:
        logger.error(f"Error creating configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/configurations/<config_name>')
def api_get_configuration(config_name):
    """Get a specific configuration."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        config = test_manager.load_configuration(config_name)
        return jsonify({"configuration": config})
        
    except Exception as e:
        logger.error(f"Error getting configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/configurations/<config_name>', methods=['DELETE'])
def api_delete_configuration(config_name):
    """Delete a configuration."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        config_path = Path(config.config_dir) / config_name
        if config_path.exists():
            config_path.unlink()
            return jsonify({"status": "success", "message": "Configuration deleted"})
        else:
            return jsonify({"error": "Configuration not found"}), 404
        
    except Exception as e:
        logger.error(f"Error deleting configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/executions', methods=['GET'])
def api_list_executions():
    """List test executions."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        limit = int(request.args.get('limit', 20))
        executions = test_manager.list_test_executions(limit=limit)
        
        # Convert to JSON-serializable format
        executions_data = []
        for execution in executions:
            executions_data.append({
                "execution_id": execution.execution_id,
                "config_name": execution.config_name,
                "status": execution.status,
                "start_time": execution.start_time,
                "end_time": execution.end_time,
                "total_tests": execution.total_tests,
                "completed_tests": execution.completed_tests,
                "failed_tests": execution.failed_tests,
                "results_file": execution.results_file,
                "error_message": execution.error_message
            })
        
        return jsonify({"executions": executions_data})
        
    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/executions', methods=['POST'])
def api_start_execution():
    """Start a new test execution."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        config_name = data.get('config_name')
        
        if not config_name:
            return jsonify({"error": "config_name is required"}), 400
        
        execution_id = test_manager.start_test(config_name)
        
        return jsonify({
            "status": "success",
            "message": "Test execution started",
            "execution_id": execution_id
        })
        
    except Exception as e:
        logger.error(f"Error starting execution: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/executions/<execution_id>/stop', methods=['POST'])
def api_stop_execution(execution_id):
    """Stop a running test execution."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        success = test_manager.stop_test(execution_id)
        
        if success:
            return jsonify({"status": "success", "message": "Test execution stopped"})
        else:
            return jsonify({"error": "Test execution not found or not running"}), 404
        
    except Exception as e:
        logger.error(f"Error stopping execution: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/executions/<execution_id>/status')
def api_execution_status(execution_id):
    """Get execution status."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        execution = test_manager.get_test_status(execution_id)
        
        if not execution:
            return jsonify({"error": "Execution not found"}), 404
        
        return jsonify({
            "execution_id": execution.execution_id,
            "config_name": execution.config_name,
            "status": execution.status,
            "start_time": execution.start_time,
            "end_time": execution.end_time,
            "total_tests": execution.total_tests,
            "completed_tests": execution.completed_tests,
            "failed_tests": execution.failed_tests,
            "results_file": execution.results_file,
            "error_message": execution.error_message
        })
        
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/executions/<execution_id>/results')
def api_execution_results(execution_id):
    """Get execution results."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        results = test_manager.get_test_results(execution_id)
        
        if not results:
            return jsonify({"error": "Results not found or not available yet"}), 404
        
        return jsonify({"results": results})
        
    except Exception as e:
        logger.error(f"Error getting execution results: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/executions/<execution_id>/analysis')
def api_execution_analysis(execution_id):
    """Get execution analysis."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        analysis = test_manager.analyze_test_results(execution_id)
        
        if not analysis:
            return jsonify({"error": "Analysis not available"}), 404
        
        return jsonify({"analysis": analysis})
        
    except Exception as e:
        logger.error(f"Error getting execution analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/quick-test', methods=['POST'])
def api_quick_test():
    """Run a quick test with random parameters."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        # Generate random test combination
        config_gen = ABTestConfigGenerator()
        combo = config_gen.get_random_test_combination()
        
        # Create quick test configuration
        quick_config = TestConfiguration(
            name="quick_test",
            description="Quick random test",
            models=[combo["model"]],
            user_types=[combo["user_type"]],
            think_mode_options=[combo["think_mode"]],
            questions=[combo["question"]],
            iterations=1,
            delay_between_tests=1.0
        )
        
        # Run test
        runner = ABTestRunner(base_url=config.main_app_url)
        results = runner.run_test_suite(quick_config)
        
        return jsonify({
            "status": "success",
            "test_combination": combo,
            "results": [
                {
                    "test_id": r.test_id,
                    "timestamp": r.timestamp,
                    "model": r.model,
                    "user_type": r.user_type,
                    "think_mode": r.think_mode,
                    "question": r.question,
                    "response_time": r.response_time,
                    "success": r.success,
                    "error": r.error
                } for r in results
            ],
            "summary": runner.get_summary_stats()
        })
        
    except Exception as e:
        logger.error(f"Error running quick test: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-configs', methods=['POST'])
def api_generate_default_configs():
    """Generate all default configurations."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        config_gen = ABTestConfigGenerator(config.config_dir)
        saved_files = config_gen.generate_all_default_configs()
        
        return jsonify({
            "status": "success",
            "message": f"Generated {len(saved_files)} default configurations",
            "files": saved_files
        })
        
    except Exception as e:
        logger.error(f"Error generating default configs: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def api_cleanup():
    """Cleanup old test executions."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        days_old = int(request.json.get('days_old', 30))
        cleaned_count = test_manager.cleanup_old_executions(days_old)
        
        return jsonify({
            "status": "success",
            "message": f"Cleaned up {cleaned_count} old executions",
            "cleaned_count": cleaned_count
        })
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Cloud Tasks Webhook Endpoints

@app.route('/api/tasks/execute-ab-test', methods=['POST'])
def api_cloud_task_execute_test():
    """Cloud Tasks webhook endpoint for executing A/B tests."""
    try:
        # Verify this is a Cloud Tasks request
        task_name = request.headers.get('X-CloudTasks-TaskName', '')
        queue_name = request.headers.get('X-CloudTasks-QueueName', '')
        
        if not task_name or not queue_name:
            logger.warning("Unauthorized Cloud Task execution attempt")
            return jsonify({"error": "Unauthorized"}), 401
        
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        execution_id = data.get('execution_id')
        config_name = data.get('config_name')
        
        if not execution_id or not config_name:
            return jsonify({"error": "execution_id and config_name are required"}), 400
        
        logger.info(f"⚡ Cloud Task executing A/B test: {execution_id}")
        
        # Execute the test via the test manager
        success = test_manager.execute_test_via_cloud_task(execution_id, config_name)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Test execution completed: {execution_id}",
                "execution_id": execution_id
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Test execution failed: {execution_id}",
                "execution_id": execution_id
            }), 500
        
    except Exception as e:
        logger.error(f"Error in Cloud Task execution: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/cleanup', methods=['POST'])
def api_cloud_task_cleanup():
    """Cloud Tasks webhook endpoint for cleanup operations."""
    try:
        # Verify this is a Cloud Tasks request
        task_name = request.headers.get('X-CloudTasks-TaskName', '')
        queue_name = request.headers.get('X-CloudTasks-QueueName', '')
        
        if not task_name or not queue_name:
            logger.warning("Unauthorized Cloud Task cleanup attempt")
            return jsonify({"error": "Unauthorized"}), 401
        
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        days_old = data.get('days_old', 30)
        
        logger.info(f"🧹 Cloud Task executing cleanup: {days_old} days old")
        
        cleaned_count = test_manager.cleanup_old_executions(days_old=days_old)
        
        return jsonify({
            "status": "success",
            "message": f"Cleanup completed: {cleaned_count} items",
            "cleaned_count": cleaned_count
        })
        
    except Exception as e:
        logger.error(f"Error in Cloud Task cleanup: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/status')
def api_cloud_tasks_status():
    """Get Cloud Tasks status and queue information."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        # Check if Cloud Tasks is enabled
        use_cloud_tasks = os.getenv('USE_CLOUD_TASKS', '').lower() == 'true'
        
        if not use_cloud_tasks:
            return jsonify({
                "cloud_tasks_enabled": False,
                "message": "Cloud Tasks is not enabled"
            })
        
        if hasattr(test_manager, 'cloud_tasks_manager'):
            # Get basic queue information
            tasks = test_manager.cloud_tasks_manager.list_tasks(page_size=10)
            
            return jsonify({
                "cloud_tasks_enabled": True,
                "queue_name": test_manager.cloud_tasks_manager.queue_name,
                "project_id": test_manager.cloud_tasks_manager.project_id,
                "location": test_manager.cloud_tasks_manager.location,
                "recent_tasks": len(tasks),
                "tasks": tasks[:5]  # Return first 5 tasks
            })
        else:
            return jsonify({
                "cloud_tasks_enabled": True,
                "error": "Cloud Tasks manager not initialized"
            })
        
    except Exception as e:
        logger.error(f"Error getting Cloud Tasks status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/results/<execution_id>')
def api_download_results(execution_id):
    """Download results file for an execution."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        execution = test_manager.get_test_status(execution_id)
        
        if not execution or not execution.results_file:
            abort(404)
        
        results_path = Path(config.results_dir) / execution.results_file
        
        if not results_path.exists():
            abort(404)
        
        return send_file(
            results_path,
            as_attachment=True,
            download_name=f"ab_test_results_{execution_id}.json"
        )
        
    except Exception as e:
        logger.error(f"Error downloading results: {str(e)}")
        abort(500)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "test_manager_ready": test_manager is not None,
        "main_app_url": config.main_app_url,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("🚀 Starting A/B Testing Flask Application...")
    logger.info(f"📊 Port: {config.port}")
    logger.info(f"🔗 Main App URL: {config.main_app_url}")
    logger.info(f"💾 Database: {config.database_path}")
    logger.info(f"📁 Config Dir: {config.config_dir}")
    logger.info(f"📈 Results Dir: {config.results_dir}")
    
    logger.info(f"🌐 Access A/B Testing Dashboard at: http://localhost:{config.port}")
    logger.info(f"📋 Configuration Management: http://localhost:{config.port}/configurations")
    logger.info(f"🏃 Test Executions: http://localhost:{config.port}/executions")
    logger.info(f"📊 Results Analysis: http://localhost:{config.port}/results")
    
    app.run(
        host='0.0.0.0',
        port=config.port,
        debug=config.debug,
        threaded=True
    ) 