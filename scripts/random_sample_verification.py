#!/usr/bin/env python3
"""
Random Sample Verification Script for Pokemon Cards
Randomly samples 10 cards marked as standard_legal=true to verify data quality
"""

import os
import sys
import random
from supabase import create_client, Client
from decouple import config

class StandardLegalVerifier:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    def get_random_standard_legal_sample(self, sample_size: int = 10):
        """Get a random sample of standard legal cards for verification"""
        print(f"🎲 Randomly sampling {sample_size} standard legal cards for verification...")
        
        try:
            # Get all standard legal cards
            result = self.supabase.table('pokemon_cards').select(
                'card_id, name, regulation_mark, set_name, set_id, standard_legal, last_updated'
            ).eq('standard_legal', True).execute()
            
            standard_legal_cards = result.data
            total_standard_legal = len(standard_legal_cards)
            
            print(f"📊 Total standard legal cards in database: {total_standard_legal}")
            
            if total_standard_legal == 0:
                print("❌ No standard legal cards found in database!")
                return
            
            # Get random sample
            sample_size = min(sample_size, total_standard_legal)
            random_sample = random.sample(standard_legal_cards, sample_size)
            
            # Display sample information
            print(f"\n🔍 Random Sample of {sample_size} Standard Legal Cards:")
            print("=" * 80)
            
            # Group by regulation mark for analysis
            reg_mark_counts = {}
            set_name_counts = {}
            
            for i, card in enumerate(random_sample, 1):
                card_name = card.get('name', 'Unknown')
                regulation_mark = card.get('regulation_mark', 'None')
                set_name = card.get('set_name', 'Unknown')
                card_id = card.get('card_id', 'Unknown')
                last_updated = card.get('last_updated', 'Unknown')
                
                # Count regulation marks and sets
                reg_mark_counts[regulation_mark] = reg_mark_counts.get(regulation_mark, 0) + 1
                set_name_counts[set_name] = set_name_counts.get(set_name, 0) + 1
                
                print(f"{i:2d}. {card_name}")
                print(f"    Card ID: {card_id}")
                print(f"    Regulation Mark: {regulation_mark}")
                print(f"    Set Name: {set_name}")
                print(f"    Last Updated: {last_updated}")
                print()
            
            # Summary analysis
            print("📈 Sample Analysis:")
            print("=" * 40)
            
            print(f"Regulation Mark Distribution:")
            for reg_mark, count in sorted(reg_mark_counts.items()):
                percentage = (count / sample_size) * 100
                print(f"  {reg_mark}: {count} cards ({percentage:.1f}%)")
            
            print(f"\nSet Distribution:")
            for set_name, count in sorted(set_name_counts.items()):
                percentage = (count / sample_size) * 100
                print(f"  {set_name}: {count} cards ({percentage:.1f}%)")
            
            # Check for concerning patterns
            print(f"\n🔍 Data Quality Verification:")
            
            # Check current standard regulation marks (G, H, I)
            current_marks = ['G', 'H', 'I']
            current_mark_cards = [card for card in random_sample if card.get('regulation_mark') in current_marks]
            current_percentage = (len(current_mark_cards) / sample_size) * 100
            
            print(f"  Cards with current regulation marks (G, H, I): {len(current_mark_cards)}/{sample_size} ({current_percentage:.1f}%)")
            
            # Check for potentially outdated cards
            old_marks = ['A', 'B', 'C', 'D', 'E', 'F']
            old_mark_cards = [card for card in random_sample if card.get('regulation_mark') in old_marks]
            
            if old_mark_cards:
                print(f"  ⚠️  Cards with old regulation marks found: {len(old_mark_cards)}")
                for card in old_mark_cards:
                    print(f"    - {card.get('name')} (Mark: {card.get('regulation_mark')}, Set: {card.get('set_name')})")
            else:
                print(f"  ✅ No cards with old regulation marks (A-F) found")
            
            # Check for cards with no regulation mark
            no_mark_cards = [card for card in random_sample if not card.get('regulation_mark') or card.get('regulation_mark') == 'None']
            
            if no_mark_cards:
                print(f"  ⚠️  Cards with no regulation mark found: {len(no_mark_cards)}")
                for card in no_mark_cards:
                    print(f"    - {card.get('name')} (Set: {card.get('set_name')})")
            else:
                print(f"  ✅ All cards have regulation marks")
            
            # Overall assessment
            print(f"\n✅ Overall Assessment:")
            if current_percentage >= 80:
                print(f"  ✅ Excellent: {current_percentage:.1f}% of sample has current regulation marks")
            elif current_percentage >= 60:
                print(f"  ⚠️  Good: {current_percentage:.1f}% of sample has current regulation marks")
            else:
                print(f"  ❌ Concerning: Only {current_percentage:.1f}% of sample has current regulation marks")
            
            if not old_mark_cards:
                print(f"  ✅ No outdated regulation marks found in sample")
            else:
                print(f"  ⚠️  Found {len(old_mark_cards)} cards with potentially outdated regulation marks")
            
            return random_sample
            
        except Exception as e:
            print(f"❌ Error getting random sample: {e}")
            raise

    def verify_specific_cards(self, card_ids: list):
        """Verify specific cards by their IDs"""
        print(f"\n🔍 Verifying specific cards...")
        
        try:
            result = self.supabase.table('pokemon_cards').select(
                'card_id, name, regulation_mark, set_name, standard_legal, last_updated'
            ).in_('card_id', card_ids).execute()
            
            cards = result.data
            
            print(f"Found {len(cards)} cards:")
            for card in cards:
                print(f"  - {card.get('name')} ({card.get('card_id')})")
                print(f"    Standard Legal: {card.get('standard_legal')}")
                print(f"    Regulation Mark: {card.get('regulation_mark')}")
                print(f"    Set: {card.get('set_name')}")
                print()
                
        except Exception as e:
            print(f"❌ Error verifying specific cards: {e}")
            raise

def main():
    """Main function to run the verification"""
    try:
        verifier = StandardLegalVerifier()
        
        # Get random sample
        sample = verifier.get_random_standard_legal_sample(10)
        
        # Optional: Allow user to verify specific cards
        print("\n" + "="*60)
        print("💡 To verify specific cards, you can call:")
        print("   verifier.verify_specific_cards(['card_id_1', 'card_id_2', ...])")
        
    except KeyboardInterrupt:
        print("\n❌ Verification cancelled by user")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        raise

if __name__ == "__main__":
    main()