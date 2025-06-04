"""
Decorator-Based A/B Testing Framework
Provides decorators for automatically running A/B tests on graph RAG functions.
"""

import functools
import time
import json
import random
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor
import requests

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Represents a single test result."""
    test_id: str
    timestamp: str
    model: str
    user_type: str
    think_mode: bool
    question: str
    response: str
    response_time: float
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class TestConfiguration:
    """Configuration for A/B test execution."""
    name: str
    description: str
    models: List[str]
    user_types: List[str]
    think_mode_options: List[bool]
    questions: List[str]
    iterations: int = 1
    delay_between_tests: float = 2.0
    timeout: float = 60.0
    collect_full_response: bool = True
    
class ABTestRunner:
    """Core A/B test runner with decorator support."""
    
    def __init__(self, base_url: str = "https://aetraggraph-529012124872.us-central1.run.app", results_file: str = None):
        self.base_url = base_url
        self.results_file = results_file or f"ab_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.results: List[TestResult] = []
        self.is_running = False
        self.lock = threading.Lock()
        
    def _make_request(self, model: str, user_type: str, think_mode: bool, question: str) -> Tuple[Dict, float]:
        """Make a request to the chat API."""
        start_time = time.time()
        
        payload = {
            "message": question,
            "response_style": user_type.title(),
            "session_id": f"ab_test_{datetime.now().timestamp()}",
            "model": model,
            "think_mode": think_mode
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            response_time = time.time() - start_time
            return response.json(), response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            raise Exception(f"Request failed: {str(e)}") from e
    
    def _generate_combinations(self, config: TestConfiguration) -> List[Dict]:
        """Generate all test combinations from configuration."""
        combinations = []
        
        for model in config.models:
            for user_type in config.user_types:
                for think_mode in config.think_mode_options:
                    # Only use think mode with compatible models
                    if think_mode and not self._supports_think_mode(model):
                        continue
                        
                    for question in config.questions:
                        combinations.append({
                            "model": model,
                            "user_type": user_type,
                            "think_mode": think_mode,
                            "question": question
                        })
        
        return combinations
    
    def _supports_think_mode(self, model: str) -> bool:
        """Check if model supports think mode."""
        think_mode_models = [
            "gemini-2.5-pro-preview-05-06",
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ]
        return any(tm in model for tm in think_mode_models)
    
    def run_single_test(self, model: str, user_type: str, think_mode: bool, question: str) -> TestResult:
        """Run a single test and return result."""
        test_id = f"test_{datetime.now().timestamp()}_{random.randint(1000, 9999)}"
        
        try:
            response_data, response_time = self._make_request(model, user_type, think_mode, question)
            
            result = TestResult(
                test_id=test_id,
                timestamp=datetime.now().isoformat(),
                model=model,
                user_type=user_type,
                think_mode=think_mode,
                question=question,
                response=response_data.get("response", ""),
                response_time=response_time,
                success=True,
                metadata=response_data.get("metadata", {})
            )
            
        except Exception as e:
            result = TestResult(
                test_id=test_id,
                timestamp=datetime.now().isoformat(),
                model=model,
                user_type=user_type,
                think_mode=think_mode,
                question=question,
                response="",
                response_time=0.0,
                success=False,
                error=str(e)
            )
        
        with self.lock:
            self.results.append(result)
        
        return result
    
    def run_test_suite(self, config: TestConfiguration) -> List[TestResult]:
        """Run a complete test suite based on configuration."""
        logger.info(f"🚀 Starting A/B test suite: {config.name}")
        self.is_running = True
        
        combinations = self._generate_combinations(config)
        
        # Randomize if specified
        random.shuffle(combinations)
        
        logger.info(f"📊 Running {len(combinations)} test combinations")
        
        suite_results = []
        
        for i, combo in enumerate(combinations, 1):
            if not self.is_running:
                logger.info("🛑 Test suite stopped by user")
                break
                
            logger.info(f"🧪 Running test {i}/{len(combinations)}: {combo['model']} | {combo['user_type']} | Think: {combo['think_mode']}")
            
            for iteration in range(config.iterations):
                result = self.run_single_test(**combo)
                suite_results.append(result)
                
                if result.success:
                    logger.info(f"   ✅ Test {i}.{iteration + 1} completed in {result.response_time:.2f}s")
                else:
                    logger.error(f"   ❌ Test {i}.{iteration + 1} failed: {result.error}")
                
                # Delay between tests
                if i < len(combinations) or iteration < config.iterations - 1:
                    time.sleep(config.delay_between_tests)
        
        self.is_running = False
        logger.info(f"🏁 Test suite completed: {len(suite_results)} tests run")
        
        # Save results
        self.save_results()
        
        return suite_results
    
    def stop_test_suite(self):
        """Stop the currently running test suite."""
        self.is_running = False
        logger.info("🛑 Stopping test suite...")
    
    def save_results(self, filename: str = None):
        """Save test results to file."""
        filename = filename or self.results_file
        
        results_data = {
            "test_run_info": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "successful_tests": len([r for r in self.results if r.success]),
                "failed_tests": len([r for r in self.results if not r.success])
            },
            "results": [asdict(result) for result in self.results]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"💾 Results saved to {filename}")
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics from test results."""
        if not self.results:
            return {"error": "No test results available"}
        
        successful_results = [r for r in self.results if r.success]
        
        stats = {
            "total_tests": len(self.results),
            "successful_tests": len(successful_results),
            "success_rate": len(successful_results) / len(self.results) * 100,
            "average_response_time": sum(r.response_time for r in successful_results) / len(successful_results) if successful_results else 0,
            "models_tested": list(set(r.model for r in self.results)),
            "user_types_tested": list(set(r.user_type for r in self.results)),
            "think_mode_usage": {
                "enabled": len([r for r in self.results if r.think_mode]),
                "disabled": len([r for r in self.results if not r.think_mode])
            }
        }
        
        return stats

