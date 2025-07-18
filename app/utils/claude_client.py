import asyncio
from typing import Dict, List, Optional, Any
from anthropic import AsyncAnthropic
from decouple import config
from ..services.conversation_service import ConversationState, DeckPhase
from ..database.card_queries import CardQueryBuilder
from .memory_cache import get_memory_cache_manager, MemoryCache


class ClaudeClient:
    def __init__(self):
        self.api_key = config('CLAUDE_API_KEY', default='')
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY must be set in environment variables")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 4000

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Pokemon deck building"""
        return """You are a master Pokemon TCG deck building strategist with decades of competitive experience. When a user asks for cards with specific capabilities, you analyze ALL available options comprehensively before making strategic recommendations.

## Your Approach:
1. **Synergy Discovery**: Look for powerful interactions and combinations between cards first
2. **Strategic Foundations**: Build deck concepts around these synergies
3. **Comprehensive Analysis**: Review ALL cards for additional synergy potential
4. **Deck Architecture**: Design complete strategies around key synergies
5. **Competitive Refinement**: Optimize synergy-based decks for tournament play

## Response Structure:
When providing deck building advice, always:

### **Synergy Identification:**
- Look for powerful interactions between cards in the search results
- Identify unique combinations that create strategic advantages
- Find overlooked synergies that others might miss
- Prioritize combinations that multiply card effectiveness

### **Synergy-Based Deck Concepts:**
- Build deck archetypes around the strongest synergies discovered
- Explain how each synergy creates a win condition or strategic advantage
- Show how synergistic cards work together to form a coherent strategy
- Present multiple synergy-based approaches using the available cards

### **Complete Deck Architecture:**
- Design full 60-card strategies around key synergies
- Recommend supporting cards needed to enable synergies
- Explain energy requirements and consistency needs for synergy execution
- Suggest specific counts that maximize synergistic potential

### **Synergy Optimization:**
- Identify ways to make synergies more consistent and powerful
- Suggest tech cards that enhance or protect key synergies
- Discuss how to adapt synergies against different meta matchups
- Recommend timing and sequencing for complex synergistic plays

## Key Principles:
- **Synergy-First**: Start with card interactions, not individual card analysis
- **Pattern Recognition**: Identify connections others might miss across the entire card pool
- **Strategic Innovation**: Create unique deck concepts based on discovered synergies
- **Educational**: Explain how synergies work and why they're powerful
- **Practical**: Provide actionable deck lists built around synergistic foundations
- **Comprehensive**: Analyze ALL cards for synergy potential, not just obvious choices

## Pokemon TCG Rules (Always Enforced):
- Standard deck must contain exactly 60 cards
- Maximum 4 copies of any card (except basic Energy)
- Unlimited basic Energy cards allowed
- Evolution chains: Basic → Stage 1 → Stage 2 (must include lower stages)
- Energy types must match Pokemon attack requirements

**CRITICAL CONSTRAINT**: You can recommend cards from TWO sources:
1. **Latest Database Search Results** - Cards from the user's most recent query
2. **Card Discovery Memory** - All cards discovered in previous searches this session

