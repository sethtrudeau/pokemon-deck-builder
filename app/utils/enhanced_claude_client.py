"""
Enhanced Claude Client with Direct Database Access
Handles semantic understanding and intelligent querying
"""

import json
from typing import Dict, List, Optional, Any
from anthropic import AsyncAnthropic
from decouple import config

from ..database.card_queries import CardQueryBuilder


class EnhancedClaudeClient:
    """Claude client with direct database querying capabilities"""
    
    def __init__(self):
        self.api_key = config('CLAUDE_API_KEY', default='')
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY must be set in environment variables")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 3000

    def _build_enhanced_system_prompt(self) -> str:
        """Enhanced system prompt with database querying capabilities"""
        return """You are an expert Pokemon Trading Card Game (TCG) deck building assistant with direct access to a comprehensive database of current standard-legal Pokemon cards. You have deep strategic knowledge and can help users build competitive decks, discover innovative strategies, and find cards that match their specific needs.

## Your Capabilities:
- **Database Access**: You can query the Pokemon card database directly using various search strategies
- **Strategic Understanding**: You understand gameplay mechanics, card synergies, and competitive strategies
- **Semantic Search**: You can find cards based on their strategic function, not just name/type
- **Flexible Querying**: You can try multiple search approaches to find the best results

## Database Query Functions Available:
You can call these functions to search the database:

1. **search_cards(name=None, card_types=None, pokemon_types=None, hp_min=None, hp_max=None, subtypes=None, limit=100)**
   - Search by structured criteria
   - Example: search_cards(card_types=["Pokémon"], hp_min=100, limit=50)

2. **search_by_text(text_query, limit=100)**
   - Search within attack and ability descriptions
   - Example: search_by_text("damage to each", limit=50)

3. **get_all_cards(limit=200)**
   - Get a broad sample of cards for analysis
   - Use when you need to examine many cards for strategic matches

## Strategic Search Strategies:

### For Spread Damage Cards:
- Search for text like: "damage to each", "damage counters on each", "all opponent's Pokemon", "bench damage"
- Look for abilities/attacks that affect multiple targets

### For Draw Power Cards:
- Search for text like: "draw cards", "draw until you have", "search your deck"
- Look for Supporter cards and Pokemon abilities

### For Energy Acceleration:
- Search for text like: "attach energy", "energy from your deck", "energy acceleration"
- Look for abilities that help with energy management

### For Disruption:
- Search for text like: "discard", "shuffle", "opponent can't", "prevent"
- Look for cards that interfere with opponent's strategy

## Your Approach:
1. **Understand Intent**: Parse what the user really wants strategically
2. **Search Strategically**: Use multiple search methods to find relevant cards
3. **Analyze Results**: Examine card text for strategic relevance
4. **Provide Insights**: Explain why cards work well together
5. **Suggest Improvements**: Offer deck building advice and alternatives

## Pokemon TCG Rules (Always Enforce):
- Standard deck must contain exactly 60 cards
- Maximum 4 copies of any card (except basic Energy)
- Unlimited basic Energy cards allowed
- Evolution chains: Basic → Stage 1 → Stage 2 (include lower stages)
- Energy types must match Pokemon attack requirements

## Response Format:
Always provide:
- **Recommended Cards**: Specific cards that match the user's request
- **Strategic Reasoning**: Why these cards work for their strategy
- **Deck Building Advice**: How to build around these cards
- **Synergy Suggestions**: Other cards that work well together

## Critical Rules:
- Only recommend cards that exist in the database search results
- Always search the database before making recommendations
- If initial searches don't find good results, try alternative search strategies
- Explain your reasoning for card recommendations
- Consider competitive viability and current meta when relevant

Remember: You have the power to intelligently search the database and understand card interactions. Use this to provide the best possible deck building assistance."""

    async def generate_response_with_database_access(
        self,
        user_message: str,
        deck_state: Any,
        query_builder: CardQueryBuilder
    ) -> Dict[str, Any]:
        """Generate response with intelligent database querying"""
        
        # Build context about current deck state
        deck_context = self._build_deck_context(deck_state)
        
        # Create the full prompt
        system_prompt = self._build_enhanced_system_prompt()
        
        # Enhanced user context with database access instructions
        full_context = f"""
## Current Deck Context:
{deck_context}

## User Request:
{user_message}

## Database Query Instructions:
You have access to query the Pokemon card database. Use these strategies:

1. For strategic searches (like "spread damage"), use search_by_text() to find cards with relevant attack/ability text
2. For specific card types, use search_cards() with appropriate filters
3. For broad exploration, use get_all_cards() to get a diverse sample
4. Try multiple search strategies if the first doesn't yield good results

## Your Task:
1. Search the database intelligently based on the user's request
2. Analyze the results for strategic relevance
3. Provide specific card recommendations with reasoning
4. Explain how these cards fit into a cohesive deck strategy

Begin by searching the database for cards that match the user's request."""

        try:
            # First, let Claude understand the request and plan search strategy
            planning_response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"{full_context}\n\nFirst, analyze this request and tell me what database searches you would perform to find the best cards. Don't actually search yet, just plan your search strategy."
                    }
                ]
            )
            
            search_plan = planning_response.content[0].text
            
            # Now execute the planned searches
            search_results = await self._execute_intelligent_search(
                user_message, search_plan, query_builder
            )
            
            # Generate final response with search results
            final_response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"{full_context}\n\nSearch Plan: {search_plan}"
                    },
                    {
                        "role": "assistant",
                        "content": f"I'll execute this search plan: {search_plan}"
                    },
                    {
                        "role": "user",
                        "content": f"Here are the search results from the database:\n\n{self._format_search_results(search_results)}\n\nNow provide your deck building recommendations based on these results."
                    }
                ]
            )
            
            return {
                "ai_response": final_response.content[0].text,
                "cards_found": search_results,
                "search_plan": search_plan,
                "updated_deck_state": None  # Could be enhanced to track deck changes
            }
            
        except Exception as e:
            return {
                "ai_response": f"I apologize, but I encountered an error while searching the database: {str(e)}",
                "cards_found": [],
                "search_plan": "",
                "updated_deck_state": None
            }

    async def _execute_intelligent_search(
        self,
        user_message: str,
        search_plan: str,
        query_builder: CardQueryBuilder
    ) -> List[Dict[str, Any]]:
        """Execute intelligent database searches based on user request"""
        
        all_results = []
        user_lower = user_message.lower()
        
        # Strategy 1: Text-based search for strategic concepts
        strategic_keywords = [
            "spread damage", "damage to each", "damage counters on each",
            "all opponent's pokemon", "bench damage", "each pokemon",
            "draw power", "draw cards", "search deck", "search your deck",
            "energy acceleration", "attach energy", "energy from deck",
            "disruption", "discard", "shuffle", "prevent", "can't"
        ]
        
        for keyword in strategic_keywords:
            if keyword in user_lower:
                try:
                    # Search in attack text
                    attack_results = query_builder.search_cards(limit=100)
                    filtered_results = [
                        card for card in attack_results.get("data", [])
                        if self._card_matches_strategic_keyword(card, keyword)
                    ]
                    all_results.extend(filtered_results[:20])  # Top 20 matches
                    break
                except:
                    continue
        
        # Strategy 2: Structured search based on detected card types
        pokemon_keywords = ["pokemon", "pokémon", "attacker", "basic", "stage", "ex", "gx", "v"]
        trainer_keywords = ["trainer", "support", "item", "stadium", "tool", "draw", "search"]
        energy_keywords = ["energy", "basic energy", "special energy"]
        
        try:
            if any(keyword in user_lower for keyword in pokemon_keywords):
                pokemon_results = query_builder.search_cards(card_types=["Pokémon"], limit=60)
                all_results.extend(pokemon_results.get("data", []))
            
            if any(keyword in user_lower for keyword in trainer_keywords):
                trainer_results = query_builder.search_cards(card_types=["Trainer"], limit=40)
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

    def _card_matches_strategic_keyword(self, card: Dict[str, Any], keyword: str) -> bool:
        """Check if a card matches a strategic keyword"""
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
        if keyword == "spread damage":
            spread_phrases = [
                "damage to each", "damage counters on each", "all opponent's pokemon",
                "each of your opponent's pokemon", "bench damage", "damage to all"
            ]
            return any(phrase in searchable_text for phrase in spread_phrases)
        
        return keyword in searchable_text

    def _build_deck_context(self, deck_state: Any) -> str:
        """Build context string from deck state"""
        total_cards = len(deck_state.selected_cards)
        pokemon_count = len([c for c in deck_state.selected_cards if c.get("card_type") == "Pokémon"])
        trainer_count = len([c for c in deck_state.selected_cards if c.get("card_type") == "Trainer"])
        energy_count = len([c for c in deck_state.selected_cards if c.get("card_type") == "Energy"])
        
        context = f"""Current Deck ({total_cards}/60 cards):
- Pokemon: {pokemon_count} cards
- Trainers: {trainer_count} cards  
- Energy: {energy_count} cards
- Remaining: {60 - total_cards} cards to add"""
        
        if deck_state.deck_strategy:
            context += f"\nCurrent Strategy: {deck_state.deck_strategy}"
        
        if deck_state.selected_cards:
            context += "\nSelected Cards:"
            card_summary = {}
            for card in deck_state.selected_cards:
                name = card.get("name", "Unknown")
                card_summary[name] = card_summary.get(name, 0) + 1
            
            for name, count in sorted(card_summary.items()):
                context += f"\n- {count}x {name}"
        
        return context

    def _format_search_results(self, cards: List[Dict[str, Any]]) -> str:
        """Format search results for Claude analysis"""
        if not cards:
            return "No cards found in database search."
        
        formatted = f"Found {len(cards)} cards:\n\n"
        
        for i, card in enumerate(cards[:30], 1):  # Show top 30
            name = card.get("name", "Unknown")
            card_type = card.get("card_type", "Unknown")
            subtype = card.get("subtype", "")
            hp = card.get("hp", "")
            types = card.get("types", [])
            
            description = f"{i}. {name} - {card_type}"
            if subtype:
                description += f" ({subtype})"
            if hp:
                description += f" - {hp} HP"
            if types:
                description += f" - {', '.join(types)} type"
            
            # Add attack/ability info for strategic analysis
            attacks = card.get("attacks", [])
            abilities = card.get("abilities", [])
            
            if attacks:
                attack_names = [attack.get("name", "") for attack in attacks]
                description += f" | Attacks: {', '.join(attack_names)}"
            
            if abilities:
                ability_names = [ability.get("name", "") for ability in abilities]
                description += f" | Abilities: {', '.join(ability_names)}"
            
            formatted += description + "\n"
        
        if len(cards) > 30:
            formatted += f"\n... and {len(cards) - 30} more cards available for analysis."
        
        return formatted


# Enhanced singleton instance
enhanced_claude_client = EnhancedClaudeClient()


async def get_enhanced_claude_client() -> EnhancedClaudeClient:
    """Get the enhanced Claude client instance"""
    return enhanced_claude_client