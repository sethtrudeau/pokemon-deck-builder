import asyncio
from typing import Dict, List, Optional, Any
from anthropic import AsyncAnthropic
from decouple import config
from ..services.conversation_service import ConversationState, DeckPhase


class ClaudeClient:
    def __init__(self):
        self.api_key = config('CLAUDE_API_KEY', default='')
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY must be set in environment variables")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 1500

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Pokemon deck building"""
        return """You are an expert Pokemon Trading Card Game (TCG) deck building assistant. Your role is to help users build competitive and fun Pokemon decks while following official TCG rules and providing strategic guidance.

## Pokemon TCG Rules & Constraints:
- Standard deck must contain exactly 60 cards
- Maximum 4 copies of any card (except basic Energy)
- Unlimited basic Energy cards allowed
- Evolution chains: Basic → Stage 1 → Stage 2 (must include lower evolution stages)
- Energy types must match Pokemon attack requirements
- Include mix of Pokemon (12-20), Trainers (20-35), and Energy (8-15)

## Deck Building Phases:
1. **Strategy**: Define deck archetype (Aggro, Control, Combo, Midrange)
2. **Core Pokemon**: Select main attackers and key Pokemon (8-12 cards)
3. **Support**: Add Trainer cards for draw, search, and utility (20-35 cards)  
4. **Energy**: Add appropriate Energy cards (8-15 cards)
5. **Complete**: Finalize and optimize the 60-card deck

## Your Responsibilities:
- Guide users through each phase systematically
- Suggest cards that synergize with their strategy
- Ensure deck follows TCG rules and card limits
- Provide strategic reasoning for card choices
- Help balance consistency vs. power
- Consider meta-game and matchup analysis when requested

## Response Style:
- Be enthusiastic and knowledgeable about Pokemon
- Explain card synergies and strategic value
- Ask clarifying questions to understand user preferences
- Provide multiple options when possible
- Keep responses concise but informative
- Focus on the current phase while considering overall deck strategy

Always prioritize deck legality, strategic coherence, and fun gameplay experience."""

    def _build_conversation_context(self, conversation_state: ConversationState, available_cards: Optional[List[Dict[str, Any]]] = None) -> str:
        """Build conversation context from current state"""
        context_parts = []
        
        # Current phase and progress
        context_parts.append(f"## Current Building Phase: {conversation_state.current_phase.value.title()}")
        
        # Deck progress summary
        total_cards = len(conversation_state.selected_cards)
        pokemon_count = len([c for c in conversation_state.selected_cards if c.get("card_type") == "Pokémon"])
        trainer_count = len([c for c in conversation_state.selected_cards if c.get("card_type") == "Trainer"])
        energy_count = len([c for c in conversation_state.selected_cards if c.get("card_type") == "Energy"])
        
        context_parts.append(f"""## Current Deck Progress ({total_cards}/60 cards):
