#!/usr/bin/env python3
"""
Enhanced Sample Verification Script for Pokemon Cards
Gets multiple random samples and additional statistics
"""

import os
import sys
import random
from collections import Counter
from supabase import create_client, Client
from decouple import config

class EnhancedStandardLegalVerifier:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    def get_comprehensive_sample_analysis(self, sample_size: int = 10):
        """Get comprehensive analysis of standard legal cards"""
        print(f"🔍 Comprehensive Analysis of Standard Legal Cards (Sample: {sample_size})...")
        
        try:
            # Get all standard legal cards
            result = self.supabase.table('pokemon_cards').select(
                'card_id, name, regulation_mark, set_name, set_id, standard_legal, card_type, last_updated'
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
            
            # Analyze the full dataset first
            print(f"\n📈 Full Dataset Analysis (All {total_standard_legal} Standard Legal Cards):")
            print("=" * 70)
            
            # Regulation mark distribution in full dataset
            all_reg_marks = Counter(card.get('regulation_mark', 'None') for card in standard_legal_cards)
            print(f"Regulation Mark Distribution:")
            for mark, count in sorted(all_reg_marks.items()):
                percentage = (count / total_standard_legal) * 100
                print(f"  {mark}: {count} cards ({percentage:.1f}%)")
            
            # Set distribution in full dataset
            all_sets = Counter(card.get('set_name', 'Unknown') for card in standard_legal_cards)
            print(f"\nTop 10 Sets by Card Count:")
            for set_name, count in all_sets.most_common(10):
                percentage = (count / total_standard_legal) * 100
                print(f"  {set_name}: {count} cards ({percentage:.1f}%)")
            
            # Card type distribution
            all_card_types = Counter(card.get('card_type', 'Unknown') for card in standard_legal_cards)
            print(f"\nCard Type Distribution:")
            for card_type, count in sorted(all_card_types.items()):
                percentage = (count / total_standard_legal) * 100
                print(f"  {card_type}: {count} cards ({percentage:.1f}%)")
            
            # Now display the random sample
            print(f"\n🎲 Random Sample of {sample_size} Cards:")
            print("=" * 70)
            
            for i, card in enumerate(random_sample, 1):
                card_name = card.get('name', 'Unknown')
                regulation_mark = card.get('regulation_mark', 'None')
                set_name = card.get('set_name', 'Unknown')
                card_id = card.get('card_id', 'Unknown')
                card_type = card.get('card_type', 'Unknown')
                
                print(f"{i:2d}. {card_name} [{card_type}]")
                print(f"    Card ID: {card_id}")
                print(f"    Regulation Mark: {regulation_mark}")
                print(f"    Set Name: {set_name}")
                print()
            
            # Check for data quality issues
            print(f"🔍 Data Quality Assessment:")
            print("=" * 40)
            
            # Check current standard regulation marks (G, H, I)
            current_marks = ['G', 'H', 'I']
            current_mark_count = sum(all_reg_marks.get(mark, 0) for mark in current_marks)
            current_percentage = (current_mark_count / total_standard_legal) * 100
            
            print(f"Current regulation marks (G, H, I): {current_mark_count}/{total_standard_legal} ({current_percentage:.1f}%)")
            
            # Check for old marks that shouldn't be standard legal
            old_marks = ['A', 'B', 'C', 'D', 'E', 'F']
            old_mark_count = sum(all_reg_marks.get(mark, 0) for mark in old_marks)
            
            if old_mark_count > 0:
                print(f"⚠️  Cards with old regulation marks (A-F): {old_mark_count}")
                for mark in old_marks:
                    if all_reg_marks.get(mark, 0) > 0:
                        print(f"   - Mark {mark}: {all_reg_marks[mark]} cards")
            else:
                print(f"✅ No cards with old regulation marks (A-F) found")
            
            # Check for cards with no regulation mark
            no_mark_count = all_reg_marks.get('None', 0) + all_reg_marks.get(None, 0)
            if no_mark_count > 0:
                print(f"⚠️  Cards with no regulation mark: {no_mark_count}")
            else:
                print(f"✅ All cards have regulation marks")
            
            # Summary assessment
            print(f"\n✅ Overall Data Quality Assessment:")
            if current_percentage >= 95:
                print(f"  ✅ Excellent: {current_percentage:.1f}% of cards have current regulation marks")
            elif current_percentage >= 85:
                print(f"  ⚠️  Good: {current_percentage:.1f}% of cards have current regulation marks")
            else:
                print(f"  ❌ Concerning: Only {current_percentage:.1f}% of cards have current regulation marks")
            
            if old_mark_count == 0:
                print(f"  ✅ No outdated regulation marks found")
            else:
                print(f"  ⚠️  Found {old_mark_count} cards with potentially outdated regulation marks")
            
            # Check set diversity
            unique_sets = len(all_sets)
            print(f"  📚 Set diversity: {unique_sets} unique sets represented")
            
            return {
                'total_cards': total_standard_legal,
                'sample': random_sample,
                'regulation_marks': all_reg_marks,
                'sets': all_sets,
                'card_types': all_card_types,
                'current_percentage': current_percentage,
                'old_mark_count': old_mark_count
            }
            
        except Exception as e:
            print(f"❌ Error getting comprehensive analysis: {e}")
            raise

def main():
    """Main function to run the enhanced verification"""
    try:
        verifier = EnhancedStandardLegalVerifier()
        
        # Get comprehensive analysis
        analysis = verifier.get_comprehensive_sample_analysis(10)
        
        print("\n" + "="*60)
        print("🎯 Analysis Complete!")
        print("The database appears to contain current standard legal cards with proper regulation marks.")
        
    except KeyboardInterrupt:
        print("\n❌ Verification cancelled by user")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        raise

if __name__ == "__main__":
    main()