def ab_test(config: TestConfiguration = None, base_url: str = "https://aetraggraph-529012124872.us-central1.run.app"):
    """
    Decorator for A/B testing functions.
    
    Usage:
        @ab_test(config=my_test_config)
        def my_chat_function(question, model, user_type, think_mode):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If no config provided, run original function
            if config is None:
                return func(*args, **kwargs)
            
            # Run A/B tests
            runner = ABTestRunner(base_url=base_url)
            results = runner.run_test_suite(config)
            
            # Return original function result plus test results
            original_result = func(*args, **kwargs)
            
            return {
                "original_result": original_result,
                "ab_test_results": results,
                "summary_stats": runner.get_summary_stats()
            }
        
        # Add test runner methods to the wrapped function
        wrapper.run_tests = lambda: ABTestRunner(base_url=base_url).run_test_suite(config)
        wrapper.test_config = config
        
        return wrapper
    
    return decorator

def performance_test(iterations: int = 5, models: List[str] = None):
    """
    Decorator for performance testing specific models.
    
    Usage:
        @performance_test(iterations=10, models=["gemini-2.0-flash-001"])
        def my_function():
            pass
    """
    if models is None:
        models = ["gemini-2.0-flash-001", "gemini-1.5-flash-001"]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create performance test config
            config = TestConfiguration(
                name="performance_test",
                description="Performance testing for specific models",
                models=models,
                user_types=["business"],
                think_mode_options=[False],
                questions=["What is the system performance?"],
                iterations=iterations,
                delay_between_tests=1.0
            )
            
            runner = ABTestRunner()
            results = runner.run_test_suite(config)
            
            # Return performance metrics
            successful_results = [r for r in results if r.success]
            
            performance_metrics = {
                "average_response_time": sum(r.response_time for r in successful_results) / len(successful_results) if successful_results else 0,
                "min_response_time": min(r.response_time for r in successful_results) if successful_results else 0,
                "max_response_time": max(r.response_time for r in successful_results) if successful_results else 0,
                "success_rate": len(successful_results) / len(results) * 100,
                "total_tests": len(results)
            }
            
            return performance_metrics
        
        return wrapper
    
    return decorator

def comparative_test(model_a: str, model_b: str, questions: List[str] = None):
    """
    Decorator for comparing two specific models.
    
    Usage:
        @comparative_test("gemini-2.5-flash-preview-05-20", "gemini-2.0-flash-001")
        def compare_models():
            pass
    """
    if questions is None:
        questions = ["How does the graph database work?", "Explain claims processing."]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = TestConfiguration(
                name="comparative_test",
                description=f"Comparing {model_a} vs {model_b}",
                models=[model_a, model_b],
                user_types=["business", "technical"],
                think_mode_options=[False, True],
                questions=questions,
                iterations=2
            )
            
            runner = ABTestRunner()
            results = runner.run_test_suite(config)
            
            # Group results by model
            model_a_results = [r for r in results if r.model == model_a and r.success]
            model_b_results = [r for r in results if r.model == model_b and r.success]
            
            comparison = {
                "model_a": {
                    "name": model_a,
                    "avg_response_time": sum(r.response_time for r in model_a_results) / len(model_a_results) if model_a_results else 0,
                    "success_rate": len(model_a_results) / len([r for r in results if r.model == model_a]) * 100,
                    "total_tests": len([r for r in results if r.model == model_a])
                },
                "model_b": {
                    "name": model_b,
                    "avg_response_time": sum(r.response_time for r in model_b_results) / len(model_b_results) if model_b_results else 0,
                    "success_rate": len(model_b_results) / len([r for r in results if r.model == model_b]) * 100,
                    "total_tests": len([r for r in results if r.model == model_b])
                }
            }
            
            return comparison
        
        return wrapper
    
    return decorator

# Example usage functions
@performance_test(iterations=3, models=["gemini-2.0-flash-001"])
def test_system_performance():
    """Test system performance with specific model."""
    return "Performance test completed"

@comparative_test("gemini-2.5-flash-preview-05-20", "gemini-2.0-flash-001")
def compare_gemini_models():
    """Compare Gemini 2.5 vs 2.0 performance."""
    return "Model comparison completed"

if __name__ == "__main__":
    # Example of running performance test
    print("🚀 Running performance test...")
    perf_results = test_system_performance()
    print(f"📊 Performance results: {perf_results}")
    
    # Example of running comparative test
    print("\n🔄 Running comparative test...")
    comp_results = compare_gemini_models()
    print(f"📈 Comparison results: {comp_results}") 