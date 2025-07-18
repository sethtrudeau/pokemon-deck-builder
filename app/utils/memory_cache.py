#!/usr/bin/env python3
"""
Dynamic Memory Cache for Pokemon Deck Builder
Accumulates discovered cards across multiple queries to help build complete decks
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import hashlib


@dataclass
class CardDiscovery:
    """Represents a discovered card with search context"""
    card_id: str
    card_data: Dict[str, Any]
    discovered_at: datetime
    search_context: str  # The user query that discovered this card
    relevance_score: float = 0.0  # How relevant this card is to the current strategy
    synergy_tags: List[str] = field(default_factory=list)  # Tags for synergy tracking
    
    def __post_init__(self):
        # Extract key card info for easy access
        self.name = self.card_data.get('name', 'Unknown')
        self.card_type = self.card_data.get('card_type', 'Unknown')
        self.types = self.card_data.get('types', [])
        self.subtype = self.card_data.get('subtype', '')


@dataclass
class MemoryCache:
    """Dynamic memory cache for accumulated card discoveries"""
    user_id: str
    deck_id: Optional[str] = None
    discovered_cards: Dict[str, CardDiscovery] = field(default_factory=dict)
    search_history: List[str] = field(default_factory=list)
    strategy_context: str = ""
    synergy_patterns: Dict[str, List[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_discovered_cards(self, cards: List[Dict[str, Any]], search_context: str) -> List[CardDiscovery]:
        """Add newly discovered cards to the cache"""
        new_discoveries = []
        
        for card in cards:
            card_id = card.get('card_id')
            if not card_id:
                continue
                
            # Create or update card discovery
            discovery = CardDiscovery(
                card_id=card_id,
                card_data=card,
                discovered_at=datetime.now(),
                search_context=search_context,
                relevance_score=self._calculate_relevance(card, search_context)
            )
            
            # Extract synergy tags
            discovery.synergy_tags = self._extract_synergy_tags(card)
            
            self.discovered_cards[card_id] = discovery
            new_discoveries.append(discovery)
        
        # Update search history
        self.search_history.append(search_context)
        if len(self.search_history) > 20:  # Keep last 20 searches
            self.search_history = self.search_history[-20:]
        
        self.last_updated = datetime.now()
        return new_discoveries
    
    def get_cards_by_type(self, card_type: str) -> List[CardDiscovery]:
        """Get all discovered cards of a specific type"""
        return [discovery for discovery in self.discovered_cards.values() 
                if discovery.card_type == card_type]
    
    def get_cards_by_synergy(self, synergy_tag: str) -> List[CardDiscovery]:
        """Get cards that match a specific synergy pattern"""
        return [discovery for discovery in self.discovered_cards.values() 
                if synergy_tag in discovery.synergy_tags]
    
    def get_top_cards_by_relevance(self, limit: int = 20) -> List[CardDiscovery]:
        """Get the most relevant discovered cards"""
        sorted_cards = sorted(self.discovered_cards.values(), 
                            key=lambda x: x.relevance_score, reverse=True)
        return sorted_cards[:limit]
    
    def get_deck_progress(self) -> Dict[str, Any]:
        """Get current deck building progress"""
        cards_by_type = {
            'Pokémon': len(self.get_cards_by_type('Pokémon')),
            'Trainer': len(self.get_cards_by_type('Trainer')),
            'Energy': len(self.get_cards_by_type('Energy'))
        }
        
        total_discovered = len(self.discovered_cards)
        synergy_count = len(self.synergy_patterns)
        
        return {
            'total_discovered': total_discovered,
            'cards_by_type': cards_by_type,
            'synergy_patterns': synergy_count,
            'deck_completion': min(100, (total_discovered / 60) * 100),
            'search_count': len(self.search_history)
        }
    
    def identify_synergies(self) -> Dict[str, List[str]]:
        """Identify potential synergies between discovered cards"""
        synergies = {}
        
        # Group cards by synergy tags
        tag_groups = {}
        for discovery in self.discovered_cards.values():
            for tag in discovery.synergy_tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(discovery.name)
        
        # Find synergy patterns with multiple cards
        for tag, card_names in tag_groups.items():
            if len(card_names) >= 2:
                synergies[tag] = card_names
        
        self.synergy_patterns = synergies
        return synergies
    
    def suggest_next_search(self) -> Optional[str]:
        """Suggest what type of cards to search for next"""
        progress = self.get_deck_progress()
        cards_by_type = progress['cards_by_type']
        
        # Prioritize based on deck building phases
        if cards_by_type['Pokémon'] < 10:
            return "Focus on finding more Pokémon attackers and support Pokémon"
        elif cards_by_type['Trainer'] < 15:
            return "Search for Trainer cards - draw power, search, and utility"
        elif cards_by_type['Energy'] < 8:
            return "Add Energy cards to power your Pokémon attacks"
        elif progress['total_discovered'] < 60:
            return "Look for synergistic cards that work well with your current discoveries"
        else:
            return "Consider refining your deck by finding better alternatives"
    
    def _calculate_relevance(self, card: Dict[str, Any], search_context: str) -> float:
        """Calculate relevance score for a card based on search context and strategy"""
        score = 1.0
        
        # Boost score if card type matches search context
        card_type = card.get('card_type', '').lower()
        if card_type in search_context.lower():
            score += 0.5
        
        # Boost score if card has abilities or attacks (more strategic value)
        if card.get('abilities') and len(card['abilities']) > 0:
            score += 0.3
        if card.get('attacks') and len(card['attacks']) > 0:
            score += 0.2
        
        # Boost score if card matches strategy context
        if self.strategy_context:
            strategy_lower = self.strategy_context.lower()
            card_name_lower = card.get('name', '').lower()
            if any(word in card_name_lower for word in strategy_lower.split()):
                score += 0.4
        
        # Boost score for cards with synergy potential
        synergy_tags = self._extract_synergy_tags(card)
        if synergy_tags:
            score += 0.2 * len(synergy_tags)
        
        return score
    
    def _extract_synergy_tags(self, card: Dict[str, Any]) -> List[str]:
        """Extract synergy tags from a card"""
        tags = []
        
        # Type-based synergies
        types = card.get('types', [])
        for ptype in types:
            tags.append(f"type_{ptype.lower()}")
        
        # Ability-based synergies
        abilities = card.get('abilities', [])
        for ability in abilities:
            ability_text = ability.get('text', '').lower()
            if 'draw' in ability_text:
                tags.append('draw_power')
            if 'search' in ability_text:
                tags.append('search_effect')
            if 'energy' in ability_text:
                tags.append('energy_acceleration')
            if 'damage' in ability_text:
                tags.append('damage_synergy')
        
        # Attack-based synergies
        attacks = card.get('attacks', [])
        for attack in attacks:
            attack_text = attack.get('text', '').lower()
            if 'each' in attack_text and 'pokemon' in attack_text:
                tags.append('spread_damage')
            if 'discard' in attack_text:
                tags.append('discard_synergy')
            if 'switch' in attack_text:
                tags.append('switch_synergy')
        
        # Subtype-based synergies
        subtype = card.get('subtype', '')
        if subtype:
            tags.append(f"subtype_{subtype.lower().replace(' ', '_')}")
        
        return tags
    
    def get_cache_summary(self) -> str:
        """Get a human-readable summary of the cache state"""
        progress = self.get_deck_progress()
        synergies = self.identify_synergies()
        
        summary = f"""
