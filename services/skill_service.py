from database import Database
from models.system import CharacterAbility
import csv

class SkillService:
    """Service for managing character skills/abilities"""
    
    def __init__(self):
        self.db = Database()
        self.abilities_cache = None
    
    def load_abilities_from_csv(self):
        """Load abilities from CSV file"""
        if self.abilities_cache is not None:
            return self.abilities_cache
            
        abilities = []
        try:
            with open('data/abilities.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    abilities.append({
                        'id': int(row['id']),
                        'character_id': int(row['character_id']),
                        'name': row['name'],
                        'damage': int(row['damage']),
                        'mana_cost': int(row['mana_cost']),
                        'elemental_type': row['elemental_type'],
                        'crit_chance': int(row.get('crit_chance', 5)),
                        'crit_multiplier': float(row.get('crit_multiplier', 1.5)),
                        'status_effect': row.get('status_effect', ''),
                        'status_chance': int(row.get('status_chance', 0)),
                        'status_duration': int(row.get('status_duration', 0)),
                        'description': row.get('description', '')
                    })
        except Exception as e:
            print(f"Error loading abilities: {e}")
        
        self.abilities_cache = abilities
        return abilities
    
    def get_character_abilities(self, character_id):
        """Get all abilities for a character from CSV"""
        abilities = self.load_abilities_from_csv()
        return [a for a in abilities if a['character_id'] == character_id]
    
    def get_character_abilities_from_db(self, character_id):
        """Get abilities from database"""
        session = self.db.get_session()
        abilities = session.query(CharacterAbility).filter_by(character_id=character_id).all()
        session.close()
        return abilities
    
    def get_ability_by_id(self, ability_id):
        """Get specific ability by ID from CSV"""
        abilities = self.load_abilities_from_csv()
        for ability in abilities:
            if ability['id'] == ability_id:
                return ability
        return None
    
    def sync_abilities_to_db(self):
        """Sync CSV abilities to database"""
        session = self.db.get_session()
        abilities = self.load_abilities_from_csv()
        
        # Clear existing abilities
        session.query(CharacterAbility).delete()
        
        # Add all abilities from CSV
        for ability_data in abilities:
            ability = CharacterAbility(
                id=ability_data['id'],
                character_id=ability_data['character_id'],
                name=ability_data['name'],
                damage=ability_data['damage'],
                mana_cost=ability_data['mana_cost'],
                elemental_type=ability_data['elemental_type'],
                crit_chance=ability_data['crit_chance'],
                crit_multiplier=ability_data['crit_multiplier'],
                status_effect=ability_data['status_effect'] if ability_data['status_effect'] else None,
                status_chance=ability_data['status_chance'],
                status_duration=ability_data['status_duration'],
                description=ability_data['description']
            )
            session.add(ability)
        
        session.commit()
        session.close()
        print(f"Synced {len(abilities)} abilities to database")
        return True
