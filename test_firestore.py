#!/usr/bin/env python3
"""
Test script for Firestore connectivity and basic operations.
Run this to verify that Firestore is properly configured.
"""

import os
import sys
from datetime import datetime

# Set environment variables for testing
os.environ['USE_FIRESTORE'] = 'true'
os.environ['GCP_PROJECT_ID'] = 'ab-perf-test-dashboard'

try:
    from ab_testing.firestore_manager import FirestoreManager, TestExecution
    print("✅ Successfully imported Firestore manager")
except ImportError as e:
    print(f"❌ Failed to import Firestore manager: {e}")
    print("Make sure google-cloud-firestore is installed: pip install google-cloud-firestore")
    sys.exit(1)

def test_firestore_connection():
    """Test basic Firestore connectivity."""
    print("\n🔥 Testing Firestore connection...")
    
    try:
        manager = FirestoreManager()
        print("✅ Firestore connection successful")
        return manager
    except Exception as e:
        print(f"❌ Firestore connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have run the setup-gcp.sh script")
        print("2. Ensure GOOGLE_APPLICATION_CREDENTIALS is set or you're running in GCP")
        print("3. Verify the project ID is correct")
        return None

def test_basic_operations(manager):
    """Test basic CRUD operations."""
    print("\n📝 Testing basic operations...")
    
    # Create a test execution
    test_execution = TestExecution(
        execution_id="test-123",
        config_name="test-config",
        status="pending",
        total_tests=10,
        created_at=datetime.utcnow().isoformat()
    )
    
    try:
        # Save execution
        manager.save_execution(test_execution)
        print("✅ Save operation successful")
        
        # Retrieve execution
        retrieved = manager.get_execution("test-123")
        if retrieved and retrieved.execution_id == "test-123":
            print("✅ Retrieve operation successful")
        else:
            print("❌ Retrieve operation failed")
            return False
        
        # Update execution
        manager.update_execution_status("test-123", "completed")
        updated = manager.get_execution("test-123")
        if updated and updated.status == "completed":
            print("✅ Update operation successful")
        else:
            print("❌ Update operation failed")
            return False
        
        # List executions
        executions = manager.list_executions(5)
        if executions and len(executions) > 0:
            print("✅ List operation successful")
        else:
            print("❌ List operation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Operations failed: {e}")
        return False

def cleanup_test_data(manager):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    try:
        # Note: In a real cleanup, you'd delete the test document
        # For now, we'll just update it to mark as cleaned
        manager.update_execution_status("test-123", "cleaned")
        print("✅ Cleanup successful")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

def main():
    """Main test function."""
    print("🚀 Starting Firestore connectivity test...")
    
    # Test connection
    manager = test_firestore_connection()
    if not manager:
        sys.exit(1)
    
    # Test operations
    if test_basic_operations(manager):
        print("\n✅ All tests passed! Firestore is ready for use.")
        cleanup_test_data(manager)
    else:
        print("\n❌ Some tests failed. Check your Firestore configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main() 