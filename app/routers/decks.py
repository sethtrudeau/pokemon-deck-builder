from fastapi import APIRouter, HTTPException
from ..services.deck_building_service import get_deck_building_service
from ..schemas.conversation_schemas import (
    ChatMessage, ChatResponse, AddCardRequest, AddCardResponse, DeckSummaryResponse
)

router = APIRouter()

@router.post("/pokemon-chat", response_model=ChatResponse)
async def pokemon_chat(message: ChatMessage):
    """Main conversation endpoint for Pokemon deck building"""
    try:
        service = await get_deck_building_service()
        result = await service.process_user_message(
            user_id=message.user_id,
            message=message.message,
            deck_id=message.deck_id
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-card", response_model=AddCardResponse)
async def add_card_to_deck(request: AddCardRequest):
    """Add a specific card to user's deck"""
    try:
        service = await get_deck_building_service()
        result = await service.add_card_to_deck(
            user_id=request.user_id,
            card_id=request.card_id,
            quantity=request.quantity
        )
        return AddCardResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary/{user_id}", response_model=DeckSummaryResponse)
async def get_deck_summary(user_id: str):
    """Get current deck summary for user"""
    try:
        service = await get_deck_building_service()
        result = await service.get_deck_summary(user_id)
        return DeckSummaryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_decks():
    return {"message": "Get all decks"}

@router.post("/")
async def create_deck():
    return {"message": "Create new deck"}

@router.get("/{deck_id}")
async def get_deck(deck_id: str):
    return {"message": f"Get deck {deck_id}"}

@router.put("/{deck_id}")
async def update_deck(deck_id: str):
    return {"message": f"Update deck {deck_id}"}

@router.delete("/{deck_id}")
async def delete_deck(deck_id: str):
    return {"message": f"Delete deck {deck_id}"}