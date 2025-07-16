from typing import List, Optional, Dict, Any
from supabase import Client
from .supabase_client import get_supabase_client


class CardQueryBuilder:
    def __init__(self, client: Client):
        self.client = client
        self.table_name = "pokemon_cards"

    def search_cards(
        self,
        name: Optional[str] = None,
        card_types: Optional[List[str]] = None,
        pokemon_types: Optional[List[str]] = None,
        hp_min: Optional[int] = None,
        hp_max: Optional[int] = None,
        subtypes: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        query = self.client.table(self.table_name).select("*")
        
        # Base filter for standard legal cards
        query = query.eq("standard_legal", True)
        
        # Build dynamic WHERE clauses
        if name:
            query = query.ilike("name", f"%{name}%")
        
        if card_types:
            query = query.in_("card_type", card_types)
        
        if pokemon_types:
            # Use cs (contains) operator for JSONB array matching
            for ptype in pokemon_types:
                query = query.cs("types", f'["{ptype}"]')
        
        if hp_min is not None:
            query = query.gte("hp", hp_min)
        
        if hp_max is not None:
            query = query.lte("hp", hp_max)
        
        if subtypes:
            # Use eq for single subtype matching
            query = query.in_("subtype", subtypes)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        result = query.execute()
        
        return {
            "data": result.data,
            "count": len(result.data),
            "offset": offset,
            "limit": limit
        }

    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        result = self.client.table(self.table_name).select("*").eq("id", card_id).execute()
        return result.data[0] if result.data else None

    def get_cards_by_ids(self, card_ids: List[str]) -> List[Dict[str, Any]]:
        result = self.client.table(self.table_name).select("*").in_("id", card_ids).execute()
        return result.data

    def get_card_types(self) -> List[str]:
        result = self.client.table(self.table_name).select("card_type").eq("standard_legal", True).execute()
        types = set()
        for row in result.data:
            if row.get("card_type"):
                types.add(row["card_type"])
        return sorted(list(types))

    def get_pokemon_types(self) -> List[str]:
        result = self.client.table(self.table_name).select("types").eq("standard_legal", True).execute()
        types = set()
        for row in result.data:
            if row.get("types"):
                for ptype in row["types"]:
                    types.add(ptype)
        return sorted(list(types))

    def get_subtypes(self) -> List[str]:
        result = self.client.table(self.table_name).select("subtype").eq("standard_legal", True).execute()
        subtypes = set()
        for row in result.data:
            if row.get("subtype"):
                subtypes.add(row["subtype"])
        return sorted(list(subtypes))

    def get_hp_range(self) -> Dict[str, int]:
        result = self.client.table(self.table_name).select("hp").eq("standard_legal", True).not_.is_("hp", "null").execute()
        
        hp_values = [row["hp"] for row in result.data if row.get("hp") is not None]
        
        if not hp_values:
            return {"min": 0, "max": 0}
        
        return {
            "min": min(hp_values),
            "max": max(hp_values)
        }

    def search_cards_with_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        return self.search_cards(
            name=filters.get("name"),
            card_types=filters.get("card_types"),
            pokemon_types=filters.get("pokemon_types"),
            hp_min=filters.get("hp_min"),
            hp_max=filters.get("hp_max"),
            subtypes=filters.get("subtypes"),
            limit=filters.get("limit", 100),
            offset=filters.get("offset", 0)
        )

    def get_random_cards(self, count: int = 10) -> List[Dict[str, Any]]:
        # Note: This is a simplified random selection
        # For better performance, consider using a dedicated random function in Supabase
        result = self.client.table(self.table_name).select("*").eq("standard_legal", True).limit(count * 5).execute()
        
        import random
        if len(result.data) <= count:
            return result.data
        
        return random.sample(result.data, count)


# Convenience functions
async def get_card_query_builder() -> CardQueryBuilder:
    client = await get_supabase_client()
    return CardQueryBuilder(client)


async def search_pokemon_cards(
    name: Optional[str] = None,
    card_types: Optional[List[str]] = None,
    pokemon_types: Optional[List[str]] = None,
    hp_min: Optional[int] = None,
    hp_max: Optional[int] = None,
    subtypes: Optional[List[str]] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    query_builder = await get_card_query_builder()
    return query_builder.search_cards(
        name=name,
        card_types=card_types,
        pokemon_types=pokemon_types,
        hp_min=hp_min,
        hp_max=hp_max,
        subtypes=subtypes,
        limit=limit,
        offset=offset
    )


async def get_pokemon_card_by_id(card_id: str) -> Optional[Dict[str, Any]]:
    query_builder = await get_card_query_builder()
    return query_builder.get_card_by_id(card_id)


async def get_available_filters() -> Dict[str, Any]:
    query_builder = await get_card_query_builder()
    
    return {
        "card_types": query_builder.get_card_types(),
        "pokemon_types": query_builder.get_pokemon_types(),
        "subtypes": query_builder.get_subtypes(),
        "hp_range": query_builder.get_hp_range()
    }