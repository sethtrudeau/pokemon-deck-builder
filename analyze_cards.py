#!/usr/bin/env python3
import asyncio
from app.database.card_queries import get_card_query_builder

async def analyze_cards():
    query_builder = await get_card_query_builder()
    client = query_builder.client
    
    # Get basic stats
    all_cards = client.table('pokemon_cards').select('*').eq('standard_legal', True).execute()
    print(f'Total standard legal cards: {len(all_cards.data)}')
    
    # Count by type
    type_counts = {}
    for card in all_cards.data:
        card_type = card.get('card_type', 'Unknown')
        type_counts[card_type] = type_counts.get(card_type, 0) + 1
    
    print('Cards by type:')
    for card_type, count in sorted(type_counts.items()):
        print(f'  {card_type}: {count}')
    
    # Check for duplicates
    names = [card.get('name', 'Unknown') for card in all_cards.data]
    unique_names = set(names)
    print(f'Unique card names: {len(unique_names)}')
    print(f'Total cards: {len(names)}')
    
    if len(names) != len(unique_names):
        print('WARNING: Duplicate cards found!')
        from collections import Counter
        name_counts = Counter(names)
        duplicates = {name: count for name, count in name_counts.items() if count > 1}
        print(f'Duplicates: {len(duplicates)}')
        for name, count in sorted(duplicates.items())[:5]:
            print(f'  {name}: {count} copies')

if __name__ == "__main__":
    asyncio.run(analyze_cards())