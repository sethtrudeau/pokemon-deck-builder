#!/usr/bin/env python3
"""
Pokemon TCG Card Import Script
Replaces n8n workflow to import current standard-legal cards from pokemontcg.io
"""

import requests
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from supabase import create_client, Client
from decouple import config

class PokemonCardImporter:
    def __init__(self):
        # Pokemon TCG API configuration
        self.tcg_api_base = "https://api.pokemontcg.io/v2"
        self.tcg_api_key = config('POKEMON_TCG_API_KEY', default='')  # Optional API key for higher rate limits
        
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Current standard legal regulation marks (update as rotation changes)
        self.current_standard_marks = ['F', 'G', 'H', 'I']  # Update this when rotation happens
        
        # Headers for Pokemon TCG API
        self.headers = {
            'Content-Type': 'application/json'
        }
        if self.tcg_api_key:
            self.headers['X-Api-Key'] = self.tcg_api_key

    def get_current_standard_sets(self) -> List[str]:
        """Get list of current standard legal sets"""
        try:
            # Query sets API to get current standard sets
            response = requests.get(
                f"{self.tcg_api_base}/sets",
                headers=self.headers,
                params={
                    'q': 'legalities.standard:Legal',  # Only standard legal sets
                    'pageSize': 250
                }
            )
            response.raise_for_status()
            
            sets_data = response.json()
            standard_sets = []
            
            for set_info in sets_data.get('data', []):
                # Check if set is standard legal
                legalities = set_info.get('legalities', {})
                if legalities.get('standard') == 'Legal':
                    standard_sets.append(set_info['id'])
                    print(f"Found standard set: {set_info['name']} ({set_info['id']})")
            
            return standard_sets
            
        except Exception as e:
            print(f"Error fetching standard sets: {e}")
            # Fallback to known recent sets if API fails
            return [
                'sv1', 'sv2', 'sv3', 'sv4', 'sv5',  # Scarlet & Violet series
                'swsh11', 'swsh12'  # Recent Sword & Shield if still legal
            ]

    def fetch_cards_from_tcg_api(self, page: int = 1, page_size: int = 250) -> Dict[str, Any]:
        """Fetch cards from Pokemon TCG API with current standard filters"""
        try:
            # Build query for current standard cards
            query_parts = []
            
            # Only get standard legal cards
            query_parts.append('legalities.standard:Legal')
            
            # Combine query parts
            query = ' '.join(query_parts)
            
            params = {
                'q': query,
                'page': page,
                'pageSize': page_size,
                'orderBy': 'set.releaseDate'  # Order by release date
            }
            
            print(f"Fetching page {page} with query: {query}")
            
            response = requests.get(
                f"{self.tcg_api_base}/cards",
                headers=self.headers,
                params=params
            )
            
            # Handle pagination more gracefully
            if response.status_code == 404:
                print(f"Page {page} not found - reached end of results")
                return {'data': [], 'page': page, 'pageSize': page_size, 'count': 0, 'totalCount': 0}
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error fetching cards from API: {e}")
            return {}

    def determine_standard_legal(self, card_data: Dict[str, Any]) -> bool:
        """Determine if a card is currently standard legal"""
        # Primary check: Use API legalities as the source of truth
        legalities = card_data.get('legalities', {})
        if legalities.get('standard') == 'Legal':
            return True
        
        # Secondary check: regulation marks (but don't reject None)
        regulation_mark = card_data.get('regulationMark')
        if regulation_mark in self.current_standard_marks:
            return True
            
        return False

    def transform_card_data(self, api_card: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Pokemon TCG API card data to Supabase schema"""
        try:
            # Extract basic information
            card_data = {
                'card_id': api_card.get('id'),
                'name': api_card.get('name'),
                'card_type': api_card.get('supertype'),  # Pokemon, Trainer, Energy
                'subtype': api_card.get('subtypes', [None])[0] if api_card.get('subtypes') else None,
                'hp': api_card.get('hp'),
                'types': api_card.get('types', []),
                'attacks': api_card.get('attacks', []),
                'abilities': api_card.get('abilities', []),
                'weaknesses': api_card.get('weaknesses'),
                'resistances': api_card.get('resistances'),
                'retreat_cost': len(api_card.get('retreatCost', [])) if api_card.get('retreatCost') else None,
                'set_id': api_card.get('set', {}).get('id'),
                'set_name': api_card.get('set', {}).get('name'),
                'rarity': api_card.get('rarity'),
                'artist': api_card.get('artist'),
                'card_number': api_card.get('number'),
                'regulation_mark': api_card.get('regulationMark'),
                'standard_legal': self.determine_standard_legal(api_card),
                'expanded_legal': api_card.get('legalities', {}).get('expanded') == 'Legal',
                'market_price': None,  # Could be populated from tcgplayer data if available
                'image_url': api_card.get('images', {}).get('large'),
                'last_updated': datetime.now().isoformat()
            }
            
            # Clean up None values that should be empty lists
            if card_data['types'] is None:
                card_data['types'] = []
            if card_data['attacks'] is None:
                card_data['attacks'] = []
            if card_data['abilities'] is None:
                card_data['abilities'] = []
                
            return card_data
            
        except Exception as e:
            print(f"Error transforming card {api_card.get('name', 'Unknown')}: {e}")
            return None

    def upsert_cards_to_supabase(self, cards: List[Dict[str, Any]], batch_size: int = 100):
        """Upsert cards to Supabase in batches"""
        try:
            total_cards = len(cards)
            print(f"Upserting {total_cards} cards to Supabase...")
            
            for i in range(0, total_cards, batch_size):
                batch = cards[i:i + batch_size]
                
                # Upsert batch
                result = self.supabase.table('pokemon_cards').upsert(
                    batch,
                    on_conflict='card_id'  # Use card_id as the conflict resolution key
                ).execute()
                
                print(f"Upserted batch {i//batch_size + 1}/{(total_cards + batch_size - 1)//batch_size}")
                
                # Rate limiting
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error upserting to Supabase: {e}")
            raise

    def import_all_standard_cards(self):
        """Main method to import all current standard legal cards"""
        print("Starting Pokemon TCG card import...")
        print(f"Current standard regulation marks: {self.current_standard_marks}")
        
        all_cards = []
        page = 1
        total_pages = 1
        
        while page <= total_pages:
            print(f"\nFetching page {page}...")
            
            api_response = self.fetch_cards_from_tcg_api(page=page)
            
            if not api_response or not api_response.get('data'):
                print("No more data from API, stopping import")
                break
                
            # Update total pages from first response
            if page == 1:
                total_count = api_response.get('totalCount', 0)
                total_pages = (total_count + 249) // 250  # Ceiling division
                print(f"Total cards available: {total_count}")
                print(f"Total pages to fetch: {total_pages}")
            
            # Process cards from this page
            cards_data = api_response.get('data', [])
            print(f"Processing {len(cards_data)} cards from page {page}")
            
            if not cards_data:
                print("No cards in response, stopping import")
                break
            
            page_cards = []
            for api_card in cards_data:
                transformed_card = self.transform_card_data(api_card)
                if transformed_card:
                    page_cards.append(transformed_card)
            
            all_cards.extend(page_cards)
            print(f"Added {len(page_cards)} valid cards (total: {len(all_cards)})")
            
            # Upsert this page's cards immediately to avoid memory issues
            if page_cards:
                self.upsert_cards_to_supabase(page_cards)
            
            page += 1
            
            # Rate limiting between pages
            time.sleep(0.5)  # Reduced to speed up import
        
        print(f"\n✅ Import complete! Processed {len(all_cards)} total cards")
        
        # Print summary statistics
        self.print_import_summary()

    def print_import_summary(self):
        """Print summary of imported cards"""
        try:
            # Get counts by type
            result = self.supabase.table('pokemon_cards').select('card_type, standard_legal, regulation_mark').execute()
            cards = result.data
            
            print("\n📊 Import Summary:")
            print(f"Total cards in database: {len(cards)}")
            
            # Count by card type
            type_counts = {}
            standard_counts = {'standard': 0, 'non_standard': 0}
            regulation_counts = {}
            
            for card in cards:
                card_type = card.get('card_type', 'Unknown')
                type_counts[card_type] = type_counts.get(card_type, 0) + 1
                
                if card.get('standard_legal'):
                    standard_counts['standard'] += 1
                else:
                    standard_counts['non_standard'] += 1
                    
                reg_mark = card.get('regulation_mark', 'None')
                regulation_counts[reg_mark] = regulation_counts.get(reg_mark, 0) + 1
            
            print("\nBy Card Type:")
            for card_type, count in sorted(type_counts.items()):
                print(f"  {card_type}: {count}")
                
            print("\nBy Standard Legality:")
            for legality, count in standard_counts.items():
                print(f"  {legality}: {count}")
                
            print("\nBy Regulation Mark:")
            for reg_mark, count in sorted(regulation_counts.items()):
                print(f"  {reg_mark}: {count}")
                
        except Exception as e:
            print(f"Error generating summary: {e}")


def main():
    """Main function to run the import"""
    try:
        importer = PokemonCardImporter()
        importer.import_all_standard_cards()
        
    except KeyboardInterrupt:
        print("\n❌ Import cancelled by user")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        raise


if __name__ == "__main__":
    main()