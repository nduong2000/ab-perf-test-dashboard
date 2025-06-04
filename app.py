#!/usr/bin/env python3
"""
A/B Testing Application Entry Point
Standalone deployment of the A/B Testing system for Graph RAG.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import the A/B testing Flask app
from ab_testing.ab_test_app import app

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    logger.info(f"🚀 Starting A/B Testing Application on port {port}")
    logger.info(f"📊 Dashboard: http://localhost:{port}/")
    logger.info(f"🧪 Configurations: http://localhost:{port}/configurations")
    logger.info(f"📈 Executions: http://localhost:{port}/executions")
    logger.info(f"📋 Results: http://localhost:{port}/results")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    ) 