#!/usr/bin/env python3
"""
Investigate Dragapult ex missing from database
Check for specific cards and analyze what might be missing
"""

import os
import sys
import requests
from collections import Counter
from supabase import create_client, Client
from decouple import config

class DragapultInvestigator:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Pokemon TCG API configuration
        self.tcg_api_base = "https://api.pokemontcg.io/v2"
        self.tcg_api_key = config('POKEMON_TCG_API_KEY', default='')
        
        self.headers = {
            'Content-Type': 'application/json'
        }
        if self.tcg_api_key:
            self.headers['X-Api-Key'] = self.tcg_api_key
        
    def search_dragapult_in_database(self):
        """Search for Dragapult cards in our database"""
        print("🔍 Searching for Dragapult cards in database...")
        
        try:
            # Search for any cards with "Dragapult" in the name
            result = self.supabase.table('pokemon_cards').select('*').ilike('name', '%Dragapult%').execute()
            
            cards = result.data
            print(f"Found {len(cards)} Dragapult cards in database:")
            
            for card in cards:
                print(f"  - {card['name']} ({card['set_name']}) - {card['card_id']}")
                print(f"    Standard Legal: {card.get('standard_legal')}")
                print(f"    Regulation Mark: {card.get('regulation_mark')}")
                print(f"    Card Type: {card.get('card_type')}")
                print(f"    Subtype: {card.get('subtype')}")
                print()
                
            return cards
            
        except Exception as e:
            print(f"❌ Error searching database: {e}")
            return []
    
    def search_dragapult_in_tcg_api(self):
        """Search for Dragapult cards via Pokemon TCG API"""
        print("🌐 Searching for Dragapult cards via Pokemon TCG API...")
        
        try:
            # Search for all Dragapult cards
            response = requests.get(
                f"{self.tcg_api_base}/cards",
                headers=self.headers,
                params={
                    'q': 'name:Dragapult',
                    'pageSize': 250
                }
            )
            response.raise_for_status()
            
            api_data = response.json()
            cards = api_data.get('data', [])
            
            print(f"Found {len(cards)} Dragapult cards in Pokemon TCG API:")
            print()
            
            standard_legal_cards = []
            
            for card in cards:
                legalities = card.get('legalities', {})
                standard_legal = legalities.get('standard') == 'Legal'
                regulation_mark = card.get('regulationMark')
                
                print(f"  - {card['name']} ({card['set']['name']}) - {card['id']}")
                print(f"    Standard Legal: {standard_legal}")
                print(f"    Regulation Mark: {regulation_mark}")
                print(f"    Rarity: {card.get('rarity')}")
                print(f"    Card Number: {card.get('number')}")
                print(f"    Release Date: {card['set'].get('releaseDate')}")
                
                if standard_legal:
                    standard_legal_cards.append(card)
                    print(f"    ⭐ THIS SHOULD BE IN OUR DATABASE!")
                    
                print()
                
            print(f"Total standard legal Dragapult cards: {len(standard_legal_cards)}")
            return standard_legal_cards
            
        except Exception as e:
            print(f"❌ Error searching Pokemon TCG API: {e}")
            return []
    
    def check_missing_standard_cards(self):
        """Check for other potentially missing standard legal cards"""
        print("🔍 Checking for other potentially missing standard legal cards...")
        
        try:
            # Get a few well-known standard legal cards that should definitely be in the database
            known_cards = [
                'Charizard ex',
                'Pikachu ex',
                'Miraidon ex',
                'Koraidon ex',
                'Chien-Pao ex',
                'Baxcalibur',
                'Gardevoir ex',
                'Kirlia'
            ]
            
            missing_cards = []
            
            for card_name in known_cards:
                result = self.supabase.table('pokemon_cards').select('name, set_name, standard_legal').ilike('name', f'%{card_name}%').execute()
                
                cards = result.data
                standard_cards = [c for c in cards if c.get('standard_legal')]
                
                print(f"  {card_name}: {len(standard_cards)} standard legal variants found")
                
                if len(standard_cards) == 0:
                    missing_cards.append(card_name)
                    print(f"    ⚠️ NO STANDARD LEGAL VARIANTS FOUND!")
                    
            if missing_cards:
                print(f"\n❌ Cards that appear to be missing: {missing_cards}")
            else:
                print(f"\n✅ All checked cards found in database")
                
        except Exception as e:
            print(f"❌ Error checking for missing cards: {e}")
    
    def analyze_api_query_restrictions(self):
        """Analyze if our API query is too restrictive"""
        print("🔍 Analyzing API query restrictions...")
        
        try:
            # Test the exact query from our import script
            query = 'legalities.standard:Legal'
            
            response = requests.get(
                f"{self.tcg_api_base}/cards",
                headers=self.headers,
                params={
                    'q': query,
                    'pageSize': 1,  # Just get count info
                }
            )
            response.raise_for_status()
            
            api_data = response.json()
            total_count = api_data.get('totalCount', 0)
            
            print(f"Total cards from API query '{query}': {total_count}")
            
            # Compare with our database count
            db_result = self.supabase.table('pokemon_cards').select('*', count='exact').eq('standard_legal', True).execute()
            db_count = db_result.count
            
            print(f"Standard legal cards in our database: {db_count}")
            
            if db_count < total_count:
                print(f"⚠️ We're missing {total_count - db_count} cards from the API!")
                print("This suggests our import might be incomplete or filtered too aggressively")
            else:
                print("✅ Our database count matches or exceeds API count")
                
            # Check specific Dragapult ex query
            dragapult_response = requests.get(
                f"{self.tcg_api_base}/cards",
                headers=self.headers,
                params={
                    'q': 'name:"Dragapult ex" AND legalities.standard:Legal',
                    'pageSize': 250
                }
            )
            dragapult_response.raise_for_status()
            
            dragapult_data = dragapult_response.json()
            dragapult_cards = dragapult_data.get('data', [])
            
            print(f"\nDragapult ex cards that should be standard legal: {len(dragapult_cards)}")
            
            for card in dragapult_cards:
                print(f"  - {card['name']} ({card['set']['name']}) - {card['id']}")
                print(f"    Regulation Mark: {card.get('regulationMark')}")
                print(f"    Should be imported: YES")
                
        except Exception as e:
            print(f"❌ Error analyzing API query: {e}")
    
    def check_regulation_mark_filtering(self):
        """Check if regulation mark filtering is causing issues"""
        print("🔍 Checking regulation mark filtering logic...")
        
        try:
            # Check what regulation marks we have in our database
            result = self.supabase.table('pokemon_cards').select('regulation_mark').execute()
            
            regulation_marks = [card.get('regulation_mark') for card in result.data]
            regulation_counter = Counter(regulation_marks)
            
            print("Regulation marks in our database:")
            for mark, count in sorted(regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone'):
                mark_display = mark if mark is not None else 'None'
                print(f"  {mark_display}: {count}")
                
            # Check the current standard marks from our import script
            current_standard_marks = ['G', 'H', 'I']
            print(f"\nCurrent standard marks in import script: {current_standard_marks}")
            
            # Check if there are newer regulation marks we're missing
            print("\nChecking Pokemon TCG API for regulation marks...")
            
            # Get recent cards to see what regulation marks exist
            response = requests.get(
                f"{self.tcg_api_base}/cards",
                headers=self.headers,
                params={
                    'q': 'legalities.standard:Legal',
                    'pageSize': 250,
                    'orderBy': 'set.releaseDate'
                }
            )
            response.raise_for_status()
            
            api_data = response.json()
            api_cards = api_data.get('data', [])
            
            api_regulation_marks = [card.get('regulationMark') for card in api_cards]
            api_regulation_counter = Counter(api_regulation_marks)
            
            print("Regulation marks from recent API cards:")
            for mark, count in sorted(api_regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone'):
                mark_display = mark if mark is not None else 'None'
                print(f"  {mark_display}: {count}")
                
            # Check if we're missing any regulation marks
            api_marks = set(api_regulation_marks)
            db_marks = set(regulation_marks)
            
            missing_marks = api_marks - db_marks
            if missing_marks:
                print(f"\n⚠️ Regulation marks in API but not in our database: {missing_marks}")
                print("This could indicate we need to update our standard marks list!")
            else:
                print("\n✅ All API regulation marks are present in our database")
                
        except Exception as e:
            print(f"❌ Error checking regulation marks: {e}")
    
    def run_full_investigation(self):
        """Run the complete investigation"""
        print("🕵️ Starting full Dragapult investigation...")
        print("=" * 60)
        
        # Step 1: Search database for Dragapult
        db_cards = self.search_dragapult_in_database()
        print("=" * 60)
        
        # Step 2: Search API for Dragapult
        api_cards = self.search_dragapult_in_tcg_api()
        print("=" * 60)
        
        # Step 3: Check for other missing cards
        self.check_missing_standard_cards()
        print("=" * 60)
        
        # Step 4: Analyze API query restrictions
        self.analyze_api_query_restrictions()
        print("=" * 60)
        
        # Step 5: Check regulation mark filtering
        self.check_regulation_mark_filtering()
        print("=" * 60)
        
        # Summary
        print("🎯 INVESTIGATION SUMMARY:")
        print(f"  Dragapult cards in database: {len(db_cards)}")
        print(f"  Standard legal Dragapult cards in API: {len(api_cards)}")
        
        if len(api_cards) > len(db_cards):
            print(f"  ⚠️ Missing {len(api_cards) - len(db_cards)} Dragapult cards!")
        else:
            print(f"  ✅ Database appears complete for Dragapult cards")

def main():
    """Main function to run the investigation"""
    try:
        investigator = DragapultInvestigator()
        investigator.run_full_investigation()
        
    except KeyboardInterrupt:
        print("\n❌ Investigation cancelled by user")
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        raise

if __name__ == "__main__":
    main()