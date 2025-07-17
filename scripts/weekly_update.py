#!/usr/bin/env python3
"""
Weekly Pokemon TCG Database Update Script
Runs automated weekly updates to keep card database current
"""

import sys
import os
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.import_pokemon_cards import PokemonCardImporter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/pokemon-cards-update.log', mode='a'),
        logging.StreamHandler()
    ]
)

def main():
    """Run weekly database update"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🃏 Starting weekly Pokemon TCG database update...")
        
        # Run the import
        importer = PokemonCardImporter()
        importer.import_all_standard_cards()
        
        logger.info("✅ Weekly update completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Weekly update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()