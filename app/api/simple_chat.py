"""
Simplified Chat API Endpoint
Direct Claude-Database interaction without complex middleware
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..services.simple_deck_service import SimpleDeckBuildingService, get_simple_deck_service

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    message: str
    deck_id: Optional[str] = None


class ChatResponse(BaseModel):
    user_id: str
    message: str
    ai_response: str
    cards_found: list
    deck_progress: Dict[str, Any]
    conversation_state: Dict[str, Any]
    error: Optional[str] = None


@router.post("/simple-chat", response_model=ChatResponse)
async def simple_chat(
    request: ChatRequest,
    deck_service: SimpleDeckBuildingService = Depends(get_simple_deck_service)
):
    """
    Simplified chat endpoint with direct Claude-database interaction
    """
    try:
        response = await deck_service.process_user_message(
            user_id=request.user_id,
            message=request.message,
            deck_id=request.deck_id
        )
        
        return ChatResponse(**response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat message: {str(e)}"
        )


@router.get("/deck-summary/{user_id}")
async def get_deck_summary(
    user_id: str,
    deck_service: SimpleDeckBuildingService = Depends(get_simple_deck_service)
):
    """Get current deck summary for a user"""
    try:
        summary = await deck_service.get_deck_summary(user_id)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting deck summary: {str(e)}"
        )


@router.post("/add-card")
async def add_card_to_deck(
    request: dict,
    deck_service: SimpleDeckBuildingService = Depends(get_simple_deck_service)
):
    """Add a card to user's deck"""
    try:
        result = await deck_service.add_card_to_deck(
            user_id=request["user_id"],
            card_id=request["card_id"],
            quantity=request.get("quantity", 1)
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding card to deck: {str(e)}"
        )