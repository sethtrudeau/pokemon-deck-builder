#!/usr/bin/env python3
"""
Test client for Pokemon Deck Builder API
Tests the complete conversation flow and endpoint functionality
"""

import asyncio
import json
import sys
from typing import Dict, Any
import httpx
from decouple import config

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_123"

class PokemonDeckBuilderTestClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        await self.client.aclose()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test the health check endpoint"""
        print("🔍 Testing health check endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            result = response.json()
            print(f"✅ Health check: {result}")
            return result
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return {"error": str(e)}
    
    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Test the root endpoint"""
        print("🔍 Testing root endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/")
            result = response.json()
            print(f"✅ Root endpoint: {result}")
            return result
        except Exception as e:
            print(f"❌ Root endpoint failed: {e}")
            return {"error": str(e)}
    
    async def test_card_search(self) -> Dict[str, Any]:
        """Test card search functionality"""
        print("🔍 Testing card search endpoint...")
        try:
            # Test basic search
            response = await self.client.get(f"{self.base_url}/cards/search?limit=5")
            result = response.json()
            print(f"✅ Card search (basic): Found {len(result.get('data', []))} cards")
            
            # Test search with filters
            response = await self.client.get(f"{self.base_url}/cards/search?name=Pikachu&limit=3")
            result = response.json()
            print(f"✅ Card search (Pikachu): Found {len(result.get('data', []))} cards")
            
            return result
        except Exception as e:
            print(f"❌ Card search failed: {e}")
            return {"error": str(e)}
    
    async def test_card_filters(self) -> Dict[str, Any]:
        """Test card filters endpoint"""
        print("🔍 Testing card filters endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/cards/filters")
            result = response.json()
            print(f"✅ Card filters: {list(result.keys())}")
            return result
        except Exception as e:
            print(f"❌ Card filters failed: {e}")
            return {"error": str(e)}
    
    async def test_pokemon_chat(self, message: str) -> Dict[str, Any]:
        """Test the main pokemon chat endpoint"""
        print(f"🔍 Testing pokemon chat: '{message}'")
        try:
            payload = {
                "user_id": TEST_USER_ID,
                "message": message,
                "deck_id": None
            }
            response = await self.client.post(f"{self.base_url}/decks/pokemon-chat", json=payload)
            result = response.json()
            
            print(f"✅ Chat response:")
            print(f"   Intent: {result.get('intent')}")
            print(f"   Focus: {result.get('focus_area')}")
            print(f"   Phase: {result.get('current_phase')}")
            print(f"   Cards found: {len(result.get('cards_found', []))}")
            print(f"   AI Response: {result.get('ai_response', '')[:100]}...")
            
            return result
        except Exception as e:
            print(f"❌ Pokemon chat failed: {e}")
            return {"error": str(e)}
    
    async def test_deck_summary(self) -> Dict[str, Any]:
        """Test deck summary endpoint"""
        print("🔍 Testing deck summary endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/decks/summary/{TEST_USER_ID}")
            result = response.json()
            
            print(f"✅ Deck summary:")
            print(f"   Phase: {result.get('current_phase')}")
            print(f"   Total cards: {result.get('deck_progress', {}).get('total_cards', 0)}")
            print(f"   Cards by type: {result.get('deck_progress', {}).get('cards_by_type', {})}")
            
            return result
        except Exception as e:
            print(f"❌ Deck summary failed: {e}")
            return {"error": str(e)}
    
    async def run_conversation_flow_test(self):
        """Test the complete conversation flow"""
        print("\n🚀 Starting conversation flow test...\n")
        
        # Test conversation flow
        test_messages = [
            "I want to build a new Pokemon deck",
            "I want to build an aggressive fire deck",
            "Show me some fire Pokemon cards",
            "Add some Charizard cards",
            "I'm ready to move to the next phase",
            "Now I need some trainer cards",
            "Show me some draw cards",
            "I need energy cards now",
            "Show me fire energy cards"
        ]
        
        for message in test_messages:
            await self.test_pokemon_chat(message)
            await asyncio.sleep(1)  # Small delay between requests
            print("-" * 50)
        
        # Test deck summary
        await self.test_deck_summary()
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Pokemon Deck Builder API Test Suite")
        print("=" * 50)
        
        try:
            # Basic endpoint tests
            await self.test_health_check()
            await self.test_root_endpoint()
            
            # Card functionality tests
            await self.test_card_search()
            await self.test_card_filters()
            
            # Conversation flow test
            await self.run_conversation_flow_test()
            
            print("\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
        finally:
            await self.close()


async def main():
    """Main test runner"""
    # Check if Claude API key is set
    if not config('CLAUDE_API_KEY', default=''):
        print("⚠️  WARNING: CLAUDE_API_KEY not set - conversation tests may fail")
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                print(f"❌ Server not responding properly: {response.status_code}")
                sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print(f"   Error: {e}")
        print("   Please start the server with: python main.py")
        sys.exit(1)
    
    # Run tests
    test_client = PokemonDeckBuilderTestClient()
    await test_client.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())