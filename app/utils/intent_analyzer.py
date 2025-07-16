import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from ..services.conversation_service import DeckPhase


class IntentType(Enum):
    CONTINUE_BUILDING = "continue_building"
    START_OVER = "start_over"
    ADD_CARDS = "add_cards"
    REMOVE_CARDS = "remove_cards"
    ANALYZE_MATCHUP = "analyze_matchup"
    FINALIZE_DECK = "finalize_deck"
    UNKNOWN = "unknown"


class FocusArea(Enum):
    POKEMON = "pokemon"
    TRAINERS = "trainers"
    ENERGY = "energy"
    STRATEGY = "strategy"
    SPECIFIC_CARD = "specific_card"
    GENERAL = "general"


@dataclass
class IntentAnalysis:
    intent_type: IntentType
    focus_area: FocusArea
    extracted_card_names: List[str]
    extracted_pokemon_types: List[str]
    extracted_attributes: Dict[str, Any]
    needs_database_query: bool
    confidence_score: float
    reasoning: str


class IntentAnalyzer:
    def __init__(self):
        self.intent_patterns = {
            IntentType.CONTINUE_BUILDING: [
                r'\b(continue|next|proceed|move on|keep going|done|finished|complete)\b',
                r'\b(ready for|move to|go to)\s+(next|support|energy|pokemon)\b',
                r'\b(what\'s next|next phase|next step)\b'
            ],
            IntentType.START_OVER: [
                r'\b(start over|restart|begin again|new deck|fresh start)\b',
                r'\b(delete everything|clear deck|reset)\b',
                r'\b(different strategy|change direction)\b'
            ],
            IntentType.ADD_CARDS: [
                r'\b(add|include|want|need|search|find|show|get|looking for)\b',
                r'\b(put in|add to deck|include in deck)\b',
                r'\b(suggest|recommend|what about)\b'
            ],
            IntentType.REMOVE_CARDS: [
                r'\b(remove|delete|take out|drop|exclude|get rid of)\b',
                r'\b(don\'t want|not interested|too many)\b',
                r'\b(replace|swap|change)\b'
            ],
            IntentType.ANALYZE_MATCHUP: [
                r'\b(matchup|counter|weakness|strength|meta|competitive)\b',
                r'\b(tournament|analysis|strategy|against|vs)\b',
                r'\b(how does.*perform|good against|weak to)\b'
            ],
            IntentType.FINALIZE_DECK: [
                r'\b(finalize|complete|finish|done building|ready to test)\b',
                r'\b(deck is ready|finished deck|complete deck)\b',
                r'\b(review|check|validate|is this good)\b'
            ]
        }

        self.focus_area_patterns = {
            FocusArea.POKEMON: [
                r'\b(pokemon|pok[eé]mon|attacker|pokemon card)\b',
                r'\b(basic|stage 1|stage 2|evolution|ex|gx|v|vmax)\b',
                r'\b(hp|attack|ability|pokemon type)\b'
            ],
            FocusArea.TRAINERS: [
                r'\b(trainer|support|item|stadium|tool)\b',
                r'\b(supporter card|trainer card|pokemon tool)\b',
                r'\b(draw|search|utility|switch|heal)\b'
            ],
            FocusArea.ENERGY: [
                r'\b(energy|basic energy|special energy)\b',
                r'\b(energy card|energy type|mana)\b'
            ],
            FocusArea.STRATEGY: [
                r'\b(strategy|archetype|game plan|win condition)\b',
                r'\b(aggro|control|combo|midrange|tempo)\b',
                r'\b(synergy|theme|focus|approach)\b'
            ],
            FocusArea.SPECIFIC_CARD: [
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(ex|gx|v|vmax)\b',
                r'\b(pikachu|charizard|mewtwo|lucario|rayquaza|gardevoir)\b',
                r'\b(professor|ultra ball|quick ball|pokeball)\b'
            ]
        }

        self.pokemon_types = {
            'fire': ['Fire', 'Flame', 'Burn'],
            'water': ['Water', 'Ice', 'Bubble'],
            'grass': ['Grass', 'Plant', 'Leaf'],
            'electric': ['Lightning', 'Electric', 'Thunder'],
            'lightning': ['Lightning', 'Electric', 'Thunder'],
            'psychic': ['Psychic', 'Psycho', 'Mind'],
            'fighting': ['Fighting', 'Fight', 'Martial'],
            'darkness': ['Darkness', 'Dark', 'Shadow'],
            'metal': ['Metal', 'Steel', 'Iron'],
            'fairy': ['Fairy', 'Magic', 'Pink'],
            'dragon': ['Dragon', 'Draco'],
            'colorless': ['Colorless', 'Normal', 'Neutral']
        }

        self.common_pokemon_names = [
            'pikachu', 'charizard', 'mewtwo', 'mew', 'lucario', 'rayquaza', 'gardevoir',
            'garchomp', 'dialga', 'palkia', 'giratina', 'arceus', 'reshiram', 'zekrom',
            'kyurem', 'xerneas', 'yveltal', 'zygarde', 'solgaleo', 'lunala', 'necrozma',
            'zacian', 'zamazenta', 'eternatus', 'calyrex', 'dragapult', 'grimmsnarl',
            'toxapex', 'corviknight', 'dragapult', 'urshifu', 'regieleki', 'regidrago'
        ]

    def analyze_intent(self, message: str, current_phase: DeckPhase) -> IntentAnalysis:
        """Main function to analyze user intent"""
        message_lower = message.lower()
        
        # Detect intent type
        intent_type, intent_confidence = self._detect_intent_type(message_lower)
        
        # Detect focus area
        focus_area = self._detect_focus_area(message_lower, current_phase)
        
        # Extract card names and Pokemon types
        card_names = self._extract_card_names(message)
        pokemon_types = self._extract_pokemon_types(message_lower)
        
        # Extract other attributes
        attributes = self._extract_attributes(message_lower)
        
        # Determine if database query is needed
        needs_query = self._needs_database_query(intent_type, focus_area, current_phase)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(intent_type, focus_area, card_names, pokemon_types)
        
        return IntentAnalysis(
            intent_type=intent_type,
            focus_area=focus_area,
            extracted_card_names=card_names,
            extracted_pokemon_types=pokemon_types,
            extracted_attributes=attributes,
            needs_database_query=needs_query,
            confidence_score=intent_confidence,
            reasoning=reasoning
        )

    def _detect_intent_type(self, message: str) -> Tuple[IntentType, float]:
        """Detect the primary intent type from the message"""
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, message, re.IGNORECASE))
                score += matches
            
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return IntentType.UNKNOWN, 0.0
        
        # Get the highest scoring intent
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        confidence = min(best_intent[1] * 0.3, 1.0)  # Scale confidence
        
        return best_intent[0], confidence

    def _detect_focus_area(self, message: str, current_phase: DeckPhase) -> FocusArea:
        """Detect what area the user is focusing on"""
        focus_scores = {}
        
        for focus, patterns in self.focus_area_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, message, re.IGNORECASE))
                score += matches
            
            if score > 0:
                focus_scores[focus] = score
        
        # Add phase-based weighting
        phase_weights = {
            DeckPhase.STRATEGY: {FocusArea.STRATEGY: 2.0},
            DeckPhase.CORE_POKEMON: {FocusArea.POKEMON: 2.0, FocusArea.SPECIFIC_CARD: 1.5},
            DeckPhase.SUPPORT: {FocusArea.TRAINERS: 2.0},
            DeckPhase.ENERGY: {FocusArea.ENERGY: 2.0},
            DeckPhase.COMPLETE: {FocusArea.GENERAL: 1.5}
        }
        
        if current_phase in phase_weights:
            for focus, weight in phase_weights[current_phase].items():
                if focus in focus_scores:
                    focus_scores[focus] *= weight
        
        if not focus_scores:
            # Default focus based on phase
            phase_defaults = {
                DeckPhase.STRATEGY: FocusArea.STRATEGY,
                DeckPhase.CORE_POKEMON: FocusArea.POKEMON,
                DeckPhase.SUPPORT: FocusArea.TRAINERS,
                DeckPhase.ENERGY: FocusArea.ENERGY,
                DeckPhase.COMPLETE: FocusArea.GENERAL
            }
            return phase_defaults.get(current_phase, FocusArea.GENERAL)
        
        return max(focus_scores.items(), key=lambda x: x[1])[0]

    def _extract_card_names(self, message: str) -> List[str]:
        """Extract specific card names from the message"""
        card_names = []
        
        # Look for Pokemon names
        for pokemon in self.common_pokemon_names:
            pattern = r'\b' + re.escape(pokemon) + r'\b'
            if re.search(pattern, message, re.IGNORECASE):
                card_names.append(pokemon.title())
        
        # Look for card names with suffixes (ex, gx, v, etc.)
        suffix_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(ex|gx|v|vmax|vstar)\b'
        matches = re.findall(suffix_pattern, message, re.IGNORECASE)
        for match in matches:
            card_name = f"{match[0]} {match[1].upper()}"
            card_names.append(card_name)
        
        # Look for trainer card names
        trainer_patterns = [
            r'\b(Professor [A-Z][a-z]+)\b',
            r'\b(Ultra Ball|Quick Ball|Poke Ball|Great Ball|Master Ball)\b',
            r'\b(Switch|Potion|Energy Search|Bill|Oak)\b'
        ]
        
        for pattern in trainer_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    card_names.extend(match)
                else:
                    card_names.append(match)
        
        # Remove duplicates and clean up
        return list(set([name.strip() for name in card_names if name.strip()]))

    def _extract_pokemon_types(self, message: str) -> List[str]:
        """Extract Pokemon types from the message"""
        extracted_types = []
        
        for type_key, type_values in self.pokemon_types.items():
            for type_variant in type_values:
                pattern = r'\b' + re.escape(type_variant.lower()) + r'\b'
                if re.search(pattern, message):
                    extracted_types.append(type_values[0])  # Use canonical name
                    break
        
        return list(set(extracted_types))

    def _extract_attributes(self, message: str) -> Dict[str, Any]:
        """Extract other attributes like HP, attack cost, etc."""
        attributes = {}
        
        # HP extraction
        hp_pattern = r'(\d+)\s*(?:-|to)\s*(\d+)\s*hp'
        hp_match = re.search(hp_pattern, message)
        if hp_match:
            attributes['hp_min'] = int(hp_match.group(1))
            attributes['hp_max'] = int(hp_match.group(2))
        else:
            single_hp = re.search(r'(\d+)\s*hp', message)
            if single_hp:
                hp_value = int(single_hp.group(1))
                attributes['hp_min'] = hp_value - 20
                attributes['hp_max'] = hp_value + 20
        
        # Attack cost extraction
        cost_pattern = r'(\d+)\s*(?:energy|mana|cost)'
        cost_match = re.search(cost_pattern, message)
        if cost_match:
            attributes['energy_cost'] = int(cost_match.group(1))
        
        # Quantity extraction
        quantity_patterns = [
            r'(\d+)x?\s+',
            r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b',
            r'\b(a few|several|many|some)\b'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, message)
            if match:
                quantity_text = match.group(1)
                try:
                    attributes['quantity'] = int(quantity_text)
                except ValueError:
                    word_to_num = {
                        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                        'a few': 3, 'several': 4, 'some': 2, 'many': 6
                    }
                    attributes['quantity'] = word_to_num.get(quantity_text.lower(), 2)
                break
        
        return attributes

    def _needs_database_query(self, intent_type: IntentType, focus_area: FocusArea, current_phase: DeckPhase) -> bool:
        """Determine if a database query is needed"""
        # Intent types that typically need database queries
        query_intents = {
            IntentType.ADD_CARDS,
            IntentType.ANALYZE_MATCHUP
        }
        
        # Focus areas that need database queries
        query_focus = {
            FocusArea.POKEMON,
            FocusArea.TRAINERS,
            FocusArea.ENERGY,
            FocusArea.SPECIFIC_CARD
        }
        
        # Phases where queries are common
        query_phases = {
            DeckPhase.CORE_POKEMON,
            DeckPhase.SUPPORT,
            DeckPhase.ENERGY
        }
        
        return (
            intent_type in query_intents or
            focus_area in query_focus or
            current_phase in query_phases
        )

    def _generate_reasoning(self, intent_type: IntentType, focus_area: FocusArea, 
                          card_names: List[str], pokemon_types: List[str]) -> str:
        """Generate human-readable reasoning for the analysis"""
        reasoning_parts = []
        
        reasoning_parts.append(f"Detected intent: {intent_type.value}")
        reasoning_parts.append(f"Focus area: {focus_area.value}")
        
        if card_names:
            reasoning_parts.append(f"Specific cards mentioned: {', '.join(card_names)}")
        
        if pokemon_types:
            reasoning_parts.append(f"Pokemon types: {', '.join(pokemon_types)}")
        
        return " | ".join(reasoning_parts)


# Convenience functions
def analyze_user_intent(message: str, current_phase: DeckPhase) -> IntentAnalysis:
    """Analyze user intent from message"""
    analyzer = IntentAnalyzer()
    return analyzer.analyze_intent(message, current_phase)


def extract_card_names(message: str) -> List[str]:
    """Extract card names from message"""
    analyzer = IntentAnalyzer()
    return analyzer._extract_card_names(message)


def extract_pokemon_types(message: str) -> List[str]:
    """Extract Pokemon types from message"""
    analyzer = IntentAnalyzer()
    return analyzer._extract_pokemon_types(message.lower())


def needs_database_query(intent_type: IntentType, focus_area: FocusArea, current_phase: DeckPhase) -> bool:
    """Check if database query is needed"""
    analyzer = IntentAnalyzer()
    return analyzer._needs_database_query(intent_type, focus_area, current_phase)