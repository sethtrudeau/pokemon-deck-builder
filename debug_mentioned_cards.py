#!/usr/bin/env python3
"""
Debug script to check the specific cards mentioned by the user
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.card_queries import get_card_query_builder

async def debug_mentioned_cards():
    """Check the specific cards mentioned by the user"""
    
    mentioned_cards = [
        "Hisuian Braviary",
        "Earthen Seal Stone", 
        "Mamoswine",
        "Cetitan",
        "Spectrier",
        "Drifblim",
        "Shadow Rider Calyrex V",
        "Electivire",
        "Absol",
        "Hitmonlee",
        "Mewtwo VSTAR",
        "Luxio",
        "Inteleon VMAX"
    ]
    
    print("=== Checking Mentioned Cards ===\n")
    
    try:
        query_builder = await get_card_query_builder()
        
        # First, let's check if these cards exist in the database at all
        print("1. Checking if cards exist in database...")
        for card_name in mentioned_cards:
            result = query_builder.client.table("pokemon_cards").select("*").ilike("name", f"%{card_name}%").execute()
            
            if result.data:
                print(f"\n{card_name}:")
                for card in result.data:
                    print(f"  - ID: {card.get('id', 'N/A')}")
                    print(f"  - Name: {card.get('name', 'N/A')}")
                    print(f"  - Standard Legal: {card.get('standard_legal', 'N/A')}")
                    print(f"  - Set: {card.get('set_name', 'N/A')} ({card.get('set_series', 'N/A')})")
                    print(f"  - Regulation Mark: {card.get('regulation_mark', 'N/A')}")
                    print(f"  - Legalities: {card.get('legalities', 'N/A')}")
                    
                    # Check if they have spread damage
                    attacks = card.get('attacks', [])
                    if attacks:
                        for attack in attacks:
                            attack_text = attack.get('text', '').lower()
                            if any(phrase in attack_text for phrase in ['damage to each', 'each opponent', 'all opponent', 'bench damage']):
                                print(f"  - SPREAD DAMAGE ATTACK: {attack.get('name', 'Unknown')}")
                                print(f"    Text: {attack.get('text', '')}")
            else:
                print(f"\n{card_name}: NOT FOUND")
        
        # Now let's check what the standard_legal filter is actually returning
        print("\n\n2. Checking what the standard_legal filter returns...")
        standard_legal_result = query_builder.client.table("pokemon_cards").select("*").eq("standard_legal", True).limit(5).execute()
        
        print(f"Found {len(standard_legal_result.data)} standard legal cards (showing first 5):")
        for card in standard_legal_result.data:
            print(f"  - {card.get('name', 'N/A')} - {card.get('set_name', 'N/A')} - Reg Mark: {card.get('regulation_mark', 'N/A')}")
        
        # Check the regulation marks in the database
        print("\n\n3. Checking regulation marks in database...")
        reg_marks_result = query_builder.client.table("pokemon_cards").select("regulation_mark").execute()
        
        reg_marks = {}
        for card in reg_marks_result.data:
            mark = card.get('regulation_mark')
            if mark:
                reg_marks[mark] = reg_marks.get(mark, 0) + 1
        
        print("Regulation marks found:")
        for mark, count in sorted(reg_marks.items()):
            print(f"  - {mark}: {count} cards")
        
        # Check which regulation marks are marked as standard_legal
        print("\n\n4. Checking which regulation marks are marked as standard_legal...")
        standard_reg_marks = {}
        standard_legal_cards = query_builder.client.table("pokemon_cards").select("regulation_mark").eq("standard_legal", True).execute()
        
        for card in standard_legal_cards.data:
            mark = card.get('regulation_mark')
            if mark:
                standard_reg_marks[mark] = standard_reg_marks.get(mark, 0) + 1
        
        print("Standard legal regulation marks:")
        for mark, count in sorted(standard_reg_marks.items()):
            print(f"  - {mark}: {count} cards")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_mentioned_cards())