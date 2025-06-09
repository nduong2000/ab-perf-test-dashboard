"""
Cloud Workflows Manager
Handles long-running A/B test executions using Google Cloud Workflows for parallel processing.
"""

import os
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from google.cloud import workflows_v1
from google.cloud.workflows import executions_v1
from google.protobuf import duration_pb2
import math

logger = logging.getLogger(__name__)

class CloudWorkflowsManager:
    """Manages long-running A/B test executions using Google Cloud Workflows."""
    
    def __init__(self, 
                 project_id: str = None,
                 location: str = None,
                 workflow_name: str = None,
                 service_url: str = None):
        """Initialize Cloud Workflows client."""
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID', 'ab-perf-test-dashboard')
        self.location = location or os.getenv('WORKFLOWS_LOCATION', 'us-central1')
        self.workflow_name = workflow_name or os.getenv('WORKFLOWS_NAME', 'ab-test-parallel')
        self.service_url = service_url or os.getenv('CLOUD_RUN_SERVICE_URL', 'https://ab-perf-test-dashboard-929371999924.us-central1.run.app')
        
        try:
            self.workflows_client = workflows_v1.WorkflowsClient()
            self.executions_client = executions_v1.ExecutionsClient()
            
            # Build workflow path
            self.workflow_path = self.workflows_client.workflow_path(
                self.project_id, self.location, self.workflow_name
            )
            
            logger.info(f"⚡ Connected to Cloud Workflows: {self.workflow_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Cloud Workflows: {e}")
            raise
    
    def create_workflow_execution(self, 
                                execution_id: str, 
                                config_name: str,
                                parallel_workers: int = None) -> str:
        """
        Create a Cloud Workflow execution for running an A/B test.
        
        Args:
            execution_id: Unique identifier for the test execution
            config_name: Name of the test configuration to run
            parallel_workers: Number of parallel workers (auto-calculated if not provided)
            
        Returns:
            Workflow execution name/ID
        """
        try:
            # Auto-calculate parallel workers if not provided
            if parallel_workers is None:
                parallel_workers = self._calculate_parallel_workers(config_name)
            
            # Prepare the workflow arguments
            workflow_args = {
                "execution_id": execution_id,
                "config_name": config_name,
                "service_url": self.service_url,
                "parallel_workers": parallel_workers
            }
            
            # Create the execution
            execution_request = executions_v1.CreateExecutionRequest(
                parent=self.workflow_path,
                execution=executions_v1.Execution(
                    argument=json.dumps(workflow_args)
                )
            )
            
            response = self.executions_client.create_execution(request=execution_request)
            
            execution_name = response.name
            logger.info(f"⚡ Created Cloud Workflow execution: {execution_id} -> {execution_name}")
            logger.info(f"📊 Using {parallel_workers} parallel workers")
            
            return execution_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create Cloud Workflow execution for {execution_id}: {e}")
            raise
    
    def get_execution_status(self, execution_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status information about a workflow execution.
        
        Args:
            execution_name: Full execution name/path
            
        Returns:
            Execution status information or None if not found
        """
        try:
            execution = self.executions_client.get_execution(name=execution_name)
            
            status_info = {
                "name": execution.name,
                "state": execution.state.name,
                "start_time": execution.start_time.ToDatetime() if execution.start_time else None,
                "end_time": execution.end_time.ToDatetime() if execution.end_time else None,
                "duration": None,
                "result": None,
                "error": None
            }
            
            # Calculate duration if both times are available
            if execution.start_time and execution.end_time:
                start = execution.start_time.ToDatetime()
                end = execution.end_time.ToDatetime()
                status_info["duration"] = (end - start).total_seconds()
            
            # Parse result or error
            if execution.state == executions_v1.Execution.State.SUCCEEDED:
                if execution.result:
                    status_info["result"] = json.loads(execution.result)
            elif execution.state == executions_v1.Execution.State.FAILED:
                if execution.error:
                    status_info["error"] = execution.error
            
            return status_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get workflow execution status {execution_name}: {e}")
            return None
    
    def cancel_execution(self, execution_name: str) -> bool:
        """
        Cancel a running workflow execution.
        
        Args:
            execution_name: Full execution name/path
            
        Returns:
            True if successfully cancelled
        """
        try:
            self.executions_client.cancel_execution(name=execution_name)
            logger.info(f"🛑 Cancelled workflow execution: {execution_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel workflow execution {execution_name}: {e}")
            return False
    
    def list_executions(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        List workflow executions.
        
        Args:
            page_size: Maximum number of executions to return
            
        Returns:
            List of execution information
        """
        try:
            executions = []
            
            request = executions_v1.ListExecutionsRequest(
                parent=self.workflow_path,
                page_size=page_size
            )
            
            page_result = self.executions_client.list_executions(request=request)
            
            for execution in page_result:
                execution_info = {
                    "name": execution.name,
                    "state": execution.state.name,
                    "start_time": execution.start_time.ToDatetime() if execution.start_time else None,
                    "end_time": execution.end_time.ToDatetime() if execution.end_time else None
                }
                executions.append(execution_info)
            
            return executions
            
        except Exception as e:
            logger.error(f"❌ Failed to list workflow executions: {e}")
            return []
    
    def _calculate_parallel_workers(self, config_name: str) -> int:
        """
        Calculate optimal number of parallel workers based on test configuration.
        
        Args:
            config_name: Name of the test configuration
            
        Returns:
            Number of parallel workers needed
        """
        try:
            # This will be called from test_manager, so we need to load config
            from .config_generator import ABTestConfigGenerator
            
            config_dir = os.path.join(os.path.dirname(__file__), 'configs')
            generator = ABTestConfigGenerator(config_dir)
            config_data = generator.load_config(config_name)
            
            estimated_minutes = self.estimate_test_duration(config_data)
            
            # Calculate workers needed to finish under 45 minutes
            target_minutes = 45
            min_workers = 2  # Always use at least 2 workers for parallelism
            
            if estimated_minutes <= target_minutes:
                return min_workers
            
            # Calculate workers needed, with a reasonable upper limit
            workers_needed = math.ceil(estimated_minutes / target_minutes)
            max_workers = 8  # Reasonable upper limit to avoid resource exhaustion
            
            return min(max(workers_needed, min_workers), max_workers)
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate parallel workers: {e}")
            return 2  # Default fallback
    
    def estimate_test_duration(self, config_data: Dict[str, Any]) -> int:
        """
        Estimate how long a test will take to run in minutes.
        
        Args:
            config_data: Test configuration dictionary
            
        Returns:
            Estimated duration in minutes
        """
        try:
            # Calculate total test combinations
            models = len(config_data.get("models_to_test", []))
            user_types = len(config_data.get("user_types", ["business"]))
            think_modes = len(config_data.get("think_mode_options", [False]))
            questions = len(config_data.get("questions", []))
            iterations = config_data.get("iterations", 1)
            
            # For comprehensive tests, use questions_per_combination instead of all questions
            if config_data.get("test_type") == "comprehensive":
                questions_per_combo = config_data.get("questions_per_combination", 3)
                total_tests = models * user_types * think_modes * questions_per_combo * iterations
            else:
                total_tests = models * user_types * think_modes * questions * iterations
            
            # Estimate time per test (including delays)
            avg_response_time = 30  # seconds
            delay_between_tests = config_data.get("delay_between_questions", 5)
            time_per_test = avg_response_time + delay_between_tests
            
            # Total time in minutes
            total_minutes = (total_tests * time_per_test) / 60
            
            # Add 20% buffer for overhead
            estimated_minutes = int(total_minutes * 1.2)
            
            logger.info(f"📊 Estimated test duration: {estimated_minutes} minutes for {total_tests} tests")
            
            return max(estimated_minutes, 5)  # Minimum 5 minutes
            
        except Exception as e:
            logger.error(f"❌ Failed to estimate test duration: {e}")
            return 60  # Default to 1 hour if estimation fails
    
    def should_use_workflows(self, config_data: Dict[str, Any]) -> bool:
        """
        Determine if a test should use Cloud Workflows based on estimated duration.
        
        Args:
            config_data: Test configuration dictionary
            
        Returns:
            True if test should use Cloud Workflows
        """
        estimated_minutes = self.estimate_test_duration(config_data)
        
        # Use Cloud Workflows for tests estimated to take longer than 30 minutes
        # or tests that need parallel processing
        return estimated_minutes > 30 or len(config_data.get("models_to_test", [])) > 2
    
    def create_test_batches(self, config_data: Dict[str, Any], parallel_workers: int) -> List[Dict[str, Any]]:
        """
        Split test configuration into parallel batches for workers.
        
        Args:
            config_data: Test configuration dictionary
            parallel_workers: Number of parallel workers
            
        Returns:
            List of test batches for each worker
        """
        try:
            # Generate all test combinations
            models = config_data.get("models_to_test", [])
            user_types = config_data.get("user_types", ["business"])
            think_modes = config_data.get("think_mode_options", [False])
            questions = config_data.get("questions", [])
            iterations = config_data.get("iterations", 1)
            
            # Optimize for large test configurations to prevent timeouts
            questions_per_test = config_data.get("questions_per_test", len(questions))
            delay_between_questions = config_data.get("delay_between_questions", 5)
            
            # Cap questions per test to prevent timeouts (max 15 minutes per worker)
            # Each question takes ~5-8 seconds + delay, so limit to prevent > 25 minute batches
            max_questions_per_batch = 20
            if questions_per_test > max_questions_per_batch:
                logger.warning(f"⚠️ Limiting questions per test from {questions_per_test} to {max_questions_per_batch} to prevent timeouts")
                questions_per_test = max_questions_per_batch
            
            # Reduce delay for large test suites
            if len(questions) * len(models) * len(user_types) > 30:
                delay_between_questions = min(delay_between_questions, 2)
                logger.info(f"📊 Reduced delay to {delay_between_questions}s for large test suite")
            
            # For comprehensive tests, sample questions per combination
            if config_data.get("test_type") == "comprehensive":
                questions_per_combo = config_data.get("questions_per_combination", 3)
                import random
                selected_questions = random.sample(questions, min(questions_per_combo, len(questions)))
            else:
                # Limit questions for category-specific tests to prevent timeouts
                if config_data.get("test_type") == "category_specific":
                    # Use first N questions up to the limit
                    selected_questions = questions[:min(questions_per_test, len(questions))]
                else:
                    selected_questions = questions
            
            # Generate all combinations
            combinations = []
            for model in models:
                for user_type in user_types:
                    for think_mode in think_modes:
                        # Skip think mode for incompatible models
                        if think_mode and not self._supports_think_mode(model):
                            continue
                        
                        for question in selected_questions:
                            for iteration in range(iterations):
                                combinations.append({
                                    "model": model,
                                    "user_type": user_type,
                                    "think_mode": think_mode,
                                    "question": question,
                                    "iteration": iteration,
                                    "delay_between_tests": delay_between_questions,
                                    "timeout": 60.0
                                })
            
            # Increase workers for very large test suites
            estimated_time_per_test = 8 + delay_between_questions  # seconds
            total_estimated_time = len(combinations) * estimated_time_per_test
            max_batch_time = 20 * 60  # 20 minutes max per batch
            
            if total_estimated_time / parallel_workers > max_batch_time:
                optimal_workers = math.ceil(total_estimated_time / max_batch_time)
                if optimal_workers > parallel_workers:
                    parallel_workers = min(optimal_workers, 6)  # Cap at 6 workers
                    logger.info(f"📊 Increased workers to {parallel_workers} to prevent timeouts")
            
            # Split combinations into batches
            batch_size = math.ceil(len(combinations) / parallel_workers)
            batches = []
            
            for i in range(parallel_workers):
                start_idx = i * batch_size
                end_idx = min((i + 1) * batch_size, len(combinations))
                
                if start_idx < len(combinations):
                    batch = {
                        "batch_id": f"batch_{i}",
                        "worker_index": i,
                        "tests": combinations[start_idx:end_idx],
                        "batch_size": end_idx - start_idx
                    }
                    batches.append(batch)
            
            total_tests = len(combinations)
            avg_batch_size = total_tests / len(batches) if batches else 0
            estimated_duration = (avg_batch_size * estimated_time_per_test) / 60  # minutes
            
            logger.info(f"📊 Created {len(batches)} test batches with ~{avg_batch_size:.1f} tests each")
            logger.info(f"⏱️ Estimated duration per batch: ~{estimated_duration:.1f} minutes")
            
            return batches
            
        except Exception as e:
            logger.error(f"❌ Failed to create test batches: {e}")
            return []
    
    def _supports_think_mode(self, model: str) -> bool:
        """Check if model supports think mode."""
        think_mode_models = [
            "gemini-2.5-pro-preview-05-06",
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ]
        return any(tm in model for tm in think_mode_models)