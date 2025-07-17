#!/usr/bin/env python3
"""
Test script for the simple chat API
"""

import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.simple_deck_service import SimpleDeckBuildingService

async def test_simple_api():
    """Test the simple deck building API directly"""
    
    service = SimpleDeckBuildingService()
    
    # Test message
    test_message = "I want Pokemon with spread damage"
    test_user_id = "test_user_123"
    
    print(f"Testing message: '{test_message}'")
    print(f"User ID: {test_user_id}")
    print("-" * 50)
    
    try:
        # Call the service directly
        response = await service.process_user_message(
            user_id=test_user_id,
            message=test_message
        )
        
        print("RESPONSE:")
        print(f"AI Response: {response.get('ai_response', 'No response')[:200]}...")
        print(f"Cards Found: {len(response.get('cards_found', []))}")
        print(f"Error: {response.get('error', 'None')}")
        
        if response.get('debug'):
            print("\nDEBUG INFO:")
            for key, value in response['debug'].items():
                print(f"  {key}: {value}")
        
        if response.get('cards_found'):
            print(f"\nFIRST FEW CARDS:")
            for i, card in enumerate(response['cards_found'][:3]):
                print(f"  {i+1}. {card.get('name', 'Unknown')} - {card.get('card_type', 'Unknown')}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_api())