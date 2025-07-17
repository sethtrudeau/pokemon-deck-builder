from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime

from ..database.card_queries import search_pokemon_cards, get_available_filters


class DeckPhase(Enum):
    STRATEGY = "strategy"
    CORE_POKEMON = "core_pokemon"
    SUPPORT = "support"
    ENERGY = "energy"
    COMPLETE = "complete"


class UserIntent(Enum):
    ADD_CARDS = "add_cards"
    REMOVE_CARDS = "remove_cards"
    ANALYZE_MATCHUPS = "analyze_matchups"
    CONTINUE_BUILDING = "continue_building"
    START_NEW_DECK = "start_new_deck"
    REVIEW_DECK = "review_deck"
    UNKNOWN = "unknown"


@dataclass
class ConversationState:
    user_id: str
    deck_id: Optional[str] = None
    current_phase: DeckPhase = DeckPhase.STRATEGY
    deck_strategy: Optional[str] = None
    selected_cards: List[Dict[str, Any]] = None
    conversation_history: List[Dict[str, Any]] = None
    last_query_filters: Dict[str, Any] = None
    phase_completion: Dict[str, bool] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.selected_cards is None:
            self.selected_cards = []
        if self.conversation_history is None:
            self.conversation_history = []
        if self.last_query_filters is None:
            self.last_query_filters = {}
        if self.phase_completion is None:
            self.phase_completion = {
                "strategy": False,
                "core_pokemon": False,
                "support": False,
                "energy": False,
                "complete": False
            }
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class ConversationService:
    def __init__(self):
        self.intent_keywords = {
            UserIntent.ADD_CARDS: [
                "add", "include", "put", "want", "need", "search", "find", "show me",
                "looking for", "get", "select", "choose", "pick"
            ],
            UserIntent.REMOVE_CARDS: [
                "remove", "delete", "take out", "don't want", "drop", "exclude",
                "get rid of", "discard", "replace"
            ],
            UserIntent.ANALYZE_MATCHUPS: [
                "matchup", "counter", "weakness", "strength", "meta", "competitive",
                "tournament", "analysis", "strategy", "against"
            ],
            UserIntent.CONTINUE_BUILDING: [
                "continue", "next", "proceed", "keep going", "move on", "what's next",
                "done with", "finished", "complete"
            ],
            UserIntent.START_NEW_DECK: [
                "new deck", "start over", "fresh", "begin", "create", "build new",
                "different deck", "another deck"
            ],
            UserIntent.REVIEW_DECK: [
                "review", "check", "look at", "show deck", "current deck", "what do I have",
                "deck list", "summary"
            ]
        }

        self.phase_progression = {
            DeckPhase.STRATEGY: DeckPhase.CORE_POKEMON,
            DeckPhase.CORE_POKEMON: DeckPhase.SUPPORT,
            DeckPhase.SUPPORT: DeckPhase.ENERGY,
            DeckPhase.ENERGY: DeckPhase.COMPLETE,
            DeckPhase.COMPLETE: DeckPhase.COMPLETE
        }

    async def load_conversation_state(self, user_id: str, deck_id: Optional[str] = None) -> ConversationState:
        """Load conversation state from storage or create new one"""
        # TODO: Implement actual storage (Redis, database, etc.)
        # For now, create a new state
        return ConversationState(
            user_id=user_id,
            deck_id=deck_id,
            current_phase=DeckPhase.STRATEGY
        )

    async def analyze_user_intent(self, user_message: str, conversation_state: ConversationState) -> UserIntent:
        """Analyze user message to determine intent"""
        message_lower = user_message.lower()
        
        # Check for specific patterns first
        if re.search(r'\b(add|include|want|need)\b.*\b(card|pokemon)\b', message_lower):
            return UserIntent.ADD_CARDS
        
        if re.search(r'\b(remove|delete|take out)\b.*\b(card|pokemon)\b', message_lower):
            return UserIntent.REMOVE_CARDS
        
        if re.search(r'\b(new|start|create)\b.*\bdeck\b', message_lower):
            return UserIntent.START_NEW_DECK
        
        if re.search(r'\b(continue|next|proceed|done)\b', message_lower):
            return UserIntent.CONTINUE_BUILDING
        
        # Score-based intent detection
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        
        # Default based on current phase
        if conversation_state.current_phase == DeckPhase.STRATEGY:
            return UserIntent.CONTINUE_BUILDING
        else:
            return UserIntent.ADD_CARDS

    async def generate_database_query(self, user_message: str, intent: UserIntent, conversation_state: ConversationState) -> Dict[str, Any]:
        """Generate database query parameters based on user message and intent"""
        query_params = {
            "limit": 80,  # Increased for comprehensive search results
            "offset": 0
        }
        
        # Check for strategic keywords that require broader searches
        strategic_keywords = [
            "spread damage", "spread", "bench damage", "all pokemon", "each pokemon",
            "draw power", "search", "acceleration", "disruption", "stall",
            "ability", "attack", "effect", "synergy", "combo"
        ]
        
        has_strategic_intent = any(keyword in message_lower for keyword in strategic_keywords)
        if has_strategic_intent:
            # For strategic searches, use minimal filters to get broad results
            # Let the AI analyze the full card set for strategic matches
            return {"limit": 120, "offset": 0}
        
        message_lower = user_message.lower()
        
        # FIRST: Detect what TYPE of cards the user wants based on their message
        card_type_detected = False
        
        # Check for Pokemon card requests
        pokemon_keywords = ["pokemon", "pokémon", "attacker", "basic", "stage 1", "stage 2", "evolution", "ex", "gx", "v", "vmax", "vstar"]
        if any(keyword in message_lower for keyword in pokemon_keywords):
            query_params["card_types"] = ["Pokémon"]
            card_type_detected = True
        
        # Check for Trainer card requests
        trainer_keywords = ["trainer", "support", "item", "stadium", "supporter", "tool", "draw", "search"]
        if any(keyword in message_lower for keyword in trainer_keywords):
            query_params["card_types"] = ["Trainer"]
            card_type_detected = True
        
        # Check for Energy card requests
        energy_keywords = ["energy", "basic energy", "special energy"]
        if any(keyword in message_lower for keyword in energy_keywords):
            query_params["card_types"] = ["Energy"]
            card_type_detected = True
        
        # Check for Pokemon type mentions (fire, water, etc.) - these imply Pokemon cards
        type_patterns = {
            r'\bfire\b': ["Fire"],
            r'\bwater\b': ["Water"],
            r'\bgrass\b': ["Grass"],
            r'\belectric\b': ["Lightning"],
            r'\blightning\b': ["Lightning"],
            r'\bpsychic\b': ["Psychic"],
            r'\bfighting\b': ["Fighting"],
            r'\bdarkness\b': ["Darkness"],
            r'\bmetal\b': ["Metal"],
            r'\bfairy\b': ["Fairy"],
            r'\bdragon\b': ["Dragon"],
            r'\bcolorless\b': ["Colorless"]
        }
        
        for type_pattern, type_values in type_patterns.items():
            if re.search(type_pattern, message_lower):
                query_params["pokemon_types"] = type_values
                # If user mentions pokemon types, they want Pokemon cards
                if not card_type_detected:
                    query_params["card_types"] = ["Pokémon"]
                    card_type_detected = True
                break
        
        # FALLBACK: If no specific card type detected, use phase-based filtering
        if not card_type_detected:
            if conversation_state.current_phase == DeckPhase.CORE_POKEMON:
                query_params["card_types"] = ["Pokémon"]
            elif conversation_state.current_phase == DeckPhase.SUPPORT:
                query_params["card_types"] = ["Trainer"]
            elif conversation_state.current_phase == DeckPhase.ENERGY:
                query_params["card_types"] = ["Energy"]
        
        # Extract specific card name from message (but not for strategic searches)
        if not has_strategic_intent:
            name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', user_message)
            if name_match:
                potential_name = name_match.group(1)
                # Filter out common words
                common_words = {"Pokemon", "Card", "Deck", "Strategy", "Energy", "Trainer", "Show", "Some", "Find", "Spread", "Damage", "Attack", "Ability"}
                if potential_name not in common_words:
                    query_params["name"] = potential_name
        
        # Extract HP range
        hp_match = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\s*hp', user_message.lower())
        if hp_match:
            query_params["hp_min"] = int(hp_match.group(1))
            query_params["hp_max"] = int(hp_match.group(2))
        else:
            # Single HP value
            hp_single = re.search(r'(\d+)\s*hp', user_message.lower())
            if hp_single:
                hp_value = int(hp_single.group(1))
                query_params["hp_min"] = hp_value - 20
                query_params["hp_max"] = hp_value + 20
        
        # Extract subtypes - use word boundaries to avoid partial matches
        subtype_patterns = {
            r'\bbasic\b': ["Basic"],
            r'\bstage 1\b': ["Stage 1"],
            r'\bstage 2\b': ["Stage 2"],
            r'\bex\b': ["Pokémon ex"],
            r'\bgx\b': ["Pokémon GX"],
            r'\bv\b': ["Pokémon V"],
            r'\bvmax\b': ["Pokémon VMAX"],
            r'\bsupporter\b': ["Supporter"],
            r'\bitem\b': ["Item"],
            r'\bstadium\b': ["Stadium"],
            r'\btool\b': ["Pokémon Tool"]
        }
        
        for subtype_pattern, subtype_values in subtype_patterns.items():
            if re.search(subtype_pattern, user_message.lower()):
                query_params["subtypes"] = subtype_values
                break
        
        return query_params

    async def update_conversation_state(self, conversation_state: ConversationState, user_message: str, intent: UserIntent, query_results: Optional[Dict[str, Any]] = None) -> ConversationState:
        """Update conversation state based on user interaction"""
        # Add to conversation history
        conversation_state.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "intent": intent.value,
            "phase": conversation_state.current_phase.value
        })
        
        # Handle different intents
        if intent == UserIntent.ADD_CARDS and query_results:
            # Store the results for user selection
            conversation_state.last_query_filters = query_results
            
        elif intent == UserIntent.CONTINUE_BUILDING:
            # Progress to next phase if current phase is complete
            if self._is_phase_complete(conversation_state):
                conversation_state.current_phase = self.phase_progression[conversation_state.current_phase]
                conversation_state.phase_completion[conversation_state.current_phase.value] = False
        
        elif intent == UserIntent.START_NEW_DECK:
            # Reset to strategy phase
            conversation_state.current_phase = DeckPhase.STRATEGY
            conversation_state.selected_cards = []
            conversation_state.deck_strategy = None
            conversation_state.phase_completion = {phase: False for phase in conversation_state.phase_completion}
        
        # Update timestamp
        conversation_state.updated_at = datetime.now()
        
        return conversation_state

    def _is_phase_complete(self, conversation_state: ConversationState) -> bool:
        """Check if current phase is complete based on selected cards"""
        if conversation_state.current_phase == DeckPhase.STRATEGY:
            return conversation_state.deck_strategy is not None
        
        elif conversation_state.current_phase == DeckPhase.CORE_POKEMON:
            pokemon_cards = [card for card in conversation_state.selected_cards 
                           if card.get("card_type") == "Pokémon"]
            return len(pokemon_cards) >= 8  # Minimum core Pokemon
        
        elif conversation_state.current_phase == DeckPhase.SUPPORT:
            trainer_cards = [card for card in conversation_state.selected_cards 
                           if card.get("card_type") == "Trainer"]
            return len(trainer_cards) >= 10  # Minimum support cards
        
        elif conversation_state.current_phase == DeckPhase.ENERGY:
            energy_cards = [card for card in conversation_state.selected_cards 
                          if card.get("card_type") == "Energy"]
            total_cards = len(conversation_state.selected_cards)
            return len(energy_cards) >= 8 and total_cards >= 60  # Standard deck requirements
        
        return False

    async def get_phase_suggestions(self, conversation_state: ConversationState) -> List[str]:
        """Get suggestions for the current phase"""
        phase_suggestions = {
            DeckPhase.STRATEGY: [
                "What type of deck strategy are you interested in? (Aggro, Control, Combo)",
                "Which Pokemon types do you want to focus on?",
                "Are you building for casual play or competitive tournaments?"
            ],
            DeckPhase.CORE_POKEMON: [
                "Let's add your main Pokemon attackers",
                "What Pokemon do you want as your primary strategy?",
                "Consider adding Pokemon with different attack costs"
            ],
            DeckPhase.SUPPORT: [
                "Now let's add Trainer cards for support",
                "You'll need draw power and search cards",
                "Consider adding Pokemon tools and stadiums"
            ],
            DeckPhase.ENERGY: [
                "Time to add Energy cards",
                "How many basic Energy do you need?",
                "Do you want any special Energy cards?"
            ],
            DeckPhase.COMPLETE: [
                "Your deck is complete!",
                "Would you like to review your deck?",
                "Ready to test your deck or make adjustments?"
            ]
        }
        
        return phase_suggestions.get(conversation_state.current_phase, [])

    def get_conversation_state_dict(self, conversation_state: ConversationState) -> Dict[str, Any]:
        """Convert conversation state to dictionary for storage/API responses"""
        return {
            "user_id": conversation_state.user_id,
            "deck_id": conversation_state.deck_id,
            "current_phase": conversation_state.current_phase.value,
            "deck_strategy": conversation_state.deck_strategy,
            "selected_cards": conversation_state.selected_cards,
            "conversation_history": conversation_state.conversation_history[-10:],  # Last 10 messages
            "phase_completion": conversation_state.phase_completion,
            "updated_at": conversation_state.updated_at.isoformat()
        }