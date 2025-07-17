#!/usr/bin/env python3
"""
Debug script to test spread damage card search functionality
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.card_queries import get_card_query_builder
from app.utils.claude_client import ClaudeClient
from app.services.simple_deck_service import SimpleDeckState

async def debug_spread_damage_search():
    """Debug the spread damage search functionality"""
    
    print("=== Debugging Spread Damage Search ===\n")
    
    # Test 1: Check database query builder
    print("1. Testing database query builder...")
    try:
        query_builder = await get_card_query_builder()
        print("✓ Database query builder created successfully")
        
        # Test a broad search
        broad_results = query_builder.search_cards(limit=10)
        print(f"✓ Broad search returned {broad_results['count']} cards")
        
        # Show some sample cards
        if broad_results['data']:
            print("\nSample cards from database:")
            for i, card in enumerate(broad_results['data'][:3]):
                print(f"  - {card.get('name', 'Unknown')} ({card.get('card_type', 'Unknown')})")
                
                # Check if card has attacks with spread damage
                attacks = card.get('attacks', [])
                if attacks:
                    for attack in attacks:
                        attack_text = attack.get('text', '').lower()
                        if any(phrase in attack_text for phrase in ['damage to each', 'each opponent', 'all opponent']):
                            print(f"    -> SPREAD DAMAGE ATTACK: {attack.get('name', 'Unknown')} - {attack.get('text', '')}")
        
    except Exception as e:
        print(f"✗ Database query builder failed: {e}")
        return
    
    # Test 2: Check intelligent search
    print("\n2. Testing intelligent search...")
    try:
        claude_client = ClaudeClient()
        
        # Test spread damage search
        search_results = await claude_client._execute_intelligent_search(
            "I need Pokemon with spread damage capabilities",
            query_builder
        )
        
        print(f"✓ Intelligent search returned {len(search_results)} cards")
        
        # Analyze results
        spread_cards = []
        for card in search_results:
            card_name = card.get('name', 'Unknown')
            attacks = card.get('attacks', [])
            
            if attacks:
                for attack in attacks:
                    attack_text = attack.get('text', '').lower()
                    if any(phrase in attack_text for phrase in ['damage to each', 'each opponent', 'all opponent', 'bench damage']):
                        spread_cards.append({
                            'name': card_name,
                            'attack': attack.get('name', 'Unknown'),
                            'text': attack.get('text', '')
                        })
        
        print(f"✓ Found {len(spread_cards)} cards with spread damage")
        
        if spread_cards:
            print("\nSpread damage cards found:")
            for card in spread_cards[:5]:  # Show first 5
                print(f"  - {card['name']}: {card['attack']}")
                print(f"    Text: {card['text'][:100]}...")
        else:
            print("⚠ No spread damage cards found in search results")
            
    except Exception as e:
        print(f"✗ Intelligent search failed: {e}")
        return
    
    # Test 3: Check full flow
    print("\n3. Testing full flow...")
    try:
        # Create a dummy deck state
        deck_state = SimpleDeckState(user_id="test_user", selected_cards=[])
        
        # Test generate_response_with_database_access
        response = await claude_client.generate_response_with_database_access(
            user_message="I need Pokemon with spread damage capabilities",
            deck_state=deck_state,
            query_builder=query_builder
        )
        
        print(f"✓ Full flow completed")
        print(f"✓ AI response length: {len(response.get('ai_response', ''))}")
        print(f"✓ Cards found: {len(response.get('cards_found', []))}")
        
        # Check if response is generic
        ai_response = response.get('ai_response', '')
        if len(ai_response) < 100 or 'hello' in ai_response.lower():
            print("⚠ Response appears to be generic")
        else:
            print("✓ Response appears to be specific")
            
        # Show first part of response
        print(f"\nFirst 200 chars of AI response: {ai_response[:200]}...")
        
    except Exception as e:
        print(f"✗ Full flow failed: {e}")
        return
    
    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    asyncio.run(debug_spread_damage_search())