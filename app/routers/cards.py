from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..database.card_queries import search_pokemon_cards, get_pokemon_card_by_id, get_available_filters
from ..schemas.conversation_schemas import CardSearchRequest, CardSearchResponse

router = APIRouter()

@router.post("/search", response_model=CardSearchResponse)
async def search_cards(request: CardSearchRequest):
    """Search for Pokemon cards with filters"""
    try:
        result = await search_pokemon_cards(
            name=request.name,
            card_types=request.card_types,
            pokemon_types=request.pokemon_types,
            hp_min=request.hp_min,
            hp_max=request.hp_max,
            subtypes=request.subtypes,
            limit=request.limit,
            offset=request.offset
        )
        return CardSearchResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_cards_get(
    name: Optional[str] = Query(None),
    card_types: Optional[List[str]] = Query(None),
    pokemon_types: Optional[List[str]] = Query(None),
    hp_min: Optional[int] = Query(None),
    hp_max: Optional[int] = Query(None),
    subtypes: Optional[List[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Search for Pokemon cards with query parameters"""
    try:
        result = await search_pokemon_cards(
            name=name,
            card_types=card_types,
            pokemon_types=pokemon_types,
            hp_min=hp_min,
            hp_max=hp_max,
            subtypes=subtypes,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filters")
async def get_card_filters():
    """Get available filter options for cards"""
    try:
        filters = await get_available_filters()
        return filters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{card_id}")
async def get_card(card_id: str):
    """Get a specific card by ID"""
    try:
        card = await get_pokemon_card_by_id(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        return card
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_cards():
    """Get all cards (with pagination)"""
    try:
        result = await search_pokemon_cards(limit=20, offset=0)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))