- Pokemon: {pokemon_count} cards
- Trainers: {trainer_count} cards  
- Energy: {energy_count} cards""")
        
        # Strategy information
        if conversation_state.deck_strategy:
            context_parts.append(f"## Deck Strategy: {conversation_state.deck_strategy}")
        
        # Selected cards summary
        if conversation_state.selected_cards:
            context_parts.append("## Currently Selected Cards:")
            card_summary = {}
            for card in conversation_state.selected_cards:
                name = card.get("name", "Unknown")
                card_summary[name] = card_summary.get(name, 0) + 1
            
            for name, count in sorted(card_summary.items()):
                context_parts.append(f"- {count}x {name}")
        
        # Phase completion status
        completed_phases = [phase for phase, completed in conversation_state.phase_completion.items() if completed]
        if completed_phases:
            context_parts.append(f"## Completed Phases: {', '.join(completed_phases)}")
        
        # Available cards from last query
        if available_cards:
            context_parts.append(f"## Available Cards Found ({len(available_cards)} results):")
            for i, card in enumerate(available_cards[:10], 1):  # Show first 10
                name = card.get("name", "Unknown")
                card_type = card.get("card_type", "Unknown")
                hp = card.get("hp", "")
                hp_text = f" ({hp} HP)" if hp else ""
                context_parts.append(f"{i}. {name} - {card_type}{hp_text}")
            
            if len(available_cards) > 10:
                context_parts.append(f"... and {len(available_cards) - 10} more cards")
        
        # Recent conversation history
        if conversation_state.conversation_history:
            context_parts.append("## Recent Conversation:")
            for entry in conversation_state.conversation_history[-3:]:  # Last 3 exchanges
                timestamp = entry.get("timestamp", "")
                user_msg = entry.get("user_message", "")
                intent = entry.get("intent", "")
                context_parts.append(f"User ({intent}): {user_msg}")
        
        # Phase-specific guidance
        phase_guidance = {
            DeckPhase.STRATEGY: "Focus on defining the deck's main strategy and win condition.",
            DeckPhase.CORE_POKEMON: "Select primary Pokemon attackers and key support Pokemon.",
            DeckPhase.SUPPORT: "Add Trainer cards for draw power, search, and strategic support.",
            DeckPhase.ENERGY: "Add Energy cards to power your Pokemon's attacks.",
            DeckPhase.COMPLETE: "Review and optimize the completed deck."
        }
        
        context_parts.append(f"## Current Phase Guidance: {phase_guidance[conversation_state.current_phase]}")
        
        return "\n\n".join(context_parts)

    async def generate_response(
        self, 
        user_message: str, 
        conversation_state: ConversationState,
        available_cards: Optional[List[Dict[str, Any]]] = None,
        custom_context: Optional[str] = None
    ) -> str:
        """Generate conversational response using Claude"""
        
        system_prompt = self._build_system_prompt()
        conversation_context = self._build_conversation_context(conversation_state, available_cards)
        
        # Build the full context
        full_context = conversation_context
        if custom_context:
            full_context += f"\n\n## Additional Context:\n{custom_context}"
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"{full_context}\n\n## User Message:\n{user_message}"
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"I apologize, but I'm having trouble generating a response right now. Error: {str(e)}"

    async def generate_card_recommendations(
        self,
        conversation_state: ConversationState,
        available_cards: List[Dict[str, Any]],
        max_recommendations: int = 5
    ) -> str:
        """Generate specific card recommendations based on current deck state"""
        
        context = f"""Analyze these available cards for the user's deck and recommend the top {max_recommendations} cards that would best fit their current strategy and phase.

Consider:
- Synergy with existing cards
- Phase requirements (currently in {conversation_state.current_phase.value})
- TCG deck building best practices
- Strategic value and consistency

Provide a numbered list with brief explanations for each recommendation."""
        
        return await self.generate_response(
            "Please recommend the best cards from the available options for my deck.",
            conversation_state,
            available_cards,
            context
        )

    async def analyze_deck_matchups(self, conversation_state: ConversationState, meta_context: str = "") -> str:
        """Analyze deck matchups and provide strategic advice"""
        
        context = f"""Analyze the current deck for competitive viability and matchups.

{meta_context}

Consider:
- Strengths and weaknesses
- Common meta matchups
- Potential improvements
- Strategic positioning"""
        
        return await self.generate_response(
            "Can you analyze my deck's matchups and competitive potential?",
            conversation_state,
            custom_context=context
        )

    async def get_phase_transition_advice(self, conversation_state: ConversationState) -> str:
        """Get advice for transitioning to the next phase"""
        
        next_phase = conversation_state.current_phase
        if conversation_state.current_phase != DeckPhase.COMPLETE:
            next_phase_mapping = {
                DeckPhase.STRATEGY: DeckPhase.CORE_POKEMON,
                DeckPhase.CORE_POKEMON: DeckPhase.SUPPORT,
                DeckPhase.SUPPORT: DeckPhase.ENERGY,
                DeckPhase.ENERGY: DeckPhase.COMPLETE
            }
            next_phase = next_phase_mapping[conversation_state.current_phase]
        
        context = f"The user is ready to move from {conversation_state.current_phase.value} phase to {next_phase.value} phase. Provide guidance for this transition and what to focus on next."
        
        return await self.generate_response(
            "I'm ready to move to the next phase of deck building.",
            conversation_state,
            custom_context=context
        )


# Singleton instance
claude_client = ClaudeClient()


async def get_claude_client() -> ClaudeClient:
    """Get the Claude client instance"""
    return claude_client