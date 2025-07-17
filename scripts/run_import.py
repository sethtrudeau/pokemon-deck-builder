#!/usr/bin/env python3
"""
Simple runner script for Pokemon card import
"""

import sys
import os

# Add parent directory to path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.import_pokemon_cards import main

if __name__ == "__main__":
    print("🃏 Pokemon TCG Card Import Tool")
    print("=" * 40)
    print("This will import current standard-legal cards from pokemontcg.io")
    print("and update your Supabase database with proper standard legality.")
    print()
    
    confirm = input("Do you want to proceed? (y/N): ").lower().strip()
    if confirm in ['y', 'yes']:
        main()
    else:
        print("Import cancelled.")