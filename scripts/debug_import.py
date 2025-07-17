#!/usr/bin/env python3
"""
Debug script to understand the import discrepancy
"""

import os
import sys
from supabase import create_client, Client
from decouple import config

class ImportDebugger:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    def debug_import_logic(self):
        """Debug the import logic discrepancy"""
        print("🔍 Debugging import logic...")
        
        try:
            # Get sample of cards to understand the data
            result = self.supabase.table('pokemon_cards').select('card_id, name, regulation_mark, standard_legal, set_name').limit(20).execute()
            
            print(f"📊 Sample of cards in database:")
            for card in result.data:
                reg_mark = card.get('regulation_mark', 'None')
                standard = card.get('standard_legal', False)
                print(f"  {card.get('name')} ({card.get('card_id')}) - Mark: {reg_mark}, Standard: {standard}")
            
            # Test the current logic against a few cards
            print(f"\n🧪 Testing current import logic:")
            current_standard_marks = ['G', 'H', 'I']
            
            for card in result.data[:5]:
                regulation_mark = card.get('regulation_mark')
                should_be_standard = regulation_mark in current_standard_marks
                actually_standard = card.get('standard_legal', False)
                
                print(f"  {card.get('name')}:")
                print(f"    Regulation mark: {regulation_mark}")
                print(f"    Should be standard (G/H/I): {should_be_standard}")
                print(f"    Actually marked standard: {actually_standard}")
                print(f"    Match: {'✅' if should_be_standard == actually_standard else '❌'}")
            
            # Check if there might be duplicate cards
            print(f"\n🔍 Checking for duplicate card IDs:")
            duplicate_result = self.supabase.table('pokemon_cards').select('card_id').execute()
            card_ids = [card.get('card_id') for card in duplicate_result.data]
            unique_ids = set(card_ids)
            
            print(f"  Total records: {len(card_ids)}")
            print(f"  Unique card IDs: {len(unique_ids)}")
            print(f"  Duplicates: {len(card_ids) - len(unique_ids)}")
            
            if len(card_ids) != len(unique_ids):
                print("  ⚠️  Duplicate card IDs found!")
            
            # Check for cards with missing regulation marks
            print(f"\n🔍 Checking cards with missing regulation marks:")
            none_result = self.supabase.table('pokemon_cards').select('card_id, name, regulation_mark, standard_legal').is_('regulation_mark', 'null').limit(10).execute()
            
            print(f"  Cards with None regulation marks:")
            for card in none_result.data:
                print(f"    {card.get('name')} ({card.get('card_id')}) - Standard: {card.get('standard_legal')}")
            
            # Check the actual counts one more time
            print(f"\n📊 Final count verification:")
            
            # Count all cards
            total_result = self.supabase.table('pokemon_cards').select('*', count='exact').execute()
            total_count = total_result.count
            
            # Count standard legal
            standard_result = self.supabase.table('pokemon_cards').select('*', count='exact').eq('standard_legal', True).execute()
            standard_count = standard_result.count
            
            # Count G/H/I cards
            ghi_result = self.supabase.table('pokemon_cards').select('*', count='exact').in_('regulation_mark', ['G', 'H', 'I']).execute()
            ghi_count = ghi_result.count
            
            print(f"  Total cards: {total_count}")
            print(f"  Standard legal cards: {standard_count}")
            print(f"  G/H/I regulation mark cards: {ghi_count}")
            print(f"  Logic consistency: {'✅' if standard_count == ghi_count else '❌'}")
            
            # The key insight: you mentioned 254 standard legal, but we have 3,262
            # This suggests either:
            # 1. The import was run with different logic
            # 2. There's a sampling/pagination issue in what you saw
            # 3. The definition of "standard legal" changed
            
            print(f"\n🎯 Key Insights:")
            print(f"  Expected (from your message): 254 standard legal cards")
            print(f"  Actual (from database): {standard_count} standard legal cards")
            print(f"  Difference: {standard_count - 254} cards")
            print(f"  This suggests the import processed ALL G/H/I cards as standard legal")
            
        except Exception as e:
            print(f"❌ Error debugging import: {e}")
            raise

def main():
    """Main function to run the debug"""
    try:
        debugger = ImportDebugger()
        debugger.debug_import_logic()
        
    except KeyboardInterrupt:
        print("\n❌ Debug cancelled by user")
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        raise

if __name__ == "__main__":
    main()