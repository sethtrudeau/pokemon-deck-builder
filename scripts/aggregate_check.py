#!/usr/bin/env python3
"""
Aggregate database check for Pokemon card import
Uses SQL aggregation to get full database statistics without loading all records
"""

import os
import sys
from supabase import create_client, Client
from decouple import config

class AggregateChecker:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    def get_aggregate_stats(self):
        """Get aggregate statistics using SQL functions"""
        print("🔍 Getting aggregate database statistics...")
        
        try:
            # Get total count
            count_result = self.supabase.table('pokemon_cards').select('*', count='exact').execute()
            total_count = count_result.count
            print(f"📊 Total cards in database: {total_count}")
            
            # Get standard legal count
            standard_result = self.supabase.table('pokemon_cards').select('*', count='exact').eq('standard_legal', True).execute()
            standard_count = standard_result.count
            non_standard_count = total_count - standard_count
            
            print(f"\n📈 Standard Legality Breakdown:")
            print(f"  Standard legal (true): {standard_count}")
            print(f"  Non-standard (false): {non_standard_count}")
            print(f"  Standard legal percentage: {(standard_count/total_count)*100:.1f}%")
            
            # Get regulation mark counts
            print(f"\n🏷️  Regulation Mark Breakdown:")
            regulation_marks = ['D', 'E', 'F', 'G', 'H', 'I']
            regulation_counts = {}
            
            for mark in regulation_marks:
                result = self.supabase.table('pokemon_cards').select('*', count='exact').eq('regulation_mark', mark).execute()
                count = result.count
                regulation_counts[mark] = count
                percentage = (count/total_count)*100
                print(f"  {mark}: {count} ({percentage:.1f}%)")
            
            # Get NULL regulation marks
            null_result = self.supabase.table('pokemon_cards').select('*', count='exact').is_('regulation_mark', 'null').execute()
            null_count = null_result.count
            regulation_counts['None'] = null_count
            percentage = (null_count/total_count)*100
            print(f"  None: {null_count} ({percentage:.1f}%)")
            
            # Calculate G, H, I total
            ghi_total = regulation_counts.get('G', 0) + regulation_counts.get('H', 0) + regulation_counts.get('I', 0)
            print(f"\n⭐ Current Standard Marks (G, H, I) Total: {ghi_total}")
            
            # Get card type counts
            print(f"\n🃏 Card Type Breakdown:")
            card_types = ['Pokémon', 'Trainer', 'Energy']
            
            for card_type in card_types:
                result = self.supabase.table('pokemon_cards').select('*', count='exact').eq('card_type', card_type).execute()
                count = result.count
                percentage = (count/total_count)*100
                print(f"  {card_type}: {count} ({percentage:.1f}%)")
            
            # Get NULL card types
            null_type_result = self.supabase.table('pokemon_cards').select('*', count='exact').is_('card_type', 'null').execute()
            null_type_count = null_type_result.count
            percentage = (null_type_count/total_count)*100
            print(f"  Unknown: {null_type_count} ({percentage:.1f}%)")
            
            # Verification checks
            print(f"\n🔍 Filtering Logic Verification:")
            
            # Check G/H/I cards that are NOT standard legal
            ghi_not_standard = 0
            for mark in ['G', 'H', 'I']:
                result = self.supabase.table('pokemon_cards').select('*', count='exact').eq('regulation_mark', mark).eq('standard_legal', False).execute()
                ghi_not_standard += result.count
            
            print(f"  G/H/I cards NOT marked as standard legal: {ghi_not_standard}")
            
            # Check standard legal cards without G/H/I marks
            standard_non_ghi = self.supabase.table('pokemon_cards').select('*', count='exact').eq('standard_legal', True).not_.in_('regulation_mark', ['G', 'H', 'I']).execute()
            standard_non_ghi_count = standard_non_ghi.count
            print(f"  Standard legal cards WITHOUT G/H/I marks: {standard_non_ghi_count}")
            
            # Get recent updates sample
            print(f"\n🕐 Recent Import Verification:")
            recent_result = self.supabase.table('pokemon_cards').select('card_id, set_name, last_updated').order('last_updated', desc=True).limit(10).execute()
            print("  Most recently updated cards:")
            for card in recent_result.data:
                print(f"    - {card.get('card_id')} ({card.get('set_name')}) - Updated: {card.get('last_updated')}")
            
            # Summary assessment
            print(f"\n✅ Import Assessment:")
            expected_standard_ratio = 0.2  # Expecting around 20% standard legal with stricter filtering
            actual_standard_ratio = standard_count / total_count
            
            if actual_standard_ratio < 0.3:
                print(f"  ✅ Strict filtering appears to be working correctly")
                print(f"  ✅ Standard legal ratio ({actual_standard_ratio:.1%}) indicates effective filtering")
            else:
                print(f"  ⚠️  Standard legal ratio ({actual_standard_ratio:.1%}) is higher than expected")
                print(f"  ⚠️  May need to review filtering logic")
            
            print(f"\n🎯 Final Summary:")
            print(f"  Total cards in database: {total_count}")
            print(f"  Standard legal cards: {standard_count} ({(standard_count/total_count)*100:.1f}%)")
            print(f"  G/H/I regulation marks: {ghi_total}")
            print(f"  Filtering logic: {'✅ Working correctly' if ghi_not_standard == 0 and standard_non_ghi_count == 0 else '⚠️ Issues detected'}")
            
            # Cross-check with import summary
            print(f"\n🔄 Cross-check with import summary:")
            print(f"  You mentioned 6,049 total cards processed - Database shows: {total_count}")
            print(f"  You mentioned 254 standard legal cards - Database shows: {standard_count}")
            print(f"  Data consistency: {'✅ Matches' if total_count == 6049 and standard_count == 254 else '⚠️ Discrepancy detected'}")
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            raise

def main():
    """Main function to run the aggregate check"""
    try:
        checker = AggregateChecker()
        checker.get_aggregate_stats()
        
    except KeyboardInterrupt:
        print("\n❌ Check cancelled by user")
    except Exception as e:
        print(f"❌ Check failed: {e}")
        raise

if __name__ == "__main__":
    main()