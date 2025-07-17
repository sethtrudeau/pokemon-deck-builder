#!/usr/bin/env python3
"""
Quick check for Dragapult ex in database
"""

import os
import sys
import json
from supabase import create_client, Client
from decouple import config

class DragapultChecker:
    def __init__(self):
        # Supabase configuration
        supabase_url = config('SUPABASE_URL')
        supabase_key = config('SUPABASE_ANON_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    def check_dragapult_ex(self):
        """Check for Dragapult ex in database"""
        print("🔍 Checking for Dragapult ex in database...")
        
        try:
            # Search for Dragapult ex specifically
            result = self.supabase.table('pokemon_cards').select('*').ilike('name', 'Dragapult ex').execute()
            
            cards = result.data
            print(f"Found {len(cards)} Dragapult ex cards in database:")
            print()
            
            for card in cards:
                print(f"📋 Card: {card['name']} ({card['set_name']}) - {card['card_id']}")
                print(f"   Standard Legal: {card.get('standard_legal')}")
                print(f"   Regulation Mark: {card.get('regulation_mark')}")
                print(f"   HP: {card.get('hp')}")
                print(f"   Types: {card.get('types')}")
                print(f"   Rarity: {card.get('rarity')}")
                print(f"   Card Number: {card.get('card_number')}")
                
                # Check attacks
                attacks = card.get('attacks', [])
                if attacks:
                    print(f"   Attacks:")
                    for i, attack in enumerate(attacks):
                        if isinstance(attack, dict):
                            attack_name = attack.get('name', 'Unknown')
                            attack_cost = attack.get('cost', [])
                            attack_damage = attack.get('damage', '')
                            attack_text = attack.get('text', '')
                            
                            print(f"     {i+1}. {attack_name}")
                            print(f"        Cost: {attack_cost}")
                            print(f"        Damage: {attack_damage}")
                            if attack_text:
                                print(f"        Text: {attack_text}")
                        else:
                            print(f"     {i+1}. {attack}")
                else:
                    print(f"   No attacks found")
                
                # Check abilities
                abilities = card.get('abilities', [])
                if abilities:
                    print(f"   Abilities:")
                    for i, ability in enumerate(abilities):
                        if isinstance(ability, dict):
                            ability_name = ability.get('name', 'Unknown')
                            ability_text = ability.get('text', '')
                            ability_type = ability.get('type', '')
                            
                            print(f"     {i+1}. {ability_name} ({ability_type})")
                            if ability_text:
                                print(f"        Text: {ability_text}")
                        else:
                            print(f"     {i+1}. {ability}")
                else:
                    print(f"   No abilities found")
                
                print()
                
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            
    def run_check(self):
        """Run the check"""
        print("🔍 Starting Dragapult ex database check...")
        print("=" * 60)
        
        self.check_dragapult_ex()

def main():
    """Main function to run the check"""
    try:
        checker = DragapultChecker()
        checker.run_check()
        
    except KeyboardInterrupt:
        print("\n❌ Check cancelled by user")
    except Exception as e:
        print(f"❌ Check failed: {e}")
        raise

if __name__ == "__main__":
    main()