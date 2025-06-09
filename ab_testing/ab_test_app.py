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

@app.route('/api/executions/<execution_id>', methods=['DELETE'])
def api_delete_execution(execution_id):
    """Delete a pending or failed test execution."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        success = test_manager.delete_execution(execution_id)
        
        if success:
            return jsonify({"status": "success", "message": "Test execution deleted"})
        else:
            return jsonify({"error": "Test execution not found or cannot be deleted"}), 404
        
    except Exception as e:
        logger.error(f"Error deleting execution: {str(e)}")
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

# Cloud Workflows Webhook Endpoints

@app.route('/api/workflows/log', methods=['POST'])
def api_workflow_log():
    """Cloud Workflows endpoint for logging workflow events."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        execution_id = data.get('execution_id')
        event = data.get('event')
        timestamp = data.get('timestamp')
        
        logger.info(f"🔄 Workflow Event [{execution_id}]: {event} at {timestamp}")
        
        # Log additional details based on event type
        if event == "batch_started":
            worker_index = data.get('worker_index')
            batch_size = data.get('batch_size')
            logger.info(f"📊 Worker {worker_index} starting batch of {batch_size} tests")
        elif event == "batch_completed":
            worker_index = data.get('worker_index')
            batch_result = data.get('batch_result', {})
            logger.info(f"✅ Worker {worker_index} completed batch: {batch_result.get('tests_completed', 0)} tests")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error logging workflow event: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/workflows/prepare', methods=['POST'])
