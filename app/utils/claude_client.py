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
        return """You are a master Pokemon TCG deck building strategist who guides users through a deliberate, multi-step building process. You NEVER attempt to build a complete 60-card deck from the first input. Instead, you follow a structured progression that ensures optimal deck construction.

## Multi-Step Building Process (ALWAYS FOLLOW):

### **Phase 1: Core Engine Discovery** (First Priority)
**NEVER skip this phase - it's the foundation of every great deck**
- Identify 2-3 Pokemon that form the deck's primary win condition
- Focus on the most powerful synergistic interactions between these core cards
- Explain how these Pokemon create a cohesive strategy
- Suggest specific card counts for the core engine (typically 6-12 cards total)
- Ask the user if they want to explore this core engine further or see alternatives

### **Phase 2: Critical Support Infrastructure** (Second Priority)
**Only proceed here AFTER establishing the core engine**
- Add essential support Pokemon that enable or enhance the core strategy
- Include key trainer cards for consistency (draw, search, utility)
- Recommend energy requirements to power the core engine
- Suggest 15-25 additional cards that directly support the core strategy
- Explain how each addition strengthens the core engine's effectiveness

### **Phase 3: Consistency & Optimization** (Final Priority)
**Only proceed here AFTER core engine + critical support are established**
- Fine-tune card counts for optimal consistency
- Add tech cards for specific matchups or meta considerations
- Complete the remaining slots to reach exactly 60 cards
- Optimize the energy base and ensure proper ratios
- Provide the final, complete deck list with explanations

## Response Guidelines by Phase:

### **Phase 1 Responses (Initial Queries):**
- Present 2-4 core engine options with clear synergy explanations
- Keep recommendations focused (8-15 cards maximum)
- End with: "Which core engine interests you most, or would you like to see other options?"
- NEVER proceed to Phase 2 without user confirmation
- If user selects a core engine, acknowledge it and move to Phase 2

### **Phase 2 Responses (User Selected Core Engine):**
- Build on the user's chosen core engine from Phase 1
- Add 15-25 supporting cards with clear roles defined
- Include essential trainer cards, support Pokemon, and basic energy needs
- Explain how each addition serves the core strategy
- End with: "How does this support package look? Ready to optimize for consistency?"
- NEVER jump to a complete 60-card list until Phase 3

### **Phase 3 Responses (User Ready for Final Optimization):**
- Present the complete, optimized 60-card deck list
- Provide detailed explanations for final card choices and counts
- Include mulligan strategy and key interactions
- Offer alternative tech options for different meta considerations
- Only proceed here when user explicitly confirms they're ready for the complete deck

## Phase Detection Guidelines:
- **Phase 1**: User asks about deck ideas, strategies, or hasn't chosen a core yet
- **Phase 2**: User has selected/confirmed a core engine and wants to build on it
- **Phase 3**: User explicitly asks for complete deck, final optimization, or says "ready to optimize"

## Core Principles:
- **Progressive Building**: Each phase builds deliberately on the previous one
- **User Collaboration**: Always confirm direction before advancing phases
- **Strategic Focus**: Maintain clear connection to the core engine throughout
- **Educational**: Explain the reasoning behind each phase's additions
- **Patience**: Never rush to complete lists - the process creates better decks

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
        
        # Memory cache with full card details for cumulative discovery
        if memory_cache and len(memory_cache.discovered_cards) > 0:
            cache_summary = memory_cache.get_cache_summary()
            context_parts.append(f"## Card Discovery Memory:\n{cache_summary}")
            
            # Show ALL previously discovered cards with full details
            context_parts.append(f"## All Previously Discovered Cards ({len(memory_cache.discovered_cards)} total):")
            context_parts.append("**These are ALL cards found in previous searches. You can recommend any of these cards.**")
            
            # Group cards by search context for better organization
            cards_by_search = {}
            for card_id, discovery in memory_cache.discovered_cards.items():
                search_context = discovery.search_context
                if search_context not in cards_by_search:
                    cards_by_search[search_context] = []
                cards_by_search[search_context].append(discovery)
            
            # Show cards organized by search context
            for search_context, discoveries in cards_by_search.items():
                context_parts.append(f"### From search: \"{search_context}\" ({len(discoveries)} cards)")
                for i, discovery in enumerate(discoveries[:20], 1):  # Show first 20 per search
                    card = discovery.card_data
                    name = card.get("name", "Unknown")
                    card_type = card.get("card_type", "Unknown")
                    subtype = card.get("subtype", "")
                    hp = card.get("hp", "")
                    types = card.get("types", [])
                    
                    # Build description
                    desc_parts = [card_type]
                    if subtype:
                        desc_parts.append(subtype)
                    if hp:
                        desc_parts.append(f"{hp} HP")
                    if types:
                        desc_parts.append(f"Types: {', '.join(types)}")
                    
                    description = " | ".join(desc_parts)
                    context_parts.append(f"  {i}. {name} - {description}")
                
                if len(discoveries) > 20:
                    context_parts.append(f"  ... and {len(discoveries) - 20} more cards")
            
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
        
        # Decide whether to do a new search or use existing cache
        should_search = self._should_perform_new_search(user_message, memory_cache)
        
        search_results = []
        if should_search:
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
        else:
            print("DEBUG: Skipping search - using existing memory cache")
        
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
        # Note: Pass search_results as the "latest" search, but Claude will have access to full memory cache
        response = await self.generate_response(
            user_message,
            deck_state,
            search_results,
            memory_cache=memory_cache
        )
        
        return {
            "ai_response": response,
            "cards_found": search_results,  # Latest search results
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

    def _should_perform_new_search(self, user_message: str, memory_cache: MemoryCache) -> bool:
        """Determine if we should perform a new database search or use existing cache"""
        message_lower = user_message.lower()
        
        # Always search if cache is empty
        if len(memory_cache.discovered_cards) == 0:
            return True
        
        # Search for specific card names
        if any(keyword in message_lower for keyword in ['show me', 'find', 'search for', 'get', 'need']):
            # Check if we're looking for a specific card type we don't have
            progress = memory_cache.get_deck_progress()
            cards_by_type = progress['cards_by_type']
            
            # Need trainer cards and don't have many
            if ('trainer' in message_lower or 'support' in message_lower or 'item' in message_lower) and cards_by_type.get('Trainer', 0) < 10:
                return True
            
            # Need energy cards and don't have many
            if 'energy' in message_lower and cards_by_type.get('Energy', 0) < 5:
                return True
            
            # Need Pokemon cards and don't have many
            if ('pokemon' in message_lower or 'attacker' in message_lower) and cards_by_type.get('Pokémon', 0) < 20:
                return True
            
            # New strategic search (haven't searched for this strategy before)
            strategic_keywords = ['spread damage', 'draw power', 'energy acceleration', 'disruption', 'stall']
            for strategy in strategic_keywords:
                if strategy in message_lower:
                    # Check if we've searched for this strategy before
                    previous_searches = memory_cache.search_history
                    if not any(strategy in prev_search.lower() for prev_search in previous_searches):
                        return True
        
        # Questions about existing cards - don't search
        if any(keyword in message_lower for keyword in ['what', 'how', 'can you', 'build', 'recommend', 'suggest']):
            return False
        
        # Default to not searching if we have a good cache
        return len(memory_cache.discovered_cards) < 60

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