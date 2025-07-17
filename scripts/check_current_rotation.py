#!/usr/bin/env python3
"""
Check what the current Pokemon TCG rotation actually is
"""

import os
import sys
import requests
from collections import Counter
from supabase import create_client, Client
from decouple import config

class RotationChecker:
    def __init__(self):
        # Pokemon TCG API configuration
        self.tcg_api_base = "https://api.pokemontcg.io/v2"
        self.tcg_api_key = config('POKEMON_TCG_API_KEY', default='')
        
        self.headers = {
            'Content-Type': 'application/json'
        }
        if self.tcg_api_key:
            self.headers['X-Api-Key'] = self.tcg_api_key
            
    def check_current_standard_sets(self):
        """Check which sets are currently standard legal"""
        print("🔍 Checking current standard legal sets...")
        
        try:
            response = requests.get(
                f"{self.tcg_api_base}/sets",
                headers=self.headers,
                params={
                    'q': 'legalities.standard:Legal',
                    'pageSize': 250
                }
            )
            response.raise_for_status()
            
            data = response.json()
            sets = data.get('data', [])
            
            # Sort by release date
            sorted_sets = sorted(sets, key=lambda x: x.get('releaseDate', ''))
            
            print(f"Found {len(sorted_sets)} standard legal sets:")
            print()
            
            for set_info in sorted_sets:
                print(f"  - {set_info['name']} ({set_info['id']}) - Released: {set_info.get('releaseDate')}")
                
                # Get sample cards from this set to check regulation marks
                cards_response = requests.get(
                    f"{self.tcg_api_base}/cards",
                    headers=self.headers,
                    params={
                        'q': f'set.id:{set_info["id"]}',
                        'pageSize': 3
                    }
                )
                
                if cards_response.status_code == 200:
                    cards_data = cards_response.json()
                    sample_cards = cards_data.get('data', [])
                    
                    if sample_cards:
                        regulation_marks = [card.get('regulationMark') for card in sample_cards]
                        unique_marks = set(regulation_marks)
                        print(f"    Sample regulation marks: {sorted(unique_marks)}")
                        
                print()
                
        except Exception as e:
            print(f"❌ Error checking standard sets: {e}")
            
    def check_dragapult_ex_specifically(self):
        """Check Dragapult ex cards specifically"""
        print("🔍 Checking Dragapult ex cards specifically...")
        
        try:
            response = requests.get(
                f"{self.tcg_api_base}/cards",
                headers=self.headers,
                params={
                    'q': 'name:"Dragapult ex"',
                    'pageSize': 250
                }
            )
            response.raise_for_status()
            
            data = response.json()
            cards = data.get('data', [])
            
            print(f"Found {len(cards)} Dragapult ex cards:")
            print()
            
            for card in cards:
                legalities = card.get('legalities', {})
                standard_legal = legalities.get('standard') == 'Legal'
                regulation_mark = card.get('regulationMark')
                
                print(f"  - {card['name']} ({card['set']['name']}) - {card['id']}")
                print(f"    Standard Legal: {standard_legal}")
                print(f"    Regulation Mark: {regulation_mark}")
                print(f"    Release Date: {card['set'].get('releaseDate')}")
                print(f"    Rarity: {card.get('rarity')}")
                print()
                
        except Exception as e:
            print(f"❌ Error checking Dragapult ex: {e}")
            
    def check_sample_standard_cards(self):
        """Check a sample of standard legal cards to understand regulation mark patterns"""
        print("🔍 Checking sample standard legal cards...")
        
        try:
            response = requests.get(
                f"{self.tcg_api_base}/cards",
                headers=self.headers,
                params={
                    'q': 'legalities.standard:Legal',
                    'pageSize': 50,
                    'orderBy': 'set.releaseDate'
                }
            )
            response.raise_for_status()
            
            data = response.json()
            cards = data.get('data', [])
            
            print(f"Analyzing {len(cards)} standard legal cards:")
            print()
            
            regulation_marks = [card.get('regulationMark') for card in cards]
            regulation_counter = Counter(regulation_marks)
            
            print("Regulation mark distribution:")
            for mark, count in sorted(regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone'):
                mark_display = mark if mark is not None else 'None'
                percentage = (count / len(cards)) * 100
                print(f"  {mark_display}: {count} ({percentage:.1f}%)")
                
            print()
            print("Sample cards with None regulation mark:")
            none_cards = [card for card in cards if card.get('regulationMark') is None]
            for card in none_cards[:5]:
                print(f"  - {card['name']} ({card['set']['name']}) - {card['id']}")
                print(f"    Release Date: {card['set'].get('releaseDate')}")
                
        except Exception as e:
            print(f"❌ Error checking sample cards: {e}")
            
    def run_rotation_check(self):
        """Run the complete rotation check"""
        print("🔍 Starting Pokemon TCG rotation check...")
        print("=" * 60)
        
        # Check current standard sets
        self.check_current_standard_sets()
        print("=" * 60)
        
        # Check Dragapult ex specifically
        self.check_dragapult_ex_specifically()
        print("=" * 60)
        
        # Check sample standard cards
        self.check_sample_standard_cards()
        print("=" * 60)

def main():
    """Main function to run the rotation check"""
    try:
        checker = RotationChecker()
        checker.run_rotation_check()
        
    except KeyboardInterrupt:
        print("\n❌ Check cancelled by user")
    except Exception as e:
        print(f"❌ Check failed: {e}")
        raise

if __name__ == "__main__":
    main()