#!/usr/bin/env python3
"""
Quick analysis of the main issues
"""

import os
import sys
import requests
from collections import Counter
from supabase import create_client, Client
from decouple import config

class QuickAnalyzer:
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
            
    def check_database_count_issue(self):
        """Check why the database count is inconsistent"""
        print("🔍 Checking database count issue...")
        
        # Get exact count
        count_result = self.supabase.table('pokemon_cards').select('*', count='exact').execute()
        total_count = count_result.count
        print(f"Exact database count: {total_count}")
        
        # Try to get actual data
        result = self.supabase.table('pokemon_cards').select('card_id, standard_legal').limit(1000).execute()
        print(f"Retrieved {len(result.data)} cards with limit 1000")
        
        # Check standard legal count
        standard_result = self.supabase.table('pokemon_cards').select('*', count='exact').eq('standard_legal', True).execute()
        standard_count = standard_result.count
        print(f"Standard legal cards: {standard_count}")
        
        return total_count, standard_count
        
    def check_regulation_marks_in_db(self):
        """Check regulation marks currently in database"""
        print("🔍 Checking regulation marks in database...")
        
        # Get regulation mark distribution
        result = self.supabase.table('pokemon_cards').select('regulation_mark').execute()
        regulation_marks = [card.get('regulation_mark') for card in result.data]
        regulation_counter = Counter(regulation_marks)
        
        print("Regulation marks in database:")
        for mark, count in sorted(regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone'):
            mark_display = mark if mark is not None else 'None'
            print(f"  {mark_display}: {count}")
            
        return regulation_counter
        
    def check_api_counts(self):
        """Check API counts quickly"""
        print("🔍 Checking API counts...")
        
        # Get total standard legal count from API
        response = requests.get(
            f"{self.tcg_api_base}/cards",
            headers=self.headers,
            params={
                'q': 'legalities.standard:Legal',
                'pageSize': 1
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            total_api_count = data.get('totalCount', 0)
            print(f"Total standard legal cards in API: {total_api_count}")
            return total_api_count
        else:
            print(f"API request failed: {response.status_code}")
            return 0
            
    def check_latest_sets(self):
        """Check what the latest sets are"""
        print("🔍 Checking latest sets...")
        
        response = requests.get(
            f"{self.tcg_api_base}/sets",
            headers=self.headers,
            params={
                'orderBy': 'releaseDate',
                'pageSize': 10
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            sets = data.get('data', [])
            
            # Sort by release date descending
            sorted_sets = sorted(sets, key=lambda x: x.get('releaseDate', ''), reverse=True)
            
            print("Latest sets:")
            for set_info in sorted_sets[:5]:
                legalities = set_info.get('legalities', {})
                standard_legal = legalities.get('standard') == 'Legal'
                print(f"  - {set_info['name']} ({set_info['id']}) - Released: {set_info.get('releaseDate')} - Standard: {standard_legal}")
                
    def check_import_script_logic(self):
        """Check the import script logic"""
        print("🔍 Checking import script logic...")
        
        # Current regulation marks in import script
        current_marks = ['G', 'H', 'I']
        print(f"Current regulation marks in import script: {current_marks}")
        
        # Get a sample of cards from API to see regulation marks
        response = requests.get(
            f"{self.tcg_api_base}/cards",
            headers=self.headers,
            params={
                'q': 'legalities.standard:Legal',
                'pageSize': 100,
                'orderBy': 'set.releaseDate'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            cards = data.get('data', [])
            
            regulation_marks = [card.get('regulationMark') for card in cards]
            regulation_counter = Counter(regulation_marks)
            
            print("Regulation marks in recent API standard legal cards:")
            for mark, count in sorted(regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone'):
                mark_display = mark if mark is not None else 'None'
                print(f"  {mark_display}: {count}")
                
            # Check if there are regulation marks we're missing
            api_marks = set(mark for mark in regulation_marks if mark is not None)
            current_marks_set = set(current_marks)
            
            missing_marks = api_marks - current_marks_set
            if missing_marks:
                print(f"\n⚠️ Regulation marks in API but not in import script: {missing_marks}")
                print("This could explain missing cards!")
            else:
                print("\n✅ All API regulation marks are covered by import script")
                
    def run_quick_analysis(self):
        """Run quick analysis"""
        print("🔍 Starting quick analysis...")
        print("=" * 60)
        
        # Check database counts
        total_db, standard_db = self.check_database_count_issue()
        print("=" * 60)
        
        # Check regulation marks in database
        db_regulation_marks = self.check_regulation_marks_in_db()
        print("=" * 60)
        
        # Check API counts
        api_total = self.check_api_counts()
        print("=" * 60)
        
        # Check latest sets
        self.check_latest_sets()
        print("=" * 60)
        
        # Check import script logic
        self.check_import_script_logic()
        print("=" * 60)
        
        print("🎯 QUICK ANALYSIS SUMMARY:")
        print(f"  Total cards in database: {total_db}")
        print(f"  Standard legal cards in database: {standard_db}")
        print(f"  Standard legal cards in API: {api_total}")
        
        if api_total > standard_db:
            print(f"  ⚠️ Missing {api_total - standard_db} cards from API!")
        else:
            print(f"  ✅ Database count matches or exceeds API count")
            
        # Check for regulation mark issues
        current_marks = ['G', 'H', 'I']
        db_ghi_total = sum(db_regulation_marks.get(mark, 0) for mark in current_marks)
        print(f"  G/H/I regulation marks in database: {db_ghi_total}")
        
        if db_ghi_total < standard_db:
            print(f"  ⚠️ Some standard legal cards don't have G/H/I marks!")
        else:
            print(f"  ✅ Regulation mark filtering appears consistent")

def main():
    """Main function to run the analysis"""
    try:
        analyzer = QuickAnalyzer()
        analyzer.run_quick_analysis()
        
    except KeyboardInterrupt:
        print("\n❌ Analysis cancelled by user")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise

if __name__ == "__main__":
    main()