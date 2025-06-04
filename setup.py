#!/usr/bin/env python3
"""
Setup script for A/B Testing Application
Initializes sample configurations and ensures proper directory structure.
"""

import os
import sys
import logging
from pathlib import Path

# Add the ab_testing module to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ab_testing.config_generator import ABTestConfigGenerator

def setup_directories():
    """Create necessary directories."""
    print("📁 Setting up directories...")
    
    directories = [
        "ab_testing/configs",
        "ab_testing/results",
        "ab_testing/__pycache__"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")

def generate_sample_configurations():
    """Generate sample test configurations."""
    print("⚙️ Generating sample configurations...")
    
    config_generator = ABTestConfigGenerator("ab_testing/configs")
    
    # Generate different types of configurations
    configs_to_create = [
        ("model_comparison", "Sample Model Comparison Test"),
        ("think_mode", "Think Mode vs Regular Mode"),
        ("user_type", "Business vs Technical Users"),
        ("comprehensive", "Comprehensive System Test"),
        ("category_specific", "Claims Processing Focus", {"category": "claims_processing"}),
        ("category_specific", "Technical Features Test", {"category": "technical_features"}),
    ]
    
    for config_type, name, *kwargs in configs_to_create:
        try:
            if config_type == "model_comparison":
                config = config_generator.generate_model_comparison_config()
            elif config_type == "think_mode":
                config = config_generator.generate_think_mode_config()
            elif config_type == "user_type":
                config = config_generator.generate_user_type_config()
            elif config_type == "comprehensive":
                config = config_generator.generate_comprehensive_config()
            elif config_type == "category_specific":
                category = kwargs[0].get("category", "claims_processing") if kwargs else "claims_processing"
                config = config_generator.generate_category_specific_config(category)
            
            # Override name
            config["name"] = name
            
            # Save configuration
            filename = config_generator.save_config(config)
            print(f"✓ Created: {filename}")
            
        except Exception as e:
            print(f"❌ Failed to create {config_type}: {e}")

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """Main setup function."""
    print("🚀 A/B Testing Application Setup")
    print("=" * 40)
    
    setup_logging()
    setup_directories()
    generate_sample_configurations()
    
    print("=" * 40)
    print("✅ Setup completed successfully!")
    print()
    print("🎯 Next steps:")
    print("1. Configure your target Graph RAG URL in .env")
    print("2. Run 'python app.py' to start the application")
    print("3. Visit http://localhost:8080 to access the dashboard")
    print()
    print("📊 Available endpoints:")
    print("- Dashboard: http://localhost:8080/")
    print("- Configurations: http://localhost:8080/configurations")
    print("- Executions: http://localhost:8080/executions")
    print("- Results: http://localhost:8080/results")

if __name__ == "__main__":
    main() 