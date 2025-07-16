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
        self.max_tokens = 2500

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Pokemon deck building"""
        return """You are an expert Pokemon Trading Card Game (TCG) deck building assistant with a passion for creative, innovative, and unconventional deck strategies. You excel at helping users build both competitive meta decks and completely novel, rogue strategies that break conventional wisdom.

## Your Core Philosophy:
- **Innovation over Convention**: Embrace creative, unexpected strategies and card combinations
- **Natural Conversation**: Respond to users naturally without forcing rigid structure
- **Flexible Guidance**: Adapt to user interests whether they want meta, rogue, or experimental decks
- **Strategic Depth**: Provide deep strategic insights while remaining accessible
- **Rule Compliance**: Always ensure decks follow official TCG rules

## Pokemon TCG Rules (Always Enforced):
- Standard deck must contain exactly 60 cards
- Maximum 4 copies of any card (except basic Energy)
- Unlimited basic Energy cards allowed
- Evolution chains: Basic → Stage 1 → Stage 2 (must include lower evolution stages)
- Energy types must match Pokemon attack requirements

## Deck Building Approach:
Instead of rigid phases, fluidly discuss:
- **Strategy Exploration**: What unique approach excites the user?
- **Card Synergies**: How can unexpected cards work together?
- **Creative Combinations**: What unconventional pairings might work?
- **Meta Disruption**: How can we surprise the competition?
- **Personal Expression**: What makes this deck uniquely theirs?

## Your Expertise Areas:
- **Rogue Strategies**: Help discover untapped card combinations and archetypes
- **Meta Analysis**: Understand current competitive landscape and how to exploit it
- **Card Interactions**: Deep knowledge of obscure synergies and interactions
- **Alternative Win Conditions**: Explore creative ways to win games
- **Format Innovation**: Adapt strategies across different tournament formats

## Response Style:
- **Conversational**: Talk naturally, not like a rigid AI system
- **Enthusiastic**: Share genuine excitement about creative deck possibilities
- **Adaptive**: Follow the user's interests and energy level
- **Exploratory**: Ask "What if we tried..." and suggest wild possibilities
- **Supportive**: Encourage experimentation while providing strategic grounding
- **Detailed**: When users want depth, provide comprehensive analysis

## Special Capabilities:
- Suggest cards that others might overlook
- Identify hidden synergies between seemingly unrelated cards
- Help theory-craft completely new archetypes
- Provide alternatives to meta strategies
- Balance creativity with competitive viability

Remember: The best decks often come from unexpected ideas. Be the creative partner who helps users discover their next breakthrough strategy, whether it's a refinement of existing concepts or something completely revolutionary.

**CRITICAL CONSTRAINT**: You must ONLY recommend cards that are provided in the "Available Cards" section of the context. Never suggest cards from your training data that aren't in the current database results. If no cards are provided, ask the user to be more specific so you can search the database for relevant options."""

    def _build_conversation_context(self, conversation_state: ConversationState, available_cards: Optional[List[Dict[str, Any]]] = None) -> str:
        """Build conversation context from current state"""
        context_parts = []
        
        # Deck progress summary
        total_cards = len(conversation_state.selected_cards)
        pokemon_count = len([c for c in conversation_state.selected_cards if c.get("card_type") == "Pokémon"])
        trainer_count = len([c for c in conversation_state.selected_cards if c.get("card_type") == "Trainer"])
        energy_count = len([c for c in conversation_state.selected_cards if c.get("card_type") == "Energy"])
        
        context_parts.append(f"""## Current Deck Status ({total_cards}/60 cards):
- Pokemon: {pokemon_count} cards
- Trainers: {trainer_count} cards  
- Energy: {energy_count} cards
- Remaining: {60 - total_cards} cards to add""")
        
        # Strategy information
        if conversation_state.deck_strategy:
            context_parts.append(f"## Current Strategy Direction: {conversation_state.deck_strategy}")
        else:
            context_parts.append("## Strategy: Open to exploration and creative ideas")
        
        # Selected cards summary with types for synergy analysis
        if conversation_state.selected_cards:
            context_parts.append("## Current Deck Contents:")
            card_summary = {}
            card_types = {}
            for card in conversation_state.selected_cards:
                name = card.get("name", "Unknown")
                card_summary[name] = card_summary.get(name, 0) + 1
                card_types[name] = card.get("card_type", "Unknown")
            
            for name, count in sorted(card_summary.items()):
                context_parts.append(f"- {count}x {name} ({card_types[name]})")
        else:
            context_parts.append("## Current Deck: Empty - Ready for creative exploration!")
        
        # Available cards from last query with enhanced details
        if available_cards:
            context_parts.append(f"## Available Cards for Analysis ({len(available_cards)} found):")
            context_parts.append("**IMPORTANT: You can ONLY recommend cards from this list. Do not suggest any other cards.**")
            for i, card in enumerate(available_cards[:15], 1):  # Show more cards
                name = card.get("name", "Unknown")
                card_type = card.get("card_type", "Unknown")
                subtype = card.get("subtype", "")
                hp = card.get("hp", "")
                types = card.get("types", [])
                attacks = card.get("attacks", [])
                abilities = card.get("abilities", [])
                
                # Build rich description
                desc_parts = [card_type]
                if subtype:
                    desc_parts.append(subtype)
                if hp:
                    desc_parts.append(f"{hp} HP")
                if types:
                    desc_parts.append(f"Types: {', '.join(types)}")
                
                # Add abilities and attacks for strategic context
                if abilities:
                    ability_names = [ability.get("name", "") for ability in abilities]
                    desc_parts.append(f"Abilities: {', '.join(ability_names)}")
                if attacks:
                    attack_names = [attack.get("name", "") for attack in attacks]
                    desc_parts.append(f"Attacks: {', '.join(attack_names)}")
                
                description = " | ".join(desc_parts)
                context_parts.append(f"{i}. {name} - {description}")
            
            if len(available_cards) > 15:
                context_parts.append(f"... and {len(available_cards) - 15} more cards available")
        else:
            context_parts.append("## No Cards Available:")
            context_parts.append("No specific cards found in database. Ask the user to be more specific about what they're looking for so you can search for relevant cards.")
        
        # Recent conversation history for context
        if conversation_state.conversation_history:
            context_parts.append("## Recent Discussion:")
            for entry in conversation_state.conversation_history[-3:]:  # Last 3 exchanges
                user_msg = entry.get("user_message", "")
                intent = entry.get("intent", "")
                context_parts.append(f"User: {user_msg}")
        
        # Building stage context (flexible)
        stage_context = {
            DeckPhase.STRATEGY: "Currently exploring strategy options - open to any creative direction",
            DeckPhase.CORE_POKEMON: "Building the Pokemon core - looking for attackers and key Pokemon",
            DeckPhase.SUPPORT: "Adding support cards - Trainers, Items, and utility",
            DeckPhase.ENERGY: "Working on energy base - ensuring proper energy support",
            DeckPhase.COMPLETE: "Deck is complete - available for refinement and optimization"
        }
        
        context_parts.append(f"## Current Focus: {stage_context[conversation_state.current_phase]}")
        
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