def api_workflow_prepare():
    """Cloud Workflows endpoint for preparing test execution."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
            
        execution_id = data.get('execution_id')
        config_name = data.get('config_name')
        parallel_workers = data.get('parallel_workers', 2)
        
        if not execution_id:
            return jsonify({
                "success": False,
                "error": "execution_id is required"
            }), 400
            
        if not config_name:
            return jsonify({
                "success": False,
                "error": "config_name is required"
            }), 400
        
        logger.info(f"🔄 Preparing workflow execution: {execution_id} with {parallel_workers} workers")
        logger.info(f"📋 Configuration: {config_name}")
        
        # Load configuration
        try:
            config_data = test_manager.load_configuration(config_name)
            logger.info(f"✅ Loaded configuration: {config_data.get('name', config_name)}")
        except FileNotFoundError:
            error_msg = f"Configuration file not found: {config_name}"
            logger.error(f"❌ {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 404
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        # Create test batches for parallel execution
        try:
            from .workflows_manager import CloudWorkflowsManager
            workflows_manager = CloudWorkflowsManager()
            test_batches = workflows_manager.create_test_batches(config_data, parallel_workers)
            
            if not test_batches:
                return jsonify({
                    "success": False,
                    "error": "Failed to create test batches - configuration may be invalid"
                }), 400
                
            logger.info(f"📊 Created {len(test_batches)} test batches")
            
        except Exception as e:
            error_msg = f"Failed to create test batches: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 500
        
        # Update execution status
        test_manager._update_execution_status(execution_id, "running")
        
        return jsonify({
            "success": True,
            "test_batches": test_batches,
            "total_batches": len(test_batches),
            "config_data": config_data
        })
        
    except Exception as e:
        logger.error(f"❌ Error preparing workflow execution: {str(e)}")
        logger.error(f"❌ Request data: {request.json}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/workflows/execute-batch', methods=['POST'])
def api_workflow_execute_batch():
    """Cloud Workflows endpoint for executing a test batch."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        execution_id = data.get('execution_id')
        worker_index = data.get('worker_index')
        test_batch = data.get('test_batch')
        
        if not execution_id:
            return jsonify({"error": "execution_id is required"}), 400
        if worker_index is None:
            return jsonify({"error": "worker_index is required"}), 400
        if not test_batch:
            return jsonify({"error": "test_batch is required"}), 400
        
        batch_id = test_batch.get('batch_id', f"batch_{worker_index}")
        tests = test_batch.get('tests', [])
        
        if not tests:
            logger.warning(f"⚠️ Worker {worker_index} received empty test batch {batch_id}")
            return jsonify({
                "success": True,
                "tests_completed": 0,
                "tests_failed": 0,
                "total_tests": 0,
                "duration": 0,
                "batch_id": batch_id,
                "worker_index": worker_index
            })
        
        logger.info(f"🔄 Worker {worker_index} executing batch {batch_id} with {len(tests)} tests")
        
        # Execute tests in this batch
        try:
            from .decorators import ABTestRunner
            runner = ABTestRunner(base_url=test_manager.base_url)
            
            batch_results = []
            tests_completed = 0
            tests_failed = 0
            start_time = datetime.now()
            
            for i, test_config in enumerate(tests):
                try:
                    logger.debug(f"🔄 Worker {worker_index} executing test {i+1}/{len(tests)}")
                    
                    # Validate test configuration
                    required_fields = ['model', 'user_type', 'think_mode', 'question']
                    for field in required_fields:
                        if field not in test_config:
                            raise ValueError(f"Missing required field: {field}")
                    
                    result = runner.run_single_test(
                        model=test_config['model'],
                        user_type=test_config['user_type'],
                        think_mode=test_config['think_mode'],
                        question=test_config['question']
                    )
                    batch_results.append(result)
                    
                    if result.success:
                        tests_completed += 1
                    else:
                        tests_failed += 1
                        logger.warning(f"⚠️ Test failed: {result.error}")
                        
                    # Add delay between tests
                    import time
                    delay = test_config.get('delay_between_tests', 2)
                    if delay > 0:
                        time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"❌ Test {i+1} failed in batch {batch_id}: {e}")
                    tests_failed += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Store batch results in Firestore
            if hasattr(test_manager, 'firestore_manager') and test_manager.firestore_manager:
                test_manager._store_result_summary(execution_id, batch_results)
            
            logger.info(f"✅ Worker {worker_index} completed batch {batch_id}: {tests_completed}/{len(tests)} successful in {duration:.1f}s")
            
            return jsonify({
                "success": True,
                "tests_completed": tests_completed,
                "tests_failed": tests_failed,
                "total_tests": len(tests),
                "duration": duration,
                "batch_id": batch_id,
                "worker_index": worker_index
            })
            
        except Exception as e:
            logger.error(f"❌ Failed to execute batch {batch_id}: {e}")
            return jsonify({
                "success": False,
                "error": f"Batch execution failed: {str(e)}",
                "batch_id": batch_id,
                "worker_index": worker_index
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error executing workflow batch: {str(e)}")
        logger.error(f"❌ Request data: {request.json}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/workflows/aggregate', methods=['POST'])
def api_workflow_aggregate():
    """Cloud Workflows endpoint for aggregating parallel results."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        execution_id = data.get('execution_id')
        if not execution_id:
            return jsonify({"error": "execution_id is required"}), 400
            
        parallel_results = data.get('parallel_results', [])
        
        logger.info(f"🔄 Aggregating results for execution: {execution_id}")
        logger.info(f"📊 Received {len(parallel_results)} parallel worker results")
        
        # If no parallel_results provided, try to get from database/Firestore
        if not parallel_results:
            logger.info("📊 No parallel_results provided, getting from database")
            execution = test_manager.get_test_status(execution_id)
            if execution:
                # Use the current stats from the execution record
                total_tests = execution.total_tests
                total_tests_completed = execution.completed_tests
                total_tests_failed = execution.failed_tests
                parallel_workers = 1  # Default if not tracked
                
                logger.info(f"📊 Retrieved from database: {total_tests_completed}/{total_tests} successful, {total_tests_failed} failed")
            else:
                logger.warning(f"⚠️ No execution found for {execution_id}")
                total_tests = 0
                total_tests_completed = 0
                total_tests_failed = 0
                parallel_workers = 0
        else:
            # Validate parallel results structure
            if not isinstance(parallel_results, list):
                logger.error(f"❌ parallel_results must be a list, got: {type(parallel_results)}")
                return jsonify({"error": "parallel_results must be a list"}), 400
            
            # Calculate totals across all workers
            total_tests_completed = 0
            total_tests_failed = 0
            total_tests = 0
            
            for i, result in enumerate(parallel_results):
                if not isinstance(result, dict):
                    logger.warning(f"⚠️ Worker {i} result is not a dict: {type(result)}")
                    continue
                    
                tests_completed = result.get('tests_completed', 0)
                tests_failed = result.get('tests_failed', 0)
                tests_total = result.get('total_tests', 0)
                
                logger.info(f"📊 Worker {i}: {tests_completed}/{tests_total} successful, {tests_failed} failed")
                
                total_tests_completed += tests_completed
                total_tests_failed += tests_failed
                total_tests += tests_total
            
            parallel_workers = len(parallel_results)
            logger.info(f"📊 Aggregated results: {total_tests_completed}/{total_tests} successful, {total_tests_failed} failed")
        
        # Update execution status in database
        if hasattr(test_manager, '_update_execution_stats'):
            test_manager._update_execution_stats(execution_id, total_tests, total_tests_completed, total_tests_failed)
        
        return jsonify({
            "success": True,
            "total_tests": total_tests,
            "tests_completed": total_tests_completed,
            "tests_failed": total_tests_failed,
            "parallel_workers": parallel_workers,
            "aggregation_time": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error aggregating workflow results: {str(e)}")
        logger.error(f"❌ Request data: {request.json}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/workflows/finalize', methods=['POST'])
def api_workflow_finalize():
    """Cloud Workflows endpoint for finalizing test execution."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        data = request.json
        execution_id = data.get('execution_id')
        final_status = data.get('final_status', 'completed')
        error_message = data.get('error_message')
        
        logger.info(f"🔄 Finalizing execution: {execution_id} with status: {final_status}")
        
        # If completing successfully, calculate actual test counts from results
        if final_status == "completed":
            try:
                # Get actual test results to calculate proper counts
                results = test_manager.get_test_results(execution_id)
                if results and 'results' in results:
                    total_completed = 0
                    total_failed = 0
                    total_tests = 0
                    
                    for result in results['results']:
                        tests_in_combo = result.get('total_tests', 0)
                        success_rate = result.get('success_rate', 0)
                        
                        completed_in_combo = int(tests_in_combo * success_rate)
                        failed_in_combo = tests_in_combo - completed_in_combo
                        
                        total_completed += completed_in_combo
                        total_failed += failed_in_combo
                        total_tests += tests_in_combo
                    
                    logger.info(f"📊 Calculated from results: {total_completed}/{total_tests} completed, {total_failed} failed")
                    
                    # Update execution statistics
                    if hasattr(test_manager, '_update_execution_stats'):
                        test_manager._update_execution_stats(execution_id, total_tests, total_completed, total_failed)
                
                test_manager._update_execution_status(execution_id, "completed")
            except Exception as calc_error:
                logger.error(f"Error calculating test counts: {calc_error}")
                test_manager._update_execution_status(execution_id, "completed")
        else:
            test_manager._update_execution_status(execution_id, "failed", error_message)
        
        # Update end time if using Firestore
        if hasattr(test_manager, 'firestore_manager') and test_manager.firestore_manager:
            execution = test_manager.firestore_manager.get_execution(execution_id)
            if execution:
                execution.end_time = datetime.now().isoformat()
                execution.status = final_status
                if error_message:
                    execution.error_message = error_message
                test_manager.firestore_manager.save_execution(execution)
        
        logger.info(f"✅ Execution {execution_id} finalized with status: {final_status}")
        
        return jsonify({
            "success": True,
            "execution_id": execution_id,
            "final_status": final_status
        })
        
    except Exception as e:
        logger.error(f"Error finalizing workflow execution: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/workflows/status/<execution_id>', methods=['GET'])
def api_workflow_status(execution_id):
    """Get workflow execution status."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        # Get execution from database
        execution = test_manager.get_test_status(execution_id)
        if not execution:
            return jsonify({"error": "Execution not found"}), 404
        
        # Get workflow status if using Cloud Workflows
        workflow_status = None
        if hasattr(test_manager, 'workflows_manager') and execution.error_message and "Cloud Workflow:" in execution.error_message:
            workflow_execution_name = execution.error_message.replace("Cloud Workflow: ", "")
            workflow_status = test_manager.workflows_manager.get_execution_status(workflow_execution_name)
        
        # Get workflow events if using Firestore
        workflow_events = []
        if hasattr(test_manager, 'firestore_manager'):
            workflow_events = test_manager.firestore_manager.get_workflow_events(execution_id, limit=10)
        
        return jsonify({
            "execution": {
                "execution_id": execution.execution_id,
                "config_name": execution.config_name,
                "status": execution.status,
                "start_time": execution.start_time,
                "end_time": execution.end_time,
                "total_tests": execution.total_tests,
                "completed_tests": execution.completed_tests,
                "failed_tests": execution.failed_tests,
                "error_message": execution.error_message
            },
            "workflow_status": workflow_status,
            "workflow_events": workflow_events
        })
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/workflows/cancel/<execution_id>', methods=['POST'])
def api_workflow_cancel(execution_id):
    """Cancel a running workflow execution."""
    try:
        if not test_manager:
            return jsonify({"error": "Test manager not initialized"}), 500
        
        # Get execution from database
        execution = test_manager.get_test_status(execution_id)
        if not execution:
            return jsonify({"error": "Execution not found"}), 404
        
        cancelled = False
        
        # Try to cancel workflow if it exists
        if hasattr(test_manager, 'workflows_manager') and execution.error_message and "Cloud Workflow:" in execution.error_message:
            workflow_execution_name = execution.error_message.replace("Cloud Workflow: ", "")
            cancelled = test_manager.workflows_manager.cancel_execution(workflow_execution_name)
            
            if cancelled:
                test_manager._update_execution_status(execution_id, "stopped", "Cancelled by user")
                logger.info(f"🛑 Cancelled workflow execution: {execution_id}")
        
        # Fallback to regular stop method
        if not cancelled:
            cancelled = test_manager.stop_test(execution_id)
        
        return jsonify({
            "success": cancelled,
            "message": "Workflow cancelled successfully" if cancelled else "Failed to cancel workflow",
            "execution_id": execution_id
        })
        
    except Exception as e:
        logger.error(f"Error cancelling workflow: {str(e)}")
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
            return jsonify({"error": "Results file not found"}), 404
        
        results_path = test_manager.results_dir / execution.results_file
        if not results_path.exists():
            return jsonify({"error": "Results file not found on disk"}), 404
        
        return send_file(results_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading results: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ab-test-dashboard"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.port, debug=config.debug) 