"""
Cloud Tasks Manager
Handles long-running A/B test executions using Google Cloud Tasks for operations that exceed Cloud Run timeout limits.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

logger = logging.getLogger(__name__)

class CloudTasksManager:
    """Manages long-running A/B test executions using Google Cloud Tasks."""
    
    def __init__(self, 
                 project_id: str = None,
                 location: str = None,
                 queue_name: str = None,
                 service_url: str = None):
        """Initialize Cloud Tasks client."""
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID', 'ab-perf-test-dashboard')
        self.location = location or os.getenv('CLOUD_TASKS_LOCATION', 'us-central1')
        self.queue_name = queue_name or os.getenv('CLOUD_TASKS_QUEUE', 'ab-test-queue')
        self.service_url = service_url or os.getenv('CLOUD_RUN_SERVICE_URL', 'https://ab-perf-test-dashboard-529012124872.us-central1.run.app')
        
        try:
            self.client = tasks_v2.CloudTasksClient()
            self.parent = self.client.queue_path(self.project_id, self.location, self.queue_name)
            logger.info(f"⚡ Connected to Cloud Tasks queue: {self.queue_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Cloud Tasks: {e}")
            raise
    
    def create_ab_test_task(self, 
                           execution_id: str, 
                           config_name: str,
                           task_timeout_minutes: int = 120,
                           schedule_delay_seconds: int = 0) -> str:
        """
        Create a Cloud Task for running an A/B test.
        
        Args:
            execution_id: Unique identifier for the test execution
            config_name: Name of the test configuration to run
            task_timeout_minutes: Maximum time for task execution (default 2 hours)
            schedule_delay_seconds: Delay before starting the task
            
        Returns:
            Task name/ID
        """
        try:
            # Prepare the task payload
            task_payload = {
                "execution_id": execution_id,
                "config_name": config_name,
                "started_at": datetime.utcnow().isoformat(),
                "timeout_minutes": task_timeout_minutes
            }
            
            # Create HTTP request for the task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{self.service_url}/api/tasks/execute-ab-test",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-CloudTasks-TaskName": f"ab-test-{execution_id}",
                        "X-CloudTasks-QueueName": self.queue_name
                    },
                    "body": json.dumps(task_payload).encode()
                },
                "name": f"{self.parent}/tasks/ab-test-{execution_id}-{int(datetime.utcnow().timestamp())}"
            }
            
            # Set task timeout
            if task_timeout_minutes > 0:
                timeout = timestamp_pb2.Timestamp()
                timeout.FromDatetime(datetime.utcnow() + timedelta(minutes=task_timeout_minutes))
                task["dispatch_deadline"] = timeout
            
            # Set schedule time if delay is specified
            if schedule_delay_seconds > 0:
                schedule_time = timestamp_pb2.Timestamp()
                schedule_time.FromDatetime(datetime.utcnow() + timedelta(seconds=schedule_delay_seconds))
                task["schedule_time"] = schedule_time
            
            # Create the task
            response = self.client.create_task(
                request={"parent": self.parent, "task": task}
            )
            
            task_name = response.name
            logger.info(f"⚡ Created Cloud Task for A/B test: {execution_id} -> {task_name}")
            
            return task_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create Cloud Task for execution {execution_id}: {e}")
            raise
    
    def create_cleanup_task(self, days_old: int = 30, schedule_delay_hours: int = 24) -> str:
        """
        Create a task for cleaning up old test data.
        
        Args:
            days_old: Delete data older than this many days
            schedule_delay_hours: Delay before running cleanup
            
        Returns:
            Task name/ID
        """
        try:
            task_payload = {
                "operation": "cleanup",
                "days_old": days_old,
                "scheduled_at": datetime.utcnow().isoformat()
            }
            
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{self.service_url}/api/tasks/cleanup",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-CloudTasks-TaskName": f"cleanup-{int(datetime.utcnow().timestamp())}",
                        "X-CloudTasks-QueueName": self.queue_name
                    },
                    "body": json.dumps(task_payload).encode()
                }
            }
            
            # Schedule for later execution
            if schedule_delay_hours > 0:
                schedule_time = timestamp_pb2.Timestamp()
                schedule_time.FromDatetime(datetime.utcnow() + timedelta(hours=schedule_delay_hours))
                task["schedule_time"] = schedule_time
            
            response = self.client.create_task(
                request={"parent": self.parent, "task": task}
            )
            
            logger.info(f"🧹 Scheduled cleanup task: {response.name}")
            return response.name
            
        except Exception as e:
            logger.error(f"❌ Failed to create cleanup task: {e}")
            raise
    
    def cancel_task(self, task_name: str) -> bool:
        """
        Cancel a running or scheduled task.
        
        Args:
            task_name: Full task name/path
            
        Returns:
            True if successfully cancelled
        """
        try:
            self.client.delete_task(name=task_name)
            logger.info(f"🛑 Cancelled task: {task_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel task {task_name}: {e}")
            return False
    
    def get_task_status(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status information about a task.
        
        Args:
            task_name: Full task name/path
            
        Returns:
            Task status information or None if not found
        """
        try:
            task = self.client.get_task(name=task_name)
            
            status_info = {
                "name": task.name,
                "create_time": task.create_time.ToDatetime() if task.create_time else None,
                "schedule_time": task.schedule_time.ToDatetime() if task.schedule_time else None,
                "dispatch_count": task.dispatch_count,
                "response_count": task.response_count,
                "first_attempt": task.first_attempt.ToDict() if task.first_attempt else None,
                "last_attempt": task.last_attempt.ToDict() if task.last_attempt else None,
                "view": task.view
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get task status {task_name}: {e}")
            return None
    
    def list_tasks(self, page_size: int = 100) -> list:
        """
        List tasks in the queue.
        
        Args:
            page_size: Maximum number of tasks to return
            
        Returns:
            List of task information
        """
        try:
            tasks = []
            
            request = tasks_v2.ListTasksRequest(
                parent=self.parent,
                page_size=page_size
            )
            
            page_result = self.client.list_tasks(request=request)
            
            for task in page_result:
                task_info = {
                    "name": task.name,
                    "create_time": task.create_time.ToDatetime() if task.create_time else None,
                    "schedule_time": task.schedule_time.ToDatetime() if task.schedule_time else None,
                    "dispatch_count": task.dispatch_count,
                    "response_count": task.response_count
                }
                tasks.append(task_info)
            
            return tasks
            
        except Exception as e:
            logger.error(f"❌ Failed to list tasks: {e}")
            return []
    
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
    
    def should_use_cloud_tasks(self, config_data: Dict[str, Any]) -> bool:
        """
        Determine if a test should use Cloud Tasks based on estimated duration.
        
        Args:
            config_data: Test configuration dictionary
            
        Returns:
            True if test should use Cloud Tasks
        """
        estimated_minutes = self.estimate_test_duration(config_data)
        
        # Use Cloud Tasks for tests estimated to take longer than 45 minutes
        # This leaves buffer before Cloud Run's 60-minute timeout
        return estimated_minutes > 45 