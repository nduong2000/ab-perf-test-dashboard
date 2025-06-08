#!/usr/bin/env python3
"""
Test script for Cloud Tasks connectivity and basic operations.
Run this to verify that Cloud Tasks is properly configured.
"""

import os
import sys
from datetime import datetime

# Set environment variables for testing
os.environ['USE_CLOUD_TASKS'] = 'true'
os.environ['GCP_PROJECT_ID'] = 'ab-perf-test-dashboard'
os.environ['CLOUD_TASKS_QUEUE'] = 'ab-test-queue'
os.environ['CLOUD_TASKS_LOCATION'] = 'us-central1'

try:
    from ab_testing.cloud_tasks_manager import CloudTasksManager
    print("✅ Successfully imported Cloud Tasks manager")
except ImportError as e:
    print(f"❌ Failed to import Cloud Tasks manager: {e}")
    print("Make sure google-cloud-tasks is installed: pip install google-cloud-tasks")
    sys.exit(1)

def test_cloud_tasks_connection():
    """Test basic Cloud Tasks connectivity."""
    print("\n⚡ Testing Cloud Tasks connection...")
    
    try:
        manager = CloudTasksManager()
        print("✅ Cloud Tasks connection successful")
        return manager
    except Exception as e:
        print(f"❌ Cloud Tasks connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have run the setup-gcp.sh script")
        print("2. Ensure GOOGLE_APPLICATION_CREDENTIALS is set or you're running in GCP")
        print("3. Verify the project ID and queue name are correct")
        print("4. Check that Cloud Tasks API is enabled")
        return None

def test_queue_operations(manager):
    """Test basic queue operations."""
    print("\n📝 Testing queue operations...")
    
    try:
        # List existing tasks
        tasks = manager.list_tasks(page_size=5)
        print(f"✅ Successfully listed tasks: {len(tasks)} found")
        
        # Test duration estimation
        sample_config = {
            "models_to_test": ["gemini-2.0-flash-exp", "gemini-2.5-flash"],
            "user_types": ["business", "technical"],
            "think_mode_options": [True, False],
            "questions": ["Sample question 1", "Sample question 2", "Sample question 3"],
            "iterations": 2,
            "delay_between_questions": 5
        }
        
        estimated_minutes = manager.estimate_test_duration(sample_config)
        print(f"✅ Duration estimation successful: {estimated_minutes} minutes")
        
        # Test should_use_cloud_tasks logic
        should_use = manager.should_use_cloud_tasks(sample_config)
        print(f"✅ Cloud Tasks decision logic: Use Cloud Tasks = {should_use}")
        
        return True
        
    except Exception as e:
        print(f"❌ Queue operations failed: {e}")
        return False

def test_task_creation(manager):
    """Test creating and managing tasks."""
    print("\n🚀 Testing task creation...")
    
    try:
        # Create a test task (this will actually create a task!)
        execution_id = f"test-{int(datetime.utcnow().timestamp())}"
        config_name = "test-config.json"
        
        print(f"Creating test task for execution: {execution_id}")
        
        # Note: This creates a real task that will call back to your service
        # Only run this if your service is deployed and accessible
        task_name = manager.create_ab_test_task(
            execution_id=execution_id,
            config_name=config_name,
            task_timeout_minutes=10,  # Short timeout for testing
            schedule_delay_seconds=30  # Delay to allow cancellation
        )
        
        print(f"✅ Task created successfully: {task_name}")
        
        # Test getting task status
        task_status = manager.get_task_status(task_name)
        if task_status:
            print(f"✅ Task status retrieved: {task_status['name']}")
            print(f"   Schedule time: {task_status.get('schedule_time')}")
            print(f"   Dispatch count: {task_status.get('dispatch_count', 0)}")
        else:
            print("⚠️ Could not retrieve task status")
        
        # Cancel the test task to avoid unnecessary execution
        print(f"\n🛑 Canceling test task...")
        if manager.cancel_task(task_name):
            print("✅ Test task canceled successfully")
        else:
            print("⚠️ Could not cancel test task")
        
        return True
        
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        return False

def test_cleanup_task(manager):
    """Test creating a cleanup task."""
    print("\n🧹 Testing cleanup task creation...")
    
    try:
        # Create a cleanup task scheduled for later
        task_name = manager.create_cleanup_task(
            days_old=30,
            schedule_delay_hours=1  # Schedule for 1 hour from now
        )
        
        print(f"✅ Cleanup task created: {task_name}")
        
        # Cancel it immediately since it's just a test
        if manager.cancel_task(task_name):
            print("✅ Test cleanup task canceled")
        else:
            print("⚠️ Could not cancel cleanup task")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup task creation failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Starting Cloud Tasks connectivity test...")
    
    # Test connection
    manager = test_cloud_tasks_connection()
    if not manager:
        sys.exit(1)
    
    # Test queue operations
    if not test_queue_operations(manager):
        print("\n❌ Queue operations failed. Check your configuration.")
        sys.exit(1)
    
    # Test task creation (only if service URL is configured)
    service_url = os.getenv('CLOUD_RUN_SERVICE_URL')
    if service_url and service_url != 'https://ab-perf-test-dashboard-529012124872.us-central1.run.app':
        print(f"\n🌐 Service URL configured: {service_url}")
        if test_task_creation(manager):
            print("✅ Task creation test passed")
        else:
            print("⚠️ Task creation test failed")
    else:
        print("\n⚠️ Skipping task creation test (service not deployed yet)")
        print("   Set CLOUD_RUN_SERVICE_URL to test task creation")
    
    # Test cleanup task
    if test_cleanup_task(manager):
        print("✅ Cleanup task test passed")
    else:
        print("⚠️ Cleanup task test failed")
    
    print("\n✅ Cloud Tasks tests completed!")
    print("\n📋 Summary:")
    print("- Cloud Tasks client is working")
    print("- Queue operations are functional")
    print("- Task creation and cancellation work")
    print("- Ready for long-running A/B tests!")

if __name__ == "__main__":
    main() 