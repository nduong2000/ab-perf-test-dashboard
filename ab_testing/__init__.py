"""
A/B Testing Framework for Graph RAG System

This package provides comprehensive A/B testing capabilities for the Graph RAG system,
including configuration management, test execution, and results analysis.

Key Components:
- ABTestRunner: Core test execution engine
- ABTestManager: Test lifecycle management  
- ABTestConfigGenerator: Configuration generation and management
- Decorators: Decorator-based testing framework
"""

from .decorators import (
    ABTestRunner, 
    TestResult, 
    TestConfiguration,
    ab_test,
    performance_test,
    comparative_test
)

from .test_manager import (
    ABTestManager,
    TestExecution
)

from .config_generator import (
    ABTestConfigGenerator
)

__version__ = "1.0.0"
__author__ = "Graph RAG Team"

__all__ = [
    # Core classes
    "ABTestRunner",
    "ABTestManager", 
    "ABTestConfigGenerator",
    
    # Data classes
    "TestResult",
    "TestConfiguration", 
    "TestExecution",
    
    # Decorators
    "ab_test",
    "performance_test",
    "comparative_test"
] 