This memory system allows you to build complete 60-card decks by accumulating cards across multiple queries. Always reference both sources when making recommendations."""

    def _build_conversation_context(self, conversation_state: ConversationState, available_cards: Optional[List[Dict[str, Any]]] = None, memory_cache: Optional[MemoryCache] = None) -> str:
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
        
        # Memory cache summary for cumulative discovery
        if memory_cache:
            cache_summary = memory_cache.get_cache_summary()
            context_parts.append(f"## Card Discovery Memory:\n{cache_summary}")
            
            # Show synergy opportunities from cached cards
            synergies = memory_cache.identify_synergies()
            if synergies:
                context_parts.append("## Discovered Synergy Opportunities:")
                for tag, cards in list(synergies.items())[:3]:  # Show top 3 synergies
                    context_parts.append(f"- **{tag.replace('_', ' ').title()}**: {', '.join(cards[:5])}")
                    if len(cards) > 5:
                        context_parts.append(f"  (+{len(cards) - 5} more cards with this synergy)")
        
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
        
        # Available cards from comprehensive database search
        if available_cards:
            context_parts.append(f"## Latest Database Search Results ({len(available_cards)} cards found):")
            context_parts.append("**These are the cards from your most recent search query.**")
            context_parts.append("**IMPORTANT: You can recommend cards from this list AND from your Card Discovery Memory above.**")
            
            # Show ALL cards found, not just first 50
            for i, card in enumerate(available_cards, 1):
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
                
        else:
            context_parts.append("## No New Cards Found:")
            context_parts.append("No cards matched your latest search. But you can still work with previously discovered cards from your Card Discovery Memory!")
        
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
        custom_context: Optional[str] = None,
        memory_cache: Optional[MemoryCache] = None
    ) -> str:
        """Generate conversational response using Claude"""
        
        system_prompt = self._build_system_prompt()
        conversation_context = self._build_conversation_context(conversation_state, available_cards, memory_cache)
        
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
        query_builder: CardQueryBuilder,
        user_id: str = None,
        deck_id: str = None
    ) -> Dict[str, Any]:
        """Generate response with intelligent database querying and memory cache"""
        
        # Get or create memory cache for this user
        cache_manager = get_memory_cache_manager()
        memory_cache = cache_manager.get_cache(user_id or "anonymous", deck_id)
        
        # DEBUG: Print cache state before search
        print(f"DEBUG: Memory cache has {len(memory_cache.discovered_cards)} cards before search")
        
        # Execute intelligent search based on user message
        search_results = await self._execute_intelligent_search(
            user_message, query_builder
        )
        
        # Add new search results to memory cache
        if search_results:
            cache_manager.add_cards_to_cache(
                user_id or "anonymous", 
                search_results, 
                user_message, 
                deck_id
            )
        
        # Update strategy context if provided
        if deck_state.deck_strategy:
            cache_manager.update_strategy_context(
                user_id or "anonymous", 
                deck_state.deck_strategy, 
                deck_id
            )
        
        # DEBUG: Print search results
        print(f"DEBUG: Search found {len(search_results)} new cards")
        print(f"DEBUG: Memory cache now has {len(memory_cache.discovered_cards)} total cards")
        if search_results:
            print(f"DEBUG: First 5 new cards: {[card.get('name', 'Unknown') for card in search_results[:5]]}")
        else:
            print("DEBUG: No new cards found in search!")
        
        # Generate response with found cards and memory cache
        response = await self.generate_response(
            user_message,
            deck_state,
            search_results,
            memory_cache=memory_cache
        )
        
        return {
            "ai_response": response,
            "cards_found": search_results,
            "updated_deck_state": None,
            "memory_cache_summary": memory_cache.get_cache_summary(),
            "total_discovered_cards": len(memory_cache.discovered_cards)
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
                    # Get broad sample to analyze - try multiple pages
                    print(f"DEBUG: Detected strategy '{strategy}' - searching for cards...")
                    all_broad_results = []
                    
                    # Get ALL standard legal cards across multiple pages
                    page = 0
                    while True:
                        offset = page * 1000
                        print(f"DEBUG: Fetching page {page + 1} with offset {offset}")
                        broad_results = query_builder.search_cards(limit=1000, offset=offset)
                        page_cards = broad_results.get("data", [])
                        
                        if not page_cards:  # No more results
                            print(f"DEBUG: No more cards found on page {page + 1}")
                            break
                            
                        all_broad_results.extend(page_cards)
                        print(f"DEBUG: Page {page + 1}: Got {len(page_cards)} cards (total so far: {len(all_broad_results)})")
                        
                        if len(page_cards) < 1000:  # Last page
                            print(f"DEBUG: Reached end of results on page {page + 1}")
                            break
                            
                        page += 1
                        
                        # Safety limit to prevent infinite loops
                        if page > 10:  # Max 10,000 cards
                            print("DEBUG: Hit safety limit of 10 pages")
                            break
                    
                    print(f"DEBUG: Total cards to analyze: {len(all_broad_results)}")
                    filtered_results = [
                        card for card in all_broad_results
                        if self._card_matches_strategy(card, strategy, keywords)
                    ]
                    print(f"DEBUG: Filtered down to {len(filtered_results)} cards matching strategy")
                    all_results.extend(filtered_results)
                    found_strategic = True
                    break
                except Exception as e:
                    print(f"DEBUG: Error in strategic search: {e}")
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
            found_match = any(phrase in searchable_text for phrase in spread_phrases)
            if found_match:
                print(f"DEBUG: Found spread damage card: {card.get('name', 'Unknown')}")
            return found_match
        
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