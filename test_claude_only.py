#!/usr/bin/env python3
"""
Test Claude API integration only
"""

import asyncio
import sys
sys.path.append('.')

from app.utils.claude_client import ClaudeClient
from app.services.conversation_service import ConversationState, DeckPhase

async def test_claude_integration():
    """Test Claude API integration"""
    print("🧪 Testing Claude API Integration")
    print("=" * 50)
    
    try:
        # Initialize Claude client
        claude_client = ClaudeClient()
        print("✅ Claude client initialized successfully")
        
        # Create a test conversation state
        conversation_state = ConversationState(
            user_id="test_user",
            current_phase=DeckPhase.STRATEGY,
            deck_strategy="Aggressive Fire Deck"
        )
        
        # Test basic response generation
        test_message = "I want to build a fire deck with Charizard"
        print(f"\n🔍 Testing message: '{test_message}'")
        
        response = await claude_client.generate_response(
            test_message,
            conversation_state
        )
        
        print(f"\n✅ Claude Response:")
        print("-" * 30)
        print(response)
        print("-" * 30)
        
        # Test phase transition advice
        print(f"\n🔍 Testing phase transition advice...")
        
        transition_response = await claude_client.get_phase_transition_advice(conversation_state)
        
        print(f"\n✅ Phase Transition Advice:")
        print("-" * 30)
        print(transition_response)
        print("-" * 30)
        
        print("\n🎉 All Claude API tests passed!")
        
    except Exception as e:
        print(f"\n❌ Claude API test failed: {e}")
        print("Please check your CLAUDE_API_KEY in .env file")

if __name__ == "__main__":
    asyncio.run(test_claude_integration())