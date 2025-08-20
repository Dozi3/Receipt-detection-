#!/usr/bin/env python3
"""
Simple script to test the GUI functionality
"""

import sys
from pathlib import Path
import logging

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("test_gui")

try:
    logger.info("Importing receipt_analyzer.gui.app")
    from receipt_analyzer.gui.app import ReceiptAnalyzerApp
    
    logger.info("Creating app instance")
    app = ReceiptAnalyzerApp()
    
    logger.info("Starting app main loop")
    app.run()
    
except Exception as e:
    logger.error(f"Error running GUI: {e}", exc_info=True)
