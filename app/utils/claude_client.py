import asyncio
from typing import Dict, List, Optional, Any
from anthropic import AsyncAnthropic
from decouple import config
from ..services.conversation_service import ConversationState, DeckPhase
from ..database.card_queries import CardQueryBuilder


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
        return """You are an expert Pokemon Trading Card Game (TCG) deck building assistant with deep strategic knowledge and a passion for both competitive excellence and creative innovation. You understand the nuances of deck building, meta analysis, and can help users create everything from tier-1 competitive decks to innovative rogue strategies.

## Your Core Philosophy:
- **Strategic Excellence**: Provide deep, strategic insights based on solid TCG fundamentals
- **Creative Innovation**: Embrace unexpected strategies and card combinations
- **Natural Conversation**: Respond naturally without forcing rigid structure
- **Adaptive Guidance**: Adjust to user preferences for meta, rogue, or experimental decks
- **Competitive Knowledge**: Understand current meta and tournament considerations
- **Rule Compliance**: Always ensure decks follow official TCG rules

## Pokemon TCG Rules (Always Enforced):
- Standard deck must contain exactly 60 cards
- Maximum 4 copies of any card (except basic Energy)
- Unlimited basic Energy cards allowed
- Evolution chains: Basic → Stage 1 → Stage 2 (must include lower evolution stages)
- Energy types must match Pokemon attack requirements

## Strategic Deck Building Principles:

### **Core Deck Structure (Standard Guidelines):**
- **Pokemon (12-20 cards)**: 2-4 main attackers, 2-4 support Pokemon, evolution lines
- **Trainers (25-35 cards)**: Draw power, search, disruption, utility
- **Energy (10-15 cards)**: Basic energy + special energy as needed

### **Essential Card Categories:**
- **Draw Power**: Professor's Research, Pokegear, Colress's Experiment
- **Search**: Ultra Ball, Nest Ball, Quick Ball, Battle VIP Pass
- **Energy Acceleration**: Energy Search, Twin Energy, special energy
- **Disruption**: Judge, Marnie, Path to the Peak
- **Utility**: Switch, Escape Rope, Tool cards
- **Recovery**: Ordinary Rod, Super Rod, Rescue Carrier

### **Deck Archetypes & Strategies:**
- **Aggro/Rush**: Fast setup, early pressure, low energy costs
- **Control**: Disruption, resource denial, late game dominance
- **Combo**: Specific card interactions, engine-based strategies
- **Midrange**: Balanced approach, adaptable game plan
- **Toolbox**: Multiple options, situational responses
- **Mill/Stall**: Defensive, resource exhaustion, alternative win conditions

### **Energy Curve & Consistency:**
- **Turn 1-2**: Basic Pokemon, setup cards, energy attachment
- **Turn 3-4**: Evolution Pokemon, active attacking
- **Turn 5+**: Powerful attacks, game-ending moves
- **Energy Balance**: Match energy costs to acceleration available
- **Consistency**: 8-12 cards that find your key pieces

### **Meta Considerations:**
- **Speed**: How fast can you set up vs. opponents?
- **Consistency**: How reliably do you execute your game plan?
- **Disruption**: How do you handle opponent's strategy?
- **Prize Trade**: Are you taking efficient prize trades?
- **Bench Management**: Minimize easy prize targets
- **Type Matchups**: Weakness/resistance considerations

### **Advanced Strategic Concepts:**
- **Card Advantage**: Drawing more cards than you use
- **Tempo**: Controlling the pace of the game
- **Resource Management**: Energy, prizes, deck size
- **Threat Assessment**: Prioritizing which problems to solve
- **Win Conditions**: Primary and backup paths to victory
- **Deck Thinning**: Removing cards to increase draw quality

## Your Expertise Areas:
- **Meta Analysis**: Current competitive landscape and counter-strategies
- **Synergy Recognition**: Identifying powerful card combinations
- **Deck Optimization**: Improving consistency and power level
- **Alternative Strategies**: Finding untapped archetypes
- **Matchup Analysis**: Understanding favorable/unfavorable matchups
- **Tournament Preparation**: Sideboard strategies and meta calls

## Response Style:
- **Strategic**: Explain the reasoning behind recommendations
- **Enthusiastic**: Share genuine excitement about possibilities
- **Educational**: Teach underlying principles, not just card choices
- **Adaptive**: Match user's competitive level and interests
- **Thorough**: Provide detailed analysis when requested
- **Practical**: Focus on actionable deck building advice

## Special Capabilities:
- Analyze energy curves and consistency needs
- Suggest overlooked tech cards and counter-strategies
- Help optimize existing decks for competitive play
- Identify meta weaknesses and exploitation opportunities
- Balance innovation with competitive viability
- Provide matchup-specific advice and sideboard options

Remember: Great deck building combines solid fundamentals with creative innovation. Help users understand both the "why" and "how" behind strategic choices, whether they're building for local tournaments or world championships.

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

    async def generate_response_with_database_access(
        self,
        user_message: str,
        deck_state: Any,
        query_builder: CardQueryBuilder
    ) -> Dict[str, Any]:
        """Generate response with intelligent database querying"""
        
        # Execute intelligent search based on user message
        search_results = await self._execute_intelligent_search(
            user_message, query_builder
        )
        
        # DEBUG: Print search results
        print(f"DEBUG: Search found {len(search_results)} cards")
        if search_results:
            print(f"DEBUG: First card: {search_results[0].get('name', 'Unknown')}")
        
        # Generate response with found cards
        response = await self.generate_response(
            user_message,
            deck_state,
            search_results
        )
        
        return {
            "ai_response": response,
            "cards_found": search_results,
            "updated_deck_state": None
        }

    async def _execute_intelligent_search(
        self,
        user_message: str,
        query_builder: CardQueryBuilder
    ) -> List[Dict[str, Any]]:
        """Execute intelligent database searches based on user request"""
        
        all_results = []
        user_lower = user_message.lower()
        
        # Strategy 1: Text-based search for strategic concepts
        strategic_searches = {
            "spread damage": ["damage to each", "damage counters on each", "all opponent's pokemon", "each of your opponent's pokemon", "bench damage"],
            "draw power": ["draw cards", "draw until you have", "search your deck", "look at"],
            "energy acceleration": ["attach energy", "energy from your deck", "energy from your discard pile"],
            "disruption": ["discard", "shuffle", "opponent can't", "prevent", "choose a card"],
            "search": ["search your deck", "search your discard pile", "look at"]
        }
        
        # Check if user is asking for strategic cards
        found_strategic = False
        for strategy, keywords in strategic_searches.items():
            if strategy in user_lower or any(keyword in user_lower for keyword in keywords):
                try:
                    # Get broad sample to analyze
                    broad_results = query_builder.search_cards(limit=120)
                    filtered_results = [
                        card for card in broad_results.get("data", [])
                        if self._card_matches_strategy(card, strategy, keywords)
                    ]
                    all_results.extend(filtered_results)
                    found_strategic = True
                    break
                except:
                    continue
        
        # Strategy 2: Structured search based on detected card types
        if not found_strategic:
            try:
                pokemon_keywords = ["pokemon", "pokémon", "attacker", "basic", "stage", "ex", "gx", "v"]
                trainer_keywords = ["trainer", "support", "item", "stadium", "tool", "draw", "search"]
                energy_keywords = ["energy", "basic energy", "special energy"]
                
                if any(keyword in user_lower for keyword in pokemon_keywords):
                    pokemon_results = query_builder.search_cards(card_types=["Pokémon"], limit=80)
                    all_results.extend(pokemon_results.get("data", []))
                
                if any(keyword in user_lower for keyword in trainer_keywords):
                    trainer_results = query_builder.search_cards(card_types=["Trainer"], limit=60)
                    all_results.extend(trainer_results.get("data", []))
                
                if any(keyword in user_lower for keyword in energy_keywords):
                    energy_results = query_builder.search_cards(card_types=["Energy"], limit=20)
                    all_results.extend(energy_results.get("data", []))
            except:
                pass
        
        # Strategy 3: Broad search if no specific results
        if not all_results:
            try:
                broad_results = query_builder.search_cards(limit=100)
                all_results.extend(broad_results.get("data", []))
            except:
                pass
        
        # Remove duplicates and return top results
        seen_ids = set()
        unique_results = []
        for card in all_results:
            card_id = card.get("card_id")
            if card_id and card_id not in seen_ids:
                seen_ids.add(card_id)
                unique_results.append(card)
        
        return unique_results[:80]  # Return top 80 unique cards

    def _card_matches_strategy(self, card: Dict[str, Any], strategy: str, keywords: List[str]) -> bool:
        """Check if a card matches a strategic concept"""
        searchable_text = ""
        
        # Add attack text
        attacks = card.get("attacks", [])
        if attacks:
            for attack in attacks:
                if attack.get("text"):
                    searchable_text += attack["text"].lower() + " "
        
        # Add ability text
        abilities = card.get("abilities", [])
        if abilities:
            for ability in abilities:
                if ability.get("text"):
                    searchable_text += ability["text"].lower() + " "
        
        # Check for keyword matches
        if strategy == "spread damage":
            spread_phrases = [
                "damage to each", "damage counters on each", "all opponent's pokemon",
                "each of your opponent's pokemon", "bench damage", "damage to all",
                "each pokemon", "all pokemon"
            ]
            return any(phrase in searchable_text for phrase in spread_phrases)
        
        # Check for other strategies
        return any(keyword in searchable_text for keyword in keywords)

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