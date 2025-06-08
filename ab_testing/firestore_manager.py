"""
Firestore Data Manager
Manages persistent storage of A/B test data using Google Cloud Firestore.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from google.cloud import firestore
from google.api_core.exceptions import NotFound, AlreadyExists

logger = logging.getLogger(__name__)

@dataclass
class TestExecution:
    """Represents a test execution instance."""
    execution_id: str
    config_name: str
    status: str  # "pending", "running", "completed", "failed", "stopped"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_tests: int = 0
    completed_tests: int = 0
    failed_tests: int = 0
    results_file: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class TestResultSummary:
    """Represents a test result summary."""
    execution_id: str
    model: str
    user_type: str
    think_mode: bool
    avg_response_time: float
    success_rate: float
    total_tests: int

class FirestoreManager:
    """Manages A/B test data persistence using Google Cloud Firestore."""
    
    def __init__(self, project_id: str = None):
        """Initialize Firestore client."""
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID', 'ab-perf-test-dashboard')
        
        try:
            self.db = firestore.Client(project=self.project_id)
            logger.info(f"🔥 Connected to Firestore database in project: {self.project_id}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Firestore: {e}")
            raise
        
        # Collection references
        self.executions_ref = self.db.collection('test_executions')
        self.results_ref = self.db.collection('test_results_summary')
        self.configs_ref = self.db.collection('test_configurations')
    
    def save_execution(self, execution: TestExecution) -> None:
        """Save or update a test execution."""
        try:
            if not execution.created_at:
                execution.created_at = datetime.utcnow().isoformat()
            
            doc_data = asdict(execution)
            self.executions_ref.document(execution.execution_id).set(doc_data, merge=True)
            logger.info(f"💾 Saved execution: {execution.execution_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save execution {execution.execution_id}: {e}")
            raise
    
    def get_execution(self, execution_id: str) -> Optional[TestExecution]:
        """Retrieve a test execution by ID."""
        try:
            doc = self.executions_ref.document(execution_id).get()
            if doc.exists:
                data = doc.to_dict()
                return TestExecution(**data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get execution {execution_id}: {e}")
            return None
    
    def update_execution_status(self, execution_id: str, status: str, error_message: str = None) -> None:
        """Update execution status."""
        try:
            update_data = {
                'status': status,
                'end_time': datetime.utcnow().isoformat() if status in ['completed', 'failed', 'stopped'] else None
            }
            
            if error_message:
                update_data['error_message'] = error_message
                
            self.executions_ref.document(execution_id).update(update_data)
            logger.info(f"📝 Updated execution {execution_id} status to: {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update execution {execution_id}: {e}")
            raise
    
    def list_executions(self, limit: int = 20) -> List[TestExecution]:
        """List test executions, most recent first."""
        try:
            docs = (self.executions_ref
                   .order_by('created_at', direction=firestore.Query.DESCENDING)
                   .limit(limit)
                   .stream())
            
            executions = []
            for doc in docs:
                data = doc.to_dict()
                executions.append(TestExecution(**data))
            
            return executions
            
        except Exception as e:
            logger.error(f"❌ Failed to list executions: {e}")
            return []
    
    def save_result_summary(self, execution_id: str, results: List[Any]) -> None:
        """Store test result summaries."""
        try:
            # Process results by model, user_type, and think_mode
            summary_data = {}
            
            for result in results:
                key = f"{result.model}_{result.user_type}_{result.think_mode}"
                
                if key not in summary_data:
                    summary_data[key] = {
                        'execution_id': execution_id,
                        'model': result.model,
                        'user_type': result.user_type,
                        'think_mode': result.think_mode,
                        'response_times': [],
                        'success_count': 0,
                        'total_count': 0
                    }
                
                summary_data[key]['response_times'].append(result.response_time)
                summary_data[key]['total_count'] += 1
                if result.success:
                    summary_data[key]['success_count'] += 1
            
            # Calculate averages and save to Firestore
            batch = self.db.batch()
            
            for key, data in summary_data.items():
                summary = TestResultSummary(
                    execution_id=execution_id,
                    model=data['model'],
                    user_type=data['user_type'],
                    think_mode=data['think_mode'],
                    avg_response_time=sum(data['response_times']) / len(data['response_times']),
                    success_rate=data['success_count'] / data['total_count'],
                    total_tests=data['total_count']
                )
                
                doc_ref = self.results_ref.document(f"{execution_id}_{key}")
                batch.set(doc_ref, asdict(summary))
            
            batch.commit()
            logger.info(f"📊 Saved result summaries for execution: {execution_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save result summaries: {e}")
            raise
    
    def get_result_summaries(self, execution_id: str) -> List[TestResultSummary]:
        """Get result summaries for an execution."""
        try:
            docs = (self.results_ref
                   .where('execution_id', '==', execution_id)
                   .stream())
            
            summaries = []
            for doc in docs:
                data = doc.to_dict()
                summaries.append(TestResultSummary(**data))
            
            return summaries
            
        except Exception as e:
            logger.error(f"❌ Failed to get result summaries: {e}")
            return []
    
    def save_configuration(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """Save a test configuration to Firestore."""
        try:
            config_data['saved_at'] = datetime.utcnow().isoformat()
            self.configs_ref.document(config_name).set(config_data, merge=True)
            logger.info(f"💾 Saved configuration: {config_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save configuration {config_name}: {e}")
            raise
    
    def get_configuration(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get a test configuration from Firestore."""
        try:
            doc = self.configs_ref.document(config_name).get()
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get configuration {config_name}: {e}")
            return None
    
    def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Clean up old test executions."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            # Query old executions
            old_docs = (self.executions_ref
                       .where('created_at', '<', cutoff_iso)
                       .stream())
            
            deleted_count = 0
            batch = self.db.batch()
            
            for doc in old_docs:
                # Delete associated result summaries
                result_docs = (self.results_ref
                              .where('execution_id', '==', doc.id)
                              .stream())
                
                for result_doc in result_docs:
                    batch.delete(result_doc.reference)
                
                # Delete execution
                batch.delete(doc.reference)
                deleted_count += 1
                
                # Commit batch every 500 operations (Firestore limit)
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            if deleted_count % 500 != 0:
                batch.commit()
            
            logger.info(f"🧹 Cleaned up {deleted_count} old executions")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old executions: {e}")
            return 0 