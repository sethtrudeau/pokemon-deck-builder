#!/usr/bin/env python3
"""
Database verification script for Pokemon card import
Checks total cards, standard legality, and regulation mark breakdown
"""

import os
import sys
from collections import Counter
from supabase import create_client, Client
from decouple import config

class DatabaseVerifier:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    def verify_import_results(self):
        """Verify the Pokemon card import results"""
        print("🔍 Verifying Pokemon card import results...")
        
        try:
            # Get all cards from database
            result = self.supabase.table('pokemon_cards').select('*').execute()
            all_cards = result.data
            
            total_cards = len(all_cards)
            print(f"\n📊 Database Summary:")
            print(f"Total cards in database: {total_cards}")
            
            # Count standard legal vs non-standard
            standard_legal_count = sum(1 for card in all_cards if card.get('standard_legal'))
            non_standard_count = total_cards - standard_legal_count
            
            print(f"\n📈 Standard Legality Breakdown:")
            print(f"  Standard legal (true): {standard_legal_count}")
            print(f"  Non-standard (false): {non_standard_count}")
            print(f"  Standard legal percentage: {(standard_legal_count/total_cards)*100:.1f}%")
            
            # Count regulation marks
            regulation_marks = [card.get('regulation_mark') for card in all_cards]
            regulation_counter = Counter(regulation_marks)
            
            print(f"\n🏷️  Regulation Mark Breakdown:")
            # Sort with None values handled properly
            sorted_items = sorted(regulation_counter.items(), key=lambda x: x[0] if x[0] is not None else 'zzzNone')
            for reg_mark, count in sorted_items:
                mark_display = reg_mark if reg_mark is not None else 'None'
                percentage = (count/total_cards)*100
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
                percentage = (count/total_cards)*100
                print(f"  {type_display}: {count} ({percentage:.1f}%)")
            
            # Check for cards with regulation marks G, H, I that are NOT standard legal
            print(f"\n🔍 Filtering Logic Verification:")
            ghi_cards = [card for card in all_cards if card.get('regulation_mark') in current_standard_marks]
            ghi_not_standard = [card for card in ghi_cards if not card.get('standard_legal')]
            
            print(f"  Cards with G/H/I regulation marks: {len(ghi_cards)}")
            print(f"  G/H/I cards NOT marked as standard legal: {len(ghi_not_standard)}")
            
            if ghi_not_standard:
                print("  Examples of G/H/I cards not marked as standard:")
                for card in ghi_not_standard[:5]:  # Show first 5 examples
                    print(f"    - {card.get('name')} ({card.get('card_id')}) - Mark: {card.get('regulation_mark')}")
            
            # Check for standard legal cards without G/H/I marks
            standard_non_ghi = [card for card in all_cards if card.get('standard_legal') and card.get('regulation_mark') not in current_standard_marks]
            print(f"  Standard legal cards WITHOUT G/H/I marks: {len(standard_non_ghi)}")
            
            if standard_non_ghi:
                print("  Examples of standard legal cards without G/H/I marks:")
                for card in standard_non_ghi[:5]:  # Show first 5 examples
                    print(f"    - {card.get('name')} ({card.get('card_id')}) - Mark: {card.get('regulation_mark')}")
            
            # Check recent cards to verify import freshness
            print(f"\n🕐 Recent Import Verification:")
            recent_cards = sorted(all_cards, key=lambda x: x.get('last_updated', ''), reverse=True)[:10]
            print("  Most recently updated cards:")
            for card in recent_cards:
                print(f"    - {card.get('name')} ({card.get('set_name')}) - Updated: {card.get('last_updated')}")
            
            # Summary assessment
            print(f"\n✅ Import Assessment:")
            expected_standard_ratio = 0.2  # Expecting around 20% standard legal with stricter filtering
            actual_standard_ratio = standard_legal_count / total_cards
            
            if actual_standard_ratio < expected_standard_ratio:
                print(f"  ✅ Strict filtering appears to be working correctly")
                print(f"  ✅ Standard legal ratio ({actual_standard_ratio:.1%}) is lower than expected, indicating effective filtering")
            else:
                print(f"  ⚠️  Standard legal ratio ({actual_standard_ratio:.1%}) is higher than expected")
                print(f"  ⚠️  May need to review filtering logic")
            
            print(f"\n🎯 Key Metrics:")
            print(f"  Total cards: {total_cards}")
            print(f"  Standard legal: {standard_legal_count} ({(standard_legal_count/total_cards)*100:.1f}%)")
            print(f"  G/H/I regulation marks: {ghi_total}")
            print(f"  Filtering effectiveness: {'✅ Good' if actual_standard_ratio < 0.3 else '⚠️ Review needed'}")
            
        except Exception as e:
            print(f"❌ Error verifying import: {e}")
            raise

def main():
    """Main function to run the verification"""
    try:
        verifier = DatabaseVerifier()
        verifier.verify_import_results()
        
    except KeyboardInterrupt:
        print("\n❌ Verification cancelled by user")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        raise

if __name__ == "__main__":
    main()