"""
Configuration Generator for A/B Testing System
Extracts sample questions and models from the main system and creates test configurations.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

class ABTestConfigGenerator:
    """Generate A/B test configurations based on system data."""
    
    def __init__(self, config_dir: str = "src/llmops/ab_testing/configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Sample questions extracted from chat.html
        self.sample_questions = [
            "How to identify Dental Claim?",
            "How to identify supplies Claim?",
            "How to identify workers comp Claim?",
            "How to identify subrogation Claim?",
            "How to identify in-house/340b Claim?",
            "How to identify supplies, workers comp claims, subrogation claims, and in-house/340b claims?",
            "How to identify indemnity Claim?",
            "What is field 15 in the Universal file?",
            "Explain External Stop Loss reporting requirements",
            "What are the capitation payment file specifications?",
            "Where can I find provider identification fields?",
            "What is ICD9_DX_CD?",
            "Present on Admission Code",
            "Explain Aexcel Designated Provider Specialty",
            "How does the graph database enhance document processing?",
            "What are the key features of Graph RAG v3.0?",
            "How does Neo4j integration improve search results?",
            "Explain the confidence scoring system",
            "What types of documents can be processed?",
            "How does iterative extraction work?",
            "What is the relationship between entities in the graph?",
            "How are embedded Excel files handled?",
            "What validation methods are used?",
            "How does the system handle older MS Office formats?",
            "Explain the multi-layer validation process",
            "What are the performance optimizations?",
            "How does error handling work?",
            "What is the graph schema flexibility?"
        ]
        
        # Models available in the AET Graph RAG System v3.0
        self.llm_models = [
            {
                "id": "gemini-2.5-pro",
                "name": "🧠 Gemini 2.5 Pro - Most Advanced Reasoning",
                "supports_think_mode": True,
                "category": "advanced"
            },
            {
                "id": "gemini-2.5-flash",
                "name": "⚡ Gemini 2.5 Flash - Best Price-Performance",
                "supports_think_mode": True,
                "category": "advanced"
            },
            {
                "id": "gemini-2.5-flash-lite",
                "name": "💰 Gemini 2.5 Flash Lite - Most Cost-Effective",
                "supports_think_mode": True,
                "category": "advanced"
            },
            {
                "id": "gemini-2.0-flash",
                "name": "🚀 Gemini 2.0 Flash - Next Generation",
                "supports_think_mode": False,
                "category": "standard"
            },
            {
                "id": "gemini-2.0-flash-lite",
                "name": "💸 Gemini 2.0 Flash Lite - Cost Efficient",
                "supports_think_mode": False,
                "category": "lite"
            },
            {
                "id": "gemini-1.5-flash",
                "name": "📦 Gemini 1.5 Flash - Legacy Stable",
                "supports_think_mode": False,
                "category": "legacy"
            },
            {
                "id": "gemini-1.5-pro",
                "name": "🏛️ Gemini 1.5 Pro - Legacy Stable",
                "supports_think_mode": False,
                "category": "legacy"
            }
        ]
        
        # User types
        self.user_types = ["business", "technical"]
        
        # Think mode options for compatible models
        self.think_mode_options = [True, False]
    
    def categorize_questions(self) -> Dict[str, List[str]]:
        """Categorize questions by topic."""
        categories = {
            "claims_processing": [],
            "technical_features": [],
            "data_fields": [],
            "compliance": [],
            "system_architecture": []
        }
        
        for question in self.sample_questions:
            question_lower = question.lower()
            
            if any(term in question_lower for term in ["claim", "dental", "workers comp", "subrogation", "indemnity"]):
                categories["claims_processing"].append(question)
            elif any(term in question_lower for term in ["graph", "neo4j", "database", "extraction", "processing"]):
                categories["technical_features"].append(question)
            elif any(term in question_lower for term in ["field", "icd9", "admission", "universal file"]):
                categories["data_fields"].append(question)
            elif any(term in question_lower for term in ["stop loss", "capitation", "aexcel"]):
                categories["compliance"].append(question)
            else:
                categories["system_architecture"].append(question)
        
        return categories
    
    def generate_basic_config(self, name: str, description: str) -> Dict[str, Any]:
        """Generate a basic test configuration."""
        return {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "test_duration_minutes": 60,
            "questions_per_test": 10,
            "delay_between_questions": 5,
            "randomize_order": True,
            "collect_metrics": True,
            "save_responses": True
        }
    
    def generate_model_comparison_config(self) -> Dict[str, Any]:
        """Generate configuration for comparing different models."""
        config = self.generate_basic_config(
            "model_comparison",
            "Compare performance across different LLM models"
        )
        
        # Select models for comparison
        config.update({
            "test_type": "model_comparison",
            "models_to_test": [model["id"] for model in self.llm_models[:4]],  # Test first 4 models
            "user_type": "business",  # Fixed user type for this test
            "think_mode": False,  # Fixed think mode for this test
            "questions": random.sample(self.sample_questions, 15),
            "metrics": [
                "response_time",
                "response_length",
                "confidence_score",
                "error_rate"
            ]
        })
        
        return config
    
    def generate_think_mode_config(self) -> Dict[str, Any]:
        """Generate configuration for testing think mode vs normal mode."""
        config = self.generate_basic_config(
            "think_mode_comparison",
            "Compare performance with think mode on vs off for Gemini 2.5 models"
        )
        
        # Only use models that support think mode
        think_mode_models = [m["id"] for m in self.llm_models if m["supports_think_mode"]]
        
        config.update({
            "test_type": "think_mode_comparison",
            "models_to_test": think_mode_models,
            "user_type": "technical",  # Technical users might benefit more from think mode
            "think_mode_options": [True, False],
            "questions": random.sample(self.sample_questions, 12),
            "metrics": [
                "response_time",
                "response_quality",
                "accuracy",
                "completeness"
            ]
        })
        
        return config
    
    def generate_user_type_config(self) -> Dict[str, Any]:
        """Generate configuration for testing business vs technical user types."""
        config = self.generate_basic_config(
            "user_type_comparison",
            "Compare response quality for business vs technical user types"
        )
        
        config.update({
            "test_type": "user_type_comparison",
            "models_to_test": ["gemini-2.0-flash"],  # Fixed model for this test
            "user_types": ["business", "technical"],
            "think_mode": False,
            "questions": random.sample(self.sample_questions, 10),
            "metrics": [
                "response_relevance",
                "technical_depth",
                "business_value",
                "clarity"
            ]
        })
        
        return config
    
    def generate_comprehensive_config(self) -> Dict[str, Any]:
        """Generate comprehensive configuration testing all combinations."""
        config = self.generate_basic_config(
            "comprehensive_test",
            "Test all combinations of models, user types, and think modes"
        )
        
        config.update({
            "test_type": "comprehensive",
            "models_to_test": [model["id"] for model in self.llm_models],
            "user_types": self.user_types,
            "think_mode_options": self.think_mode_options,
            "questions": self.sample_questions,  # Use all questions
            "test_duration_minutes": 180,  # Longer test for comprehensive coverage
            "questions_per_combination": 3,  # 3 questions per combination
            "metrics": [
                "response_time",
                "response_length",
                "response_quality",
                "accuracy",
                "relevance",
                "error_rate"
            ]
        })
        
        return config
    
    def generate_category_specific_config(self, category: str) -> Dict[str, Any]:
        """Generate configuration for testing specific question categories."""
        categories = self.categorize_questions()
        
        if category not in categories:
            raise ValueError(f"Unknown category: {category}")
        
        config = self.generate_basic_config(
            f"{category}_test",
            f"Test performance on {category} questions"
        )
        
        config.update({
            "test_type": "category_specific",
            "category": category,
            "models_to_test": [model["id"] for model in self.llm_models[:3]],  # Test top 3 models
            "user_types": self.user_types,
            "think_mode_options": [False],  # Keep simple for category tests
            "questions": categories[category],
            "metrics": [
                "category_relevance",
                "accuracy",
                "completeness"
            ]
        })
        
        return config
    
    def save_config(self, config: Dict[str, Any], filename: str = None) -> str:
        """Save configuration to file."""
        if filename is None:
            filename = f"{config['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        config_path = self.config_dir / filename
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return str(config_path)
    
    def load_config(self, filename: str) -> Dict[str, Any]:
        """Load configuration from file."""
        config_path = self.config_dir / filename
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def list_configs(self) -> List[str]:
        """List all available configuration files."""
        return [f.name for f in self.config_dir.glob("*.json")]
    
    def generate_all_default_configs(self) -> List[str]:
        """Generate all default configurations and save them."""
        configs = [
            self.generate_model_comparison_config(),
            self.generate_think_mode_config(),
            self.generate_user_type_config(),
            self.generate_comprehensive_config()
        ]
        
        # Generate category-specific configs
        categories = self.categorize_questions()
        for category in categories.keys():
            if categories[category]:  # Only if category has questions
                configs.append(self.generate_category_specific_config(category))
        
        saved_files = []
        for config in configs:
            filename = self.save_config(config)
            saved_files.append(filename)
        
        return saved_files
    
    def get_random_test_combination(self) -> Dict[str, Any]:
        """Get a random combination for testing."""
        model = random.choice(self.llm_models)
        user_type = random.choice(self.user_types)
        think_mode = False
        
        # Enable think mode only for compatible models
        if model["supports_think_mode"]:
            think_mode = random.choice(self.think_mode_options)
        
        return {
            "model": model["id"],
            "model_name": model["name"],
            "user_type": user_type,
            "think_mode": think_mode,
            "question": random.choice(self.sample_questions)
        }


if __name__ == "__main__":
    # Example usage
    generator = ABTestConfigGenerator()
    
    print("🔧 Generating A/B test configurations...")
    
    # Generate all default configs
    saved_files = generator.generate_all_default_configs()
    
    print(f"✅ Generated {len(saved_files)} configuration files:")
    for file in saved_files:
        print(f"   📄 {file}")
    
    # Show example random combination
    combo = generator.get_random_test_combination()
    print(f"\n🎲 Example random test combination:")
    print(f"   Model: {combo['model_name']}")
    print(f"   User Type: {combo['user_type']}")
    print(f"   Think Mode: {combo['think_mode']}")
    print(f"   Question: {combo['question']}")
    
    print(f"\n📊 Question categories:")
    categories = generator.categorize_questions()
    for category, questions in categories.items():
        print(f"   {category}: {len(questions)} questions") 