#!/usr/bin/env python3
"""
Analyze regulation mark filtering and potential issues
"""

import os
import sys
import requests
from collections import Counter
from supabase import create_client, Client
from decouple import config

class RegulationMarkAnalyzer:
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
            
    def get_all_database_cards(self):
        """Get all cards from database with pagination"""
        print("🔍 Getting all cards from database...")
        
        all_cards = []
        page_size = 1000
        page = 0
        
        while True:
            offset = page * page_size
            result = self.supabase.table('pokemon_cards').select('card_id, name, set_name, regulation_mark, standard_legal').range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
                
            all_cards.extend(result.data)
            page += 1
            print(f"  Loaded page {page}, total cards so far: {len(all_cards)}")
            
            # Continue until we get less than page_size
            if len(result.data) < page_size:
                break
                
        print(f"Total cards loaded: {len(all_cards)}")
        return all_cards
        
    def analyze_current_standard_legal_cards(self):
        """Analyze what makes a card standard legal according to Pokemon TCG API"""
        print("🔍 Analyzing current standard legal cards from API...")
        
        try:
            # Get all standard legal cards from API
            all_standard_cards = []
            page = 1
            
            while True:
                response = requests.get(
                    f"{self.tcg_api_base}/cards",
                    headers=self.headers,
                    params={
                        'q': 'legalities.standard:Legal',
                        'page': page,
                        'pageSize': 250
                    }
                )
                
                if response.status_code == 404:
                    break
                    
                response.raise_for_status()
                data = response.json()
                
                cards = data.get('data', [])
                if not cards:
                    break
                    
                all_standard_cards.extend(cards)
                print(f"  Loaded API page {page}, total cards so far: {len(all_standard_cards)}")
                
                page += 1
                
                # Safety check - if we're getting too many, there might be an issue
                if len(all_standard_cards) > 10000:
                    print("  Stopping at 10,000 cards to avoid runaway query")
                    break
                    
            print(f"Total standard legal cards from API: {len(all_standard_cards)}")
            
            # Analyze regulation marks
            regulation_marks = [card.get('regulationMark') for card in all_standard_cards]
            regulation_counter = Counter(regulation_marks)
            
            print("\nRegulation mark distribution in API standard legal cards:")
            for mark, count in sorted(regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone'):
                mark_display = mark if mark is not None else 'None'
                percentage = (count / len(all_standard_cards)) * 100
                print(f"  {mark_display}: {count} ({percentage:.1f}%)")
                
            # Check which regulation marks we should be including
            current_marks = ['G', 'H', 'I']
            print(f"\nCurrent import script marks: {current_marks}")
            
            # Find all unique regulation marks that are standard legal
            unique_marks = set(mark for mark in regulation_marks if mark is not None)
            print(f"All regulation marks in standard legal cards: {sorted(unique_marks)}")
            
            # Check for cards with None regulation mark that are standard legal
            none_mark_cards = [card for card in all_standard_cards if card.get('regulationMark') is None]
            if none_mark_cards:
                print(f"\nCards with None regulation mark that are standard legal: {len(none_mark_cards)}")
                print("Sample cards:")
                for card in none_mark_cards[:10]:
                    print(f"  - {card['name']} ({card['set']['name']}) - {card['id']}")
                    
            return all_standard_cards
            
        except Exception as e:
            print(f"❌ Error analyzing API cards: {e}")
            return []
            
    def compare_database_vs_api(self):
        """Compare our database filtering with API results"""
        print("🔍 Comparing database vs API results...")
        
        # Get database cards
        db_cards = self.get_all_database_cards()
        
        # Get API cards
        api_cards = self.analyze_current_standard_legal_cards()
        
        # Create sets for comparison
        db_card_ids = set(card['card_id'] for card in db_cards)
        api_card_ids = set(card['id'] for card in api_cards)
        
        # Find missing cards
        missing_from_db = api_card_ids - db_card_ids
        extra_in_db = db_card_ids - api_card_ids
        
        print(f"\nComparison Results:")
        print(f"  Cards in API: {len(api_card_ids)}")
        print(f"  Cards in database: {len(db_card_ids)}")
        print(f"  Missing from database: {len(missing_from_db)}")
        print(f"  Extra in database: {len(extra_in_db)}")
        
        if missing_from_db:
            print(f"\nSample missing cards (first 20):")
            missing_cards = [card for card in api_cards if card['id'] in missing_from_db][:20]
            for card in missing_cards:
                print(f"  - {card['name']} ({card['set']['name']}) - {card['id']}")
                print(f"    Regulation Mark: {card.get('regulationMark')}")
                print(f"    Set Release Date: {card['set'].get('releaseDate')}")
                
        return missing_from_db, extra_in_db
        
    def check_regulation_mark_evolution(self):
        """Check if regulation marks have evolved beyond G, H, I"""
        print("🔍 Checking regulation mark evolution...")
        
        try:
            # Get the most recent sets
            response = requests.get(
                f"{self.tcg_api_base}/sets",
                headers=self.headers,
                params={
                    'orderBy': 'releaseDate',
                    'pageSize': 50
                }
            )
            response.raise_for_status()
            
            sets_data = response.json()
            recent_sets = sorted(sets_data.get('data', []), key=lambda x: x.get('releaseDate', ''), reverse=True)[:10]
            
            print("Recent sets and their regulation marks:")
            for set_info in recent_sets:
                print(f"  - {set_info['name']} ({set_info['id']}) - Released: {set_info.get('releaseDate')}")
                
                # Get a sample of cards from this set
                cards_response = requests.get(
                    f"{self.tcg_api_base}/cards",
                    headers=self.headers,
                    params={
                        'q': f'set.id:{set_info["id"]}',
                        'pageSize': 5
                    }
                )
                
                if cards_response.status_code == 200:
                    cards_data = cards_response.json()
                    sample_cards = cards_data.get('data', [])
                    
                    if sample_cards:
                        regulation_marks = set(card.get('regulationMark') for card in sample_cards)
                        print(f"    Regulation marks in this set: {sorted(regulation_marks)}")
                        
        except Exception as e:
            print(f"❌ Error checking regulation mark evolution: {e}")
            
    def run_analysis(self):
        """Run the complete analysis"""
        print("🔍 Starting regulation mark analysis...")
        print("=" * 60)
        
        # Check current API standard legal cards
        self.analyze_current_standard_legal_cards()
        print("=" * 60)
        
        # Compare database vs API
        missing_cards, extra_cards = self.compare_database_vs_api()
        print("=" * 60)
        
        # Check regulation mark evolution
        self.check_regulation_mark_evolution()
        print("=" * 60)
        
        print("🎯 ANALYSIS SUMMARY:")
        print(f"  Missing cards from database: {len(missing_cards)}")
        print(f"  Extra cards in database: {len(extra_cards)}")
        
        if len(missing_cards) > 0:
            print("  ⚠️ Database is missing cards that should be standard legal!")
            print("  This suggests the import filtering is too restrictive.")
        else:
            print("  ✅ Database appears complete for standard legal cards")

def main():
    """Main function to run the analysis"""
    try:
        analyzer = RegulationMarkAnalyzer()
        analyzer.run_analysis()
        
    except KeyboardInterrupt:
        print("\n❌ Analysis cancelled by user")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise

if __name__ == "__main__":
    main()