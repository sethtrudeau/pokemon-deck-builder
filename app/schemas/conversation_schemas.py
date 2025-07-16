from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class ChatMessage(BaseModel):
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="User message")
    deck_id: Optional[str] = Field(None, description="Optional deck identifier")


class ChatResponse(BaseModel):
    user_id: str
    message: str
    intent: str
    focus_area: str
    current_phase: str
    cards_found: List[Dict[str, Any]] = Field(default_factory=list)
    ai_response: str
    deck_progress: Dict[str, Any]
    phase_complete: bool = False
    conversation_state: Dict[str, Any]
    error: Optional[str] = None


class AddCardRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    card_id: str = Field(..., description="Card identifier")
    quantity: int = Field(1, ge=1, le=4, description="Number of cards to add (1-4)")


class AddCardResponse(BaseModel):
    success: bool
    card_added: Optional[str] = None
    quantity: Optional[int] = None
    deck_progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DeckSummaryResponse(BaseModel):
    user_id: str
    current_phase: str
    deck_progress: Dict[str, Any]
    selected_cards: Dict[str, int]  # Card name -> quantity
    conversation_state: Dict[str, Any]
    error: Optional[str] = None


class CardSearchRequest(BaseModel):
    name: Optional[str] = None
    card_types: Optional[List[str]] = None
    pokemon_types: Optional[List[str]] = None
    hp_min: Optional[int] = None
    hp_max: Optional[int] = None
    subtypes: Optional[List[str]] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class CardSearchResponse(BaseModel):
    data: List[Dict[str, Any]]
    count: int
    offset: int
    limit: int
    error: Optional[str] = None