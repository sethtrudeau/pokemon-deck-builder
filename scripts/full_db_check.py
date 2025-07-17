#!/usr/bin/env python3
"""
Full database check for Pokemon card import
Gets complete database counts and pagination info
"""

import os
import sys
from collections import Counter
from supabase import create_client, Client
from decouple import config

class FullDatabaseChecker:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    def get_full_database_stats(self):
        """Get complete database statistics"""
        print("🔍 Checking full database statistics...")
        
        try:
            # Get total count first
            count_result = self.supabase.table('pokemon_cards').select('*', count='exact').execute()
            total_count = count_result.count
            print(f"📊 Total cards in database: {total_count}")
            
            # Get cards with pagination if needed
            all_cards = []
            page_size = 1000
            page = 0
            
            while True:
                offset = page * page_size
                result = self.supabase.table('pokemon_cards').select('card_id, standard_legal, regulation_mark, card_type, set_name, last_updated').range(offset, offset + page_size - 1).execute()
                
                if not result.data:
                    break
                    
                all_cards.extend(result.data)
                page += 1
                print(f"  Loaded page {page}, total cards so far: {len(all_cards)}")
                
                # Continue until we've loaded all cards or get less than page_size
                if len(result.data) < page_size:
                    break
                    
                # Safety check to prevent infinite loop
                if len(all_cards) >= total_count:
                    break
            
            print(f"\n📈 Complete Database Analysis:")
            print(f"Total cards loaded: {len(all_cards)}")
            
            # Count standard legal vs non-standard
            standard_legal_count = sum(1 for card in all_cards if card.get('standard_legal'))
            non_standard_count = len(all_cards) - standard_legal_count
            
            print(f"\n📈 Standard Legality Breakdown:")
            print(f"  Standard legal (true): {standard_legal_count}")
            print(f"  Non-standard (false): {non_standard_count}")
            print(f"  Standard legal percentage: {(standard_legal_count/len(all_cards))*100:.1f}%")
            
            # Count regulation marks
            regulation_marks = [card.get('regulation_mark') for card in all_cards]
            regulation_counter = Counter(regulation_marks)
            
            print(f"\n🏷️  Regulation Mark Breakdown:")
            # Sort with None values handled properly
            sorted_items = sorted(regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone')
            for reg_mark, count in sorted_items:
                mark_display = reg_mark if reg_mark is not None else 'None'
                percentage = (count/len(all_cards))*100
                print(f"  {mark_display}: {count} ({percentage:.1f}%)")
            
            # Focus on G, H, I marks (current standard)
            current_standard_marks = ['G', 'H', 'I']
            ghi_total = sum(regulation_counter.get(mark, 0) for mark in current_standard_marks)
            print(f"\n⭐ Current Standard Marks (G, H, I) Total: {ghi_total}")
            
            # Count by card type
            card_types = [card.get('card_type') for card in all_cards]
            type_counter = Counter(card_types)
            
            print(f"\n🃏 Card Type Breakdown:")
            # Sort with None values handled properly
            sorted_types = sorted(type_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzUnknown')
            for card_type, count in sorted_types:
                type_display = card_type if card_type is not None else 'Unknown'
                percentage = (count/len(all_cards))*100
                print(f"  {type_display}: {count} ({percentage:.1f}%)")
            
            # Check filtering logic
            print(f"\n🔍 Filtering Logic Verification:")
            ghi_cards = [card for card in all_cards if card.get('regulation_mark') in current_standard_marks]
            ghi_not_standard = [card for card in ghi_cards if not card.get('standard_legal')]
            
            print(f"  Cards with G/H/I regulation marks: {len(ghi_cards)}")
            print(f"  G/H/I cards NOT marked as standard legal: {len(ghi_not_standard)}")
            
            # Check for standard legal cards without G/H/I marks
            standard_non_ghi = [card for card in all_cards if card.get('standard_legal') and card.get('regulation_mark') not in current_standard_marks]
            print(f"  Standard legal cards WITHOUT G/H/I marks: {len(standard_non_ghi)}")
            
            # Check recent updates
            print(f"\n🕐 Recent Import Verification:")
            recent_cards = sorted(all_cards, key=lambda x: x.get('last_updated', ''), reverse=True)[:10]
            print("  Most recently updated cards:")
            for card in recent_cards:
                print(f"    - {card.get('card_id')} ({card.get('set_name')}) - Updated: {card.get('last_updated')}")
            
            # Summary
            print(f"\n🎯 Final Summary:")
            print(f"  Total cards in database: {len(all_cards)}")
            print(f"  Standard legal cards: {standard_legal_count} ({(standard_legal_count/len(all_cards))*100:.1f}%)")
            print(f"  G/H/I regulation marks: {ghi_total}")
            print(f"  Filtering logic: {'✅ Working correctly' if len(ghi_not_standard) == 0 and len(standard_non_ghi) == 0 else '⚠️ Issues detected'}")
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            raise

def main():
    """Main function to run the full database check"""
    try:
        checker = FullDatabaseChecker()
        checker.get_full_database_stats()
        
    except KeyboardInterrupt:
        print("\n❌ Check cancelled by user")
    except Exception as e:
        print(f"❌ Check failed: {e}")
        raise

if __name__ == "__main__":
    main()