## Memory Cache Summary
- **Total Cards Discovered**: {progress['total_discovered']}
- **Pokémon**: {progress['cards_by_type']['Pokémon']}
- **Trainers**: {progress['cards_by_type']['Trainer']}
- **Energy**: {progress['cards_by_type']['Energy']}
- **Deck Completion**: {progress['deck_completion']:.1f}%
- **Synergy Patterns**: {len(synergies)}
- **Searches Performed**: {progress['search_count']}

"""
        
        if synergies:
            summary += "### Discovered Synergies:\n"
            for tag, cards in list(synergies.items())[:5]:  # Show top 5
                summary += f"- **{tag.replace('_', ' ').title()}**: {', '.join(cards[:3])}"
                if len(cards) > 3:
                    summary += f" (+{len(cards) - 3} more)"
                summary += "\n"
        
        next_suggestion = self.suggest_next_search()
        if next_suggestion:
            summary += f"\n### Next Search Suggestion:\n{next_suggestion}"
        
        return summary.strip()


class MemoryCacheManager:
    """Manages memory caches for different users/decks"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.caches: Dict[str, MemoryCache] = {}
            self.cache_timeout = timedelta(hours=6)  # Caches expire after 6 hours
            self._initialized = True
    
    def get_cache(self, user_id: str, deck_id: Optional[str] = None) -> MemoryCache:
        """Get or create a memory cache for a user/deck"""
        cache_key = f"{user_id}_{deck_id or 'default'}"
        
        # Check if cache exists and is not expired
        if cache_key in self.caches:
            cache = self.caches[cache_key]
            if datetime.now() - cache.last_updated < self.cache_timeout:
                return cache
            else:
                # Remove expired cache
                del self.caches[cache_key]
        
        # Create new cache
        cache = MemoryCache(user_id=user_id, deck_id=deck_id)
        self.caches[cache_key] = cache
        return cache
    
    def add_cards_to_cache(self, user_id: str, cards: List[Dict[str, Any]], 
                          search_context: str, deck_id: Optional[str] = None) -> MemoryCache:
        """Add discovered cards to the user's cache"""
        cache = self.get_cache(user_id, deck_id)
        cache.add_discovered_cards(cards, search_context)
        return cache
    
    def update_strategy_context(self, user_id: str, strategy: str, deck_id: Optional[str] = None):
        """Update the strategy context for better relevance scoring"""
        cache = self.get_cache(user_id, deck_id)
        cache.strategy_context = strategy
        cache.last_updated = datetime.now()
    
    def clear_cache(self, user_id: str, deck_id: Optional[str] = None):
        """Clear a user's cache"""
        cache_key = f"{user_id}_{deck_id or 'default'}"
        if cache_key in self.caches:
            del self.caches[cache_key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about all caches"""
        return {
            'total_caches': len(self.caches),
            'active_caches': len([c for c in self.caches.values() 
                                if datetime.now() - c.last_updated < self.cache_timeout]),
            'total_cards_cached': sum(len(c.discovered_cards) for c in self.caches.values()),
            'cache_keys': list(self.caches.keys())
        }


# Global cache manager instance - singleton
_memory_cache_manager = None


def get_memory_cache_manager() -> MemoryCacheManager:
    """Get the global memory cache manager singleton"""
    global _memory_cache_manager
    if _memory_cache_manager is None:
        _memory_cache_manager = MemoryCacheManager()
    return _memory_cache_manager