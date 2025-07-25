from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime

from .conversation_service import ConversationService, ConversationState, DeckPhase, UserIntent
from ..utils.intent_analyzer import IntentAnalyzer, IntentType, FocusArea
from ..utils.claude_client import ClaudeClient
from ..database.card_queries import search_pokemon_cards, get_pokemon_card_by_id


class DeckBuildingService:
    """Main orchestration service that ties together all components"""
    
    def __init__(self):
        self.conversation_service = ConversationService()
        self.intent_analyzer = IntentAnalyzer()
        self.claude_client = ClaudeClient()

    async def process_user_message(self, user_id: str, message: str, deck_id: Optional[str] = None) -> Dict[str, Any]:
        """Main entry point for processing user messages"""
        try:
            # Load conversation state
            conversation_state = await self.conversation_service.load_conversation_state(user_id, deck_id)
            
            # Analyze user intent
            intent_analysis = self.intent_analyzer.analyze_intent(message, conversation_state.current_phase)
            
            # Initialize response structure
            response = {
                "user_id": user_id,
                "message": message,
                "intent": intent_analysis.intent_type.value,
                "focus_area": intent_analysis.focus_area.value,
                "current_phase": conversation_state.current_phase.value,
                "cards_found": [],
                "ai_response": "",
                "deck_progress": self._get_deck_progress(conversation_state),
                "phase_complete": False,
                "error": None
            }
            
            # Handle different intent types
            if intent_analysis.intent_type == IntentType.START_OVER:
                response = await self._handle_start_over(conversation_state, response)
            
            elif intent_analysis.intent_type == IntentType.ADD_CARDS:
                response = await self._handle_add_cards(conversation_state, intent_analysis, response)
            
            elif intent_analysis.intent_type == IntentType.REMOVE_CARDS:
                response = await self._handle_remove_cards(conversation_state, intent_analysis, response)
            
            elif intent_analysis.intent_type == IntentType.CONTINUE_BUILDING:
                response = await self._handle_continue_building(conversation_state, response)
            
            elif intent_analysis.intent_type == IntentType.ANALYZE_MATCHUP:
                response = await self._handle_analyze_matchup(conversation_state, response)
            
            elif intent_analysis.intent_type == IntentType.FINALIZE_DECK:
                response = await self._handle_finalize_deck(conversation_state, response)
            
            else:
                # Default conversation response
                response = await self._handle_general_conversation(conversation_state, message, response)
            
            # Map IntentType to UserIntent
            intent_mapping = {
                IntentType.ADD_CARDS: UserIntent.ADD_CARDS,
                IntentType.REMOVE_CARDS: UserIntent.REMOVE_CARDS,
                IntentType.CONTINUE_BUILDING: UserIntent.CONTINUE_BUILDING,
                IntentType.START_OVER: UserIntent.START_NEW_DECK,
                IntentType.ANALYZE_MATCHUP: UserIntent.ANALYZE_MATCHUPS,
                IntentType.FINALIZE_DECK: UserIntent.REVIEW_DECK,
                IntentType.UNKNOWN: UserIntent.UNKNOWN
            }
            
            # Update conversation state
            await self.conversation_service.update_conversation_state(
                conversation_state, message, intent_mapping.get(intent_analysis.intent_type, UserIntent.UNKNOWN), response.get("cards_found", [])
            )
            
            # Add conversation state to response
            response["conversation_state"] = self.conversation_service.get_conversation_state_dict(conversation_state)
            
            return response
            
        except Exception as e:
            return {
                "user_id": user_id,
                "message": message,
                "intent": "unknown",
                "focus_area": "general",
                "current_phase": "strategy",
                "cards_found": [],
                "ai_response": "I apologize, but I encountered an error processing your request. Please try again.",
                "deck_progress": {"total_cards": 0, "cards_by_type": {"Pokemon": 0, "Trainer": 0, "Energy": 0}, "cards_remaining": 60, "phase_completion": {}, "deck_strategy": None},
                "phase_complete": False,
                "conversation_state": {"user_id": user_id, "current_phase": "strategy", "selected_cards": [], "conversation_history": []},
                "error": str(e)
            }

    async def _handle_start_over(self, conversation_state: ConversationState, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle starting over with a new deck"""
        # Reset conversation state
        conversation_state.current_phase = DeckPhase.STRATEGY
        conversation_state.selected_cards = []
        conversation_state.deck_strategy = None
        conversation_state.phase_completion = {phase: False for phase in conversation_state.phase_completion}
        
        # Generate AI response
        response["ai_response"] = await self.claude_client.generate_response(
            "I want to start over with a new deck",
            conversation_state
        )
        
        response["current_phase"] = DeckPhase.STRATEGY.value
        response["deck_progress"] = self._get_deck_progress(conversation_state)
        
        return response

    async def _handle_add_cards(self, conversation_state: ConversationState, intent_analysis, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle adding cards to the deck"""
        response["cards_found"] = []
        
        try:
            # Use intelligent query generation to understand what user wants
            query_params = await self.conversation_service.generate_database_query(
                response["message"], intent_analysis.intent_type, conversation_state
            )
            
            # Try the intelligent search first
            search_results = await search_pokemon_cards(**query_params)
            response["cards_found"] = search_results.get("data", [])
            
            # If no results, try broader search but keep card type if detected
            if not response["cards_found"]:
                fallback_params = {
                    "limit": 80,
                    "offset": 0
                }
                if "card_types" in query_params:
                    fallback_params["card_types"] = query_params["card_types"]
                
                fallback_results = await search_pokemon_cards(**fallback_params)
                response["cards_found"] = fallback_results.get("data", [])
            
            # Generate AI response with card recommendations
            response["ai_response"] = await self.claude_client.generate_card_recommendations(
                conversation_state,
                response["cards_found"]
            )
            
        except Exception as e:
            # Fallback to general response
            response["ai_response"] = await self.claude_client.generate_response(
                response["message"],
                conversation_state
            )
        
        return response

    async def _handle_remove_cards(self, conversation_state: ConversationState, intent_analysis, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle removing cards from the deck"""
        # Extract card names to remove
        cards_to_remove = intent_analysis.extracted_card_names
        
        if cards_to_remove:
            # Remove cards from selected_cards
            original_count = len(conversation_state.selected_cards)
            conversation_state.selected_cards = [
                card for card in conversation_state.selected_cards 
                if card.get("name", "").lower() not in [name.lower() for name in cards_to_remove]
            ]
            removed_count = original_count - len(conversation_state.selected_cards)
            
            response["ai_response"] = await self.claude_client.generate_response(
                f"I removed {removed_count} cards from your deck: {', '.join(cards_to_remove)}",
                conversation_state
            )
        else:
            response["ai_response"] = await self.claude_client.generate_response(
                response["message"],
                conversation_state
            )
        
        response["deck_progress"] = self._get_deck_progress(conversation_state)
        return response

    async def _handle_continue_building(self, conversation_state: ConversationState, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle continuing to build the deck"""
        response["cards_found"] = []
        
        try:
            # Get phase-appropriate cards using intelligent query generation
            intent_analysis = self.intent_analyzer.analyze_intent(response["message"], conversation_state.current_phase)
            
            # Generate a query based on current phase to get relevant cards
            query_params = await self.conversation_service.generate_database_query(
                response["message"], intent_analysis.intent_type, conversation_state
            )
            
            # Try intelligent search based on phase
            search_results = await search_pokemon_cards(**query_params)
            response["cards_found"] = search_results.get("data", [])
            
            # If no results, get cards appropriate for current phase
            if not response["cards_found"]:
                fallback_params = {"limit": 80, "offset": 0}
                
                if conversation_state.current_phase == DeckPhase.CORE_POKEMON:
                    fallback_params["card_types"] = ["Pokémon"]
                elif conversation_state.current_phase == DeckPhase.SUPPORT:
                    fallback_params["card_types"] = ["Trainer"]
                elif conversation_state.current_phase == DeckPhase.ENERGY:
                    fallback_params["card_types"] = ["Energy"]
                
                fallback_results = await search_pokemon_cards(**fallback_params)
                response["cards_found"] = fallback_results.get("data", [])
                
        except Exception as e:
            response["cards_found"] = []
        
        # Generate flexible response based on current deck state with actual cards
        response["ai_response"] = await self.claude_client.generate_response(
            response["message"],
            conversation_state,
            response.get("cards_found", [])
        )
        
        # Optionally progress phase if user explicitly wants to move forward
        if any(keyword in response["message"].lower() for keyword in ["next phase", "move on", "continue to"]):
            next_phase = self.conversation_service.phase_progression.get(conversation_state.current_phase)
            if next_phase and next_phase != conversation_state.current_phase:
                conversation_state.current_phase = next_phase
                response["current_phase"] = next_phase.value
                response["phase_complete"] = True
        
        return response

    async def _handle_analyze_matchup(self, conversation_state: ConversationState, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle matchup analysis"""
        response["ai_response"] = await self.claude_client.analyze_deck_matchups(
            conversation_state,
            "Analyze competitive viability and common matchups"
        )
        
        return response

    async def _handle_finalize_deck(self, conversation_state: ConversationState, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle finalizing the deck"""
        conversation_state.current_phase = DeckPhase.COMPLETE
        response["current_phase"] = DeckPhase.COMPLETE.value
        response["phase_complete"] = True
        
        response["ai_response"] = await self.claude_client.generate_response(
            "I want to finalize my deck",
            conversation_state
        )
        
        return response

    async def _handle_general_conversation(self, conversation_state: ConversationState, message: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general conversation with intelligent card search"""
        response["cards_found"] = []
        
        try:
            # Strategy 1: Use the improved query generation to understand what user wants
            intent_analysis = self.intent_analyzer.analyze_intent(message, conversation_state.current_phase)
            
            query_params = await self.conversation_service.generate_database_query(
                message, intent_analysis.intent_type, conversation_state
            )
            
            # Try the intelligent search first
            search_results = await search_pokemon_cards(**query_params)
            response["cards_found"] = search_results.get("data", [])
            
            # Strategy 2: If no results, try a broader search but still respecting card type if detected
            if not response["cards_found"]:
                # Remove specific filters but keep card type if it was detected
                fallback_params = {
                    "limit": 80,
                    "offset": 0
                }
                if "card_types" in query_params:
                    fallback_params["card_types"] = query_params["card_types"]
                
                fallback_results = await search_pokemon_cards(**fallback_params)
                response["cards_found"] = fallback_results.get("data", [])
            
            # Strategy 3: If still no cards, try basic search with high limit
            if not response["cards_found"]:
                basic_results = await search_pokemon_cards(limit=100)
                response["cards_found"] = basic_results.get("data", [])
                
        except Exception as e:
            # Final fallback: try simple search
            try:
                fallback_results = await search_pokemon_cards(limit=50)
                response["cards_found"] = fallback_results.get("data", [])
            except:
                response["cards_found"] = []
        
        # Generate AI response with found cards
        response["ai_response"] = await self.claude_client.generate_response(
            message,
            conversation_state,
            response.get("cards_found", [])
        )
        
        return response

    def _get_deck_progress(self, conversation_state: ConversationState) -> Dict[str, Any]:
        """Get current deck progress summary"""
        total_cards = len(conversation_state.selected_cards)
        
        card_counts = {"Pokemon": 0, "Trainer": 0, "Energy": 0}
        for card in conversation_state.selected_cards:
            card_type = card.get("card_type", "Unknown")
            if card_type in card_counts:
                card_counts[card_type] += 1
        
        return {
            "total_cards": total_cards,
            "cards_by_type": card_counts,
            "cards_remaining": 60 - total_cards,
            "phase_completion": conversation_state.phase_completion,
            "deck_strategy": conversation_state.deck_strategy
        }

    async def add_card_to_deck(self, user_id: str, card_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Add a specific card to the user's deck"""
        try:
            # Load conversation state
            conversation_state = await self.conversation_service.load_conversation_state(user_id)
            
            # Get card details
            card = await get_pokemon_card_by_id(card_id)
            if not card:
                return {"error": "Card not found"}
            
            # Check deck rules (max 4 copies, max 60 cards)
            current_count = sum(1 for c in conversation_state.selected_cards if c.get("id") == card_id)
            if current_count + quantity > 4:
                return {"error": "Maximum 4 copies of any card allowed"}
            
            if len(conversation_state.selected_cards) + quantity > 60:
                return {"error": "Deck cannot exceed 60 cards"}
            
            # Add cards to deck
            for _ in range(quantity):
                conversation_state.selected_cards.append(card)
            
            # Update conversation state
            await self.conversation_service.update_conversation_state(
                conversation_state, f"Added {quantity}x {card.get('name', 'Unknown')}", IntentType.ADD_CARDS
            )
            
            return {
                "success": True,
                "card_added": card.get("name"),
                "quantity": quantity,
                "deck_progress": self._get_deck_progress(conversation_state)
            }
            
        except Exception as e:
            return {"error": str(e)}

    async def get_deck_summary(self, user_id: str) -> Dict[str, Any]:
        """Get current deck summary"""
        try:
            conversation_state = await self.conversation_service.load_conversation_state(user_id)
            
            # Group cards by name and count
            card_summary = {}
            for card in conversation_state.selected_cards:
                name = card.get("name", "Unknown")
                card_summary[name] = card_summary.get(name, 0) + 1
            
            return {
                "user_id": user_id,
                "current_phase": conversation_state.current_phase.value,
                "deck_progress": self._get_deck_progress(conversation_state),
                "selected_cards": card_summary,
                "conversation_state": self.conversation_service.get_conversation_state_dict(conversation_state)
            }
            
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
deck_building_service = DeckBuildingService()


async def get_deck_building_service() -> DeckBuildingService:
    """Get the deck building service instance"""
    return deck_building_service