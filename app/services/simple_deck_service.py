"""
Simplified Pokemon Deck Building Service
Direct Claude-Database interaction without complex middleware
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from ..utils.claude_client import ClaudeClient
from ..database.card_queries import CardQueryBuilder, get_card_query_builder
from ..database.supabase_client import get_supabase_client
from ..services.conversation_service import ConversationState, DeckPhase


@dataclass
class SimpleDeckState:
    """Simplified deck state management"""
    user_id: str
    selected_cards: List[Dict[str, Any]] = None
    deck_strategy: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.selected_cards is None:
            self.selected_cards = []
        if self.conversation_history is None:
            self.conversation_history = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class SimpleDeckBuildingService:
    """Direct Claude-Database interaction for deck building"""
    
    def __init__(self):
        self.claude_client = ClaudeClient()
        # In-memory storage for now - could be Redis/database later
        self.deck_states: Dict[str, SimpleDeckState] = {}

    async def process_user_message(self, user_id: str, message: str, deck_id: Optional[str] = None) -> Dict[str, Any]:
        """Main entry point - direct Claude interaction"""
        try:
            # Load or create deck state
            deck_state = self._get_or_create_deck_state(user_id, deck_id)
            
            # Add user message to history
            deck_state.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": message
            })
            
            # Get database query builder
            query_builder = await get_card_query_builder()
            
            # Convert SimpleDeckState to ConversationState for Claude client
            conversation_state = self._convert_to_conversation_state(deck_state)
            
            # DEBUG: Print what we're doing
            print(f"DEBUG: Processing message: '{message}'")
            print(f"DEBUG: User ID: {user_id}")
            
            # Let Claude handle everything directly with memory cache
            response = await self.claude_client.generate_response_with_database_access(
                user_message=message,
                deck_state=conversation_state,
                query_builder=query_builder,
                user_id=user_id,
                deck_id=deck_id
            )
            
            # DEBUG: Print response
            print(f"DEBUG: Claude response: {response.get('ai_response', 'No response')[:200]}...")
            print(f"DEBUG: Cards found: {len(response.get('cards_found', []))}")
            
            # Add Claude's response to history
            deck_state.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "assistant",
                "content": response["ai_response"]
            })
            
            # Update deck state if Claude modified it
            if response.get("updated_deck_state"):
                deck_state.selected_cards = response["updated_deck_state"].get("selected_cards", deck_state.selected_cards)
                deck_state.deck_strategy = response["updated_deck_state"].get("deck_strategy", deck_state.deck_strategy)
            
            deck_state.updated_at = datetime.now()
            
            # Build response
            return {
                "user_id": user_id,
                "message": message,
                "ai_response": response["ai_response"],
                "cards_found": response.get("cards_found", []),
                "deck_progress": self._get_deck_progress(deck_state),
                "conversation_state": self._deck_state_to_dict(deck_state),
                "memory_cache_summary": response.get("memory_cache_summary", ""),
                "total_discovered_cards": response.get("total_discovered_cards", 0),
                "debug": {
                    "cards_found_count": len(response.get("cards_found", [])),
                    "first_card": response.get("cards_found", [{}])[0].get("name", "No cards") if response.get("cards_found") else "No cards",
                    "search_detected": "spread damage" in message.lower(),
                    "memory_cache_enabled": True
                },
                "error": None
            }
            
        except Exception as e:
            return {
                "user_id": user_id,
                "message": message,
                "ai_response": "I apologize, but I encountered an error processing your request. Please try again.",
                "cards_found": [],
                "deck_progress": {"total_cards": 0, "cards_by_type": {"Pokemon": 0, "Trainer": 0, "Energy": 0}, "cards_remaining": 60},
                "conversation_state": {"user_id": user_id, "selected_cards": [], "conversation_history": []},
                "error": str(e)
            }

    def _get_or_create_deck_state(self, user_id: str, deck_id: Optional[str]) -> SimpleDeckState:
        """Get existing deck state or create new one"""
        state_key = f"{user_id}:{deck_id or 'default'}"
        
        if state_key not in self.deck_states:
            self.deck_states[state_key] = SimpleDeckState(user_id=user_id)
        
        return self.deck_states[state_key]

    def _convert_to_conversation_state(self, deck_state: SimpleDeckState) -> ConversationState:
        """Convert SimpleDeckState to ConversationState for Claude client compatibility"""
        return ConversationState(
            user_id=deck_state.user_id,
            deck_id=None,
            current_phase=DeckPhase.STRATEGY,  # Default phase
            deck_strategy=deck_state.deck_strategy,
            selected_cards=deck_state.selected_cards,
            conversation_history=deck_state.conversation_history,
            last_query_filters={},
            phase_completion={
                "strategy": False,
                "core_pokemon": False,
                "support": False,
                "energy": False,
                "complete": False
            },
            created_at=deck_state.created_at,
            updated_at=deck_state.updated_at
        )

    def _get_deck_progress(self, deck_state: SimpleDeckState) -> Dict[str, Any]:
        """Get current deck progress summary"""
        total_cards = len(deck_state.selected_cards)
        
        card_counts = {"Pokemon": 0, "Trainer": 0, "Energy": 0}
        for card in deck_state.selected_cards:
            card_type = card.get("card_type", "Unknown")
            if card_type in card_counts:
                card_counts[card_type] += 1
        
        return {
            "total_cards": total_cards,
            "cards_by_type": card_counts,
            "cards_remaining": 60 - total_cards,
            "deck_strategy": deck_state.deck_strategy
        }

    def _deck_state_to_dict(self, deck_state: SimpleDeckState) -> Dict[str, Any]:
        """Convert deck state to dictionary"""
        return {
            "user_id": deck_state.user_id,
            "selected_cards": deck_state.selected_cards,
            "deck_strategy": deck_state.deck_strategy,
            "conversation_history": deck_state.conversation_history[-10:],  # Last 10 messages
            "updated_at": deck_state.updated_at.isoformat()
        }

    async def add_card_to_deck(self, user_id: str, card_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Add a specific card to the user's deck"""
        try:
            deck_state = self._get_or_create_deck_state(user_id, None)
            query_builder = await get_card_query_builder()
            
            # Get card details
            card = query_builder.get_card_by_id(card_id)
            if not card:
                return {"error": "Card not found"}
            
            # Check deck rules
            current_count = sum(1 for c in deck_state.selected_cards if c.get("card_id") == card_id)
            if current_count + quantity > 4:
                return {"error": "Maximum 4 copies of any card allowed"}
            
            if len(deck_state.selected_cards) + quantity > 60:
                return {"error": "Deck cannot exceed 60 cards"}
            
            # Add cards to deck
            for _ in range(quantity):
                deck_state.selected_cards.append(card)
            
            deck_state.updated_at = datetime.now()
            
            return {
                "success": True,
                "card_added": card.get("name"),
                "quantity": quantity,
                "deck_progress": self._get_deck_progress(deck_state)
            }
            
        except Exception as e:
            return {"error": str(e)}

    async def get_deck_summary(self, user_id: str) -> Dict[str, Any]:
        """Get current deck summary"""
        try:
            deck_state = self._get_or_create_deck_state(user_id, None)
            
            # Group cards by name and count
            card_summary = {}
            for card in deck_state.selected_cards:
                name = card.get("name", "Unknown")
                card_summary[name] = card_summary.get(name, 0) + 1
            
            return {
                "user_id": user_id,
                "deck_progress": self._get_deck_progress(deck_state),
                "selected_cards": card_summary,
                "conversation_state": self._deck_state_to_dict(deck_state)
            }
            
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
simple_deck_service = SimpleDeckBuildingService()


async def get_simple_deck_service() -> SimpleDeckBuildingService:
    """Get the simplified deck building service instance"""
    return simple_deck_service