"""
A/B Test Manager
Manages the lifecycle of A/B tests including scheduling, execution, monitoring, and analysis.
"""

import json
import sqlite3
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, Future
import uuid

from .decorators import ABTestRunner, TestResult, TestConfiguration
from .config_generator import ABTestConfigGenerator

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

class ABTestManager:
    """Manages A/B test lifecycle and execution."""
    
    def __init__(self, 
                 database_path: str = "src/llmops/ab_testing/test_manager.db",
                 config_dir: str = "src/llmops/ab_testing/configs",
                 results_dir: str = "src/llmops/ab_testing/results",
                 base_url: str = "https://aetraggraph-529012124872.us-central1.run.app"):
        
        self.database_path = Path(database_path)
        self.config_dir = Path(config_dir)
        self.results_dir = Path(results_dir)
        self.base_url = base_url
        
        # Create directories
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Runtime tracking
        self.active_executions: Dict[str, Future] = {}
        self.active_runners: Dict[str, ABTestRunner] = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.lock = threading.Lock()
        
        # Initialize config generator
        self.config_generator = ABTestConfigGenerator(str(self.config_dir))
    
    def _init_database(self):
        """Initialize SQLite database for test tracking."""
        with sqlite3.connect(self.database_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_executions (
                    execution_id TEXT PRIMARY KEY,
                    config_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    total_tests INTEGER DEFAULT 0,
                    completed_tests INTEGER DEFAULT 0,
                    failed_tests INTEGER DEFAULT 0,
                    results_file TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results_summary (
                    execution_id TEXT,
                    model TEXT,
                    user_type TEXT,
                    think_mode BOOLEAN,
                    avg_response_time REAL,
                    success_rate REAL,
                    total_tests INTEGER,
                    FOREIGN KEY (execution_id) REFERENCES test_executions (execution_id)
                )
            """)
            
            conn.commit()
    
    def create_test_configuration(self, 
                                config_type: str,
                                name: str = None,
                                **kwargs) -> str:
        """Create a new test configuration."""
        
        if config_type == "model_comparison":
            config = self.config_generator.generate_model_comparison_config()
        elif config_type == "think_mode":
            config = self.config_generator.generate_think_mode_config()
        elif config_type == "user_type":
            config = self.config_generator.generate_user_type_config()
        elif config_type == "comprehensive":
            config = self.config_generator.generate_comprehensive_config()
        elif config_type == "category_specific":
            category = kwargs.get("category", "claims_processing")
            config = self.config_generator.generate_category_specific_config(category)
        else:
            raise ValueError(f"Unknown config type: {config_type}")
        
        # Override name if provided
        if name:
            config["name"] = name
        
        # Override any other parameters
        config.update(kwargs)
        
        # Save configuration
        filename = self.config_generator.save_config(config)
        
        logger.info(f"📋 Created test configuration: {config['name']} -> {filename}")
        return filename
    
    def list_configurations(self) -> List[Dict[str, Any]]:
        """List all available test configurations."""
        configs = []
        
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                configs.append({
                    "filename": config_file.name,
                    "name": config.get("name", "Unknown"),
                    "description": config.get("description", "No description"),
                    "test_type": config.get("test_type", "unknown"),
                    "created_at": config.get("created_at", "Unknown"),
                    "questions_count": len(config.get("questions", [])),
                    "models_count": len(config.get("models_to_test", [])),
                    "duration_minutes": config.get("test_duration_minutes", 60)
                })
                
            except Exception as e:
                logger.error(f"Error reading config {config_file}: {e}")
        
        return sorted(configs, key=lambda x: x["created_at"], reverse=True)
    
    def load_configuration(self, config_name: str) -> Dict[str, Any]:
        """Load a specific configuration."""
        return self.config_generator.load_config(config_name)
    
    def start_test(self, config_name: str) -> str:
        """Start a new test execution."""
        execution_id = str(uuid.uuid4())
        
        try:
            # Load configuration
            config_data = self.load_configuration(config_name)
            
            # Create test configuration object
            test_config = TestConfiguration(
                name=config_data["name"],
                description=config_data["description"],
                models=config_data.get("models_to_test", []),
                user_types=config_data.get("user_types", ["business"]),
                think_mode_options=config_data.get("think_mode_options", [False]),
                questions=config_data["questions"],
                iterations=config_data.get("iterations", 1),
                delay_between_tests=config_data.get("delay_between_questions", 5),
                timeout=60.0
            )
            
            # Create test execution record
            execution = TestExecution(
                execution_id=execution_id,
                config_name=config_name,
                status="pending",
                total_tests=len(test_config.models) * len(test_config.user_types) * 
                           len(test_config.think_mode_options) * len(test_config.questions) * 
                           test_config.iterations
            )
            
            # Save to database
            self._save_execution(execution)
            
            # Start test in background
            future = self.executor.submit(self._run_test_execution, execution_id, test_config)
            
            with self.lock:
                self.active_executions[execution_id] = future
            
            logger.info(f"🚀 Started test execution: {execution_id} for config: {config_name}")
            return execution_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start test: {str(e)}")
            raise
    
    def stop_test(self, execution_id: str) -> bool:
        """Stop a running test execution."""
        with self.lock:
            if execution_id in self.active_runners:
                runner = self.active_runners[execution_id]
                runner.stop_test_suite()
                
                # Update status
                self._update_execution_status(execution_id, "stopped")
                
                logger.info(f"🛑 Stopped test execution: {execution_id}")
                return True
            else:
                logger.warning(f"⚠️ Test execution not found or not running: {execution_id}")
                return False
    
    def get_test_status(self, execution_id: str) -> Optional[TestExecution]:
        """Get the status of a test execution."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM test_executions WHERE execution_id = ?
            """, (execution_id,))
            
            row = cursor.fetchone()
            if row:
                return TestExecution(
                    execution_id=row[0],
                    config_name=row[1],
                    status=row[2],
                    start_time=row[3],
                    end_time=row[4],
                    total_tests=row[5],
                    completed_tests=row[6],
                    failed_tests=row[7],
                    results_file=row[8],
                    error_message=row[9]
                )
        
        return None
    
    def list_test_executions(self, limit: int = 20) -> List[TestExecution]:
        """List recent test executions."""
        executions = []
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM test_executions 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            for row in cursor.fetchall():
                executions.append(TestExecution(
                    execution_id=row[0],
                    config_name=row[1],
                    status=row[2],
                    start_time=row[3],
                    end_time=row[4],
                    total_tests=row[5],
                    completed_tests=row[6],
                    failed_tests=row[7],
                    results_file=row[8],
                    error_message=row[9]
                ))
        
        return executions
    
    def get_test_results(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed test results for an execution."""
        execution = self.get_test_status(execution_id)
        
        if not execution or not execution.results_file:
            return None
        
        results_path = self.results_dir / execution.results_file
        
        if not results_path.exists():
            return None
        
        try:
            with open(results_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            return None
    
    def analyze_test_results(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Analyze test results and provide insights."""
        results_data = self.get_test_results(execution_id)
        
        if not results_data:
            return None
        
        results = results_data.get("results", [])
        
        if not results:
            return {"error": "No test results found"}
        
        # Group results by different dimensions
        by_model = {}
        by_user_type = {}
        by_think_mode = {}
        
        successful_results = [r for r in results if r.get("success", False)]
        
        for result in successful_results:
            model = result.get("model", "unknown")
            user_type = result.get("user_type", "unknown")
            think_mode = result.get("think_mode", False)
            response_time = result.get("response_time", 0)
            
            # Group by model
            if model not in by_model:
                by_model[model] = {"times": [], "count": 0}
            by_model[model]["times"].append(response_time)
            by_model[model]["count"] += 1
            
            # Group by user type
            if user_type not in by_user_type:
                by_user_type[user_type] = {"times": [], "count": 0}
            by_user_type[user_type]["times"].append(response_time)
            by_user_type[user_type]["count"] += 1
            
            # Group by think mode
            think_key = "enabled" if think_mode else "disabled"
            if think_key not in by_think_mode:
                by_think_mode[think_key] = {"times": [], "count": 0}
            by_think_mode[think_key]["times"].append(response_time)
            by_think_mode[think_key]["count"] += 1
        
        # Calculate statistics
        def calc_stats(data):
            if not data["times"]:
                return {"avg": 0, "min": 0, "max": 0, "count": 0}
            times = data["times"]
            return {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(times)
            }
        
        analysis = {
            "execution_id": execution_id,
            "total_tests": len(results),
            "successful_tests": len(successful_results),
            "success_rate": len(successful_results) / len(results) * 100 if results else 0,
            "by_model": {model: calc_stats(data) for model, data in by_model.items()},
            "by_user_type": {ut: calc_stats(data) for ut, data in by_user_type.items()},
            "by_think_mode": {tm: calc_stats(data) for tm, data in by_think_mode.items()},
            "recommendations": self._generate_recommendations(by_model, by_user_type, by_think_mode)
        }
        
        return analysis
    
    def _generate_recommendations(self, by_model, by_user_type, by_think_mode) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Find best performing model
        if by_model:
            best_model = min(by_model.items(), key=lambda x: x[1]["times"] and sum(x[1]["times"])/len(x[1]["times"]) or float('inf'))
            if best_model[1]["times"]:
                recommendations.append(f"🏆 Best performing model: {best_model[0]} (avg: {best_model[1]['times'] and sum(best_model[1]['times'])/len(best_model[1]['times']):.2f}s)")
        
        # Compare user types
        if len(by_user_type) > 1:
            user_times = {ut: sum(data["times"])/len(data["times"]) if data["times"] else 0 for ut, data in by_user_type.items()}
            best_user_type = min(user_times.items(), key=lambda x: x[1])
            recommendations.append(f"👤 Fastest user type: {best_user_type[0]} (avg: {best_user_type[1]:.2f}s)")
        
        # Think mode analysis
        if len(by_think_mode) > 1:
            enabled_avg = sum(by_think_mode.get("enabled", {}).get("times", [])) / len(by_think_mode.get("enabled", {}).get("times", [1])) if by_think_mode.get("enabled", {}).get("times") else 0
            disabled_avg = sum(by_think_mode.get("disabled", {}).get("times", [])) / len(by_think_mode.get("disabled", {}).get("times", [1])) if by_think_mode.get("disabled", {}).get("times") else 0
            
            if enabled_avg > 0 and disabled_avg > 0:
                if enabled_avg < disabled_avg:
                    recommendations.append(f"🧠 Think mode shows better performance (avg: {enabled_avg:.2f}s vs {disabled_avg:.2f}s)")
                else:
                    recommendations.append(f"⚡ Regular mode is faster (avg: {disabled_avg:.2f}s vs {enabled_avg:.2f}s)")
        
        return recommendations
    
    def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Cleanup old test executions and results."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            # Get old executions
            cursor.execute("""
                SELECT execution_id, results_file FROM test_executions 
                WHERE created_at < ?
            """, (cutoff_date.isoformat(),))
            
            old_executions = cursor.fetchall()
            
            # Delete result files
            for execution_id, results_file in old_executions:
                if results_file:
                    results_path = self.results_dir / results_file
                    if results_path.exists():
                        results_path.unlink()
            
            # Delete database records
            cursor.execute("DELETE FROM test_results_summary WHERE execution_id IN (SELECT execution_id FROM test_executions WHERE created_at < ?)", (cutoff_date.isoformat(),))
            cursor.execute("DELETE FROM test_executions WHERE created_at < ?", (cutoff_date.isoformat(),))
            
            conn.commit()
            
            logger.info(f"🧹 Cleaned up {len(old_executions)} old test executions")
            return len(old_executions)
    
    def _run_test_execution(self, execution_id: str, test_config: TestConfiguration):
        """Run a test execution (called in background thread)."""
        try:
            # Update status to running
            self._update_execution_status(execution_id, "running")
            
            # Create results filename
            results_filename = f"results_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            results_path = self.results_dir / results_filename
            
            # Create test runner
            runner = ABTestRunner(base_url=self.base_url, results_file=str(results_path))
            
            with self.lock:
                self.active_runners[execution_id] = runner
            
            # Run tests
            results = runner.run_test_suite(test_config)
            
            # Update execution with results
            successful_tests = len([r for r in results if r.success])
            failed_tests = len([r for r in results if not r.success])
            
            with sqlite3.connect(self.database_path) as conn:
                conn.execute("""
                    UPDATE test_executions 
                    SET status = ?, end_time = ?, completed_tests = ?, 
                        failed_tests = ?, results_file = ?
                    WHERE execution_id = ?
                """, ("completed", datetime.now().isoformat(), successful_tests, 
                      failed_tests, results_filename, execution_id))
                conn.commit()
            
            # Store summary results
            self._store_result_summary(execution_id, results)
            
            logger.info(f"✅ Test execution completed: {execution_id}")
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {execution_id} - {str(e)}")
            self._update_execution_status(execution_id, "failed", str(e))
        
        finally:
            # Cleanup
            with self.lock:
                self.active_executions.pop(execution_id, None)
                self.active_runners.pop(execution_id, None)
    
    def _save_execution(self, execution: TestExecution):
        """Save test execution to database."""
        with sqlite3.connect(self.database_path) as conn:
            conn.execute("""
                INSERT INTO test_executions 
                (execution_id, config_name, status, start_time, total_tests, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (execution.execution_id, execution.config_name, execution.status,
                  datetime.now().isoformat(), execution.total_tests, datetime.now().isoformat()))
            conn.commit()
    
    def _update_execution_status(self, execution_id: str, status: str, error_message: str = None):
        """Update execution status in database."""
        with sqlite3.connect(self.database_path) as conn:
            if error_message:
                conn.execute("""
                    UPDATE test_executions 
                    SET status = ?, error_message = ?
                    WHERE execution_id = ?
                """, (status, error_message, execution_id))
            else:
                conn.execute("""
                    UPDATE test_executions 
                    SET status = ?
                    WHERE execution_id = ?
                """, (status, execution_id))
            conn.commit()
    
    def _store_result_summary(self, execution_id: str, results: List[TestResult]):
        """Store summary statistics in database."""
        # Group results by model/user_type/think_mode
        summary_data = {}
        
        for result in results:
            key = (result.model, result.user_type, result.think_mode)
            
            if key not in summary_data:
                summary_data[key] = {
                    "response_times": [],
                    "success_count": 0,
                    "total_count": 0
                }
            
            summary_data[key]["total_count"] += 1
            if result.success:
                summary_data[key]["success_count"] += 1
                summary_data[key]["response_times"].append(result.response_time)
        
        # Insert summary data
        with sqlite3.connect(self.database_path) as conn:
            for (model, user_type, think_mode), data in summary_data.items():
                avg_time = sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0
                success_rate = data["success_count"] / data["total_count"] * 100 if data["total_count"] > 0 else 0
                
                conn.execute("""
                    INSERT INTO test_results_summary 
                    (execution_id, model, user_type, think_mode, avg_response_time, success_rate, total_tests)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (execution_id, model, user_type, think_mode, avg_time, success_rate, data["total_count"]))
            
            conn.commit()


if __name__ == "__main__":
    # Example usage
    manager = ABTestManager()
    
    print("🔧 A/B Test Manager initialized")
    
    # Create a sample configuration
    config_path = manager.create_test_configuration("model_comparison", name="sample_model_test")
    print(f"📋 Created configuration: {config_path}")
    
    # List configurations
    configs = manager.list_configurations()
    print(f"📂 Available configurations: {len(configs)}")
    for config in configs[:3]:  # Show first 3
        print(f"   - {config['name']}: {config['description']}") 