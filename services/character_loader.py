"""
Character Loader Service - Load character data from CSV
Replaces database queries for static character data
"""
import csv
import os
from typing import Optional, List, Dict, Any

class CharacterLoader:
    """Load and cache character data from CSV file"""
    
    def __init__(self):
        self._cache = None
        self._cache_by_id = {}
        self._cache_by_name = {}
    
    def load_characters_from_csv(self) -> List[Dict[str, Any]]:
        """Load all characters from CSV with caching"""
        if self._cache is not None:
            return self._cache
        
        # Helper to safely convert to int
        def safe_int(value, default=0):
            if not value or value.strip() == '':
                return default
            try:
                return int(value)
            except ValueError:
                return default
        
        # Helper to safely convert to float
        def safe_float(value, default=0.0):
            if not value or value.strip() == '':
                return default
            try:
                return float(value)
            except ValueError:
                return default

        characters = []
        try:
            with open('data/characters.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    char = {
                        'id': safe_int(row.get('id')),
                        'nome': row.get('nome', ''),
                        'livello': safe_int(row.get('livello'), 1),
                        'lv_premium': safe_int(row.get('lv_premium'), 0),
                        'exp_required': safe_int(row.get('exp_required'), 100),
                        'special_attack_name': row.get('special_attack_name', ''),
                        'special_attack_damage': safe_int(row.get('special_attack_damage'), 0),
                        'special_attack_mana_cost': safe_int(row.get('special_attack_mana_cost'), 0),
                        'price': safe_int(row.get('price'), 0),
                        'description': row.get('description', ''),
                        'character_group': row.get('character_group', 'General'),
                        'max_concurrent_owners': safe_int(row.get('max_concurrent_owners'), -1),
                        'is_pokemon': safe_int(row.get('is_pokemon'), 0),
                        'elemental_type': row.get('elemental_type', 'Normal'),
                        'crit_chance': safe_int(row.get('crit_chance'), 5),
                        'crit_multiplier': safe_float(row.get('crit_multiplier'), 1.5),
                        'required_character_id': safe_int(row.get('required_character_id'), None) if row.get('required_character_id', '').strip() else None,
                        # Transformation fields
                        'is_transformation': safe_int(row.get('is_transformation'), 0),
                        'base_character_id': safe_int(row.get('base_character_id'), None) if row.get('base_character_id', '').strip() else None,
                        'transformation_mana_cost': safe_int(row.get('transformation_mana_cost'), 0),
                        'transformation_duration_days': safe_int(row.get('transformation_duration_days'), 0),
                    }
                    characters.append(char)
                    
                    # Build lookup caches
                    self._cache_by_id[char['id']] = char
                    self._cache_by_name[char['nome']] = char
                    
        except Exception as e:
            print(f"Error loading characters from CSV: {e}")
            import traceback
            traceback.print_exc()
            self._cache = []
            return []
        
        # Sort by level
        characters.sort(key=lambda x: x['livello'])
        self._cache = characters
        return characters
    
    def get_character_by_id(self, char_id: int) -> Optional[Dict[str, Any]]:
        """Get character by ID"""
        if not self._cache:
            self.load_characters_from_csv()
        return self._cache_by_id.get(char_id)
    
    def get_character_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get character by name"""
        if not self._cache:
            self.load_characters_from_csv()
        return self._cache_by_name.get(name)
    
    def get_characters_by_level(self, level: int) -> List[Dict[str, Any]]:
        """Get all characters for a specific level"""
        if not self._cache:
            self.load_characters_from_csv()
        return [c for c in self._cache if c['livello'] == level]
    
    def get_all_characters(self) -> List[Dict[str, Any]]:
        """Get all characters sorted by level"""
        if not self._cache:
            self.load_characters_from_csv()
        return self._cache.copy()
    
    def filter_characters(self, level: Optional[int] = None, 
                         lv_premium: Optional[int] = None,
                         purchasable_only: bool = False) -> List[Dict[str, Any]]:
        """Filter characters by various criteria"""
        if not self._cache:
            self.load_characters_from_csv()
        
        result = self._cache.copy()
        
        if level is not None:
            result = [c for c in result if c['livello'] <= level]
        
        if lv_premium is not None:
            result = [c for c in result if c['lv_premium'] == lv_premium]
        
        if purchasable_only:
            result = [c for c in result if c['lv_premium'] == 2 and c['price'] > 0]
        
        return result
    
    def get_character_levels(self) -> List[int]:
        """Get unique character levels"""
        if not self._cache:
            self.load_characters_from_csv()
        levels = sorted(set(c['livello'] for c in self._cache))
        return levels
    
    def get_all_sagas(self) -> List[str]:
        """Get unique character sagas/groups sorted alphabetically"""
        if not self._cache:
            self.load_characters_from_csv()
        sagas = sorted(set(c['character_group'] for c in self._cache if c['character_group']))
        return sagas
    
    def get_characters_by_saga(self, saga: str) -> List[Dict[str, Any]]:
        """Get all characters for a specific saga, sorted by level"""
        if not self._cache:
            self.load_characters_from_csv()
        chars = [c for c in self._cache if c['character_group'] == saga]
        chars.sort(key=lambda x: x['livello'])
        return chars
    
    def is_transformation(self, char_id: int) -> bool:
        """Check if a character is a transformation (not base form)"""
        char = self.get_character_by_id(char_id)
        if not char:
            return False
        return char.get('is_transformation', 0) == 1
    
    def get_base_character(self, char_id: int) -> Optional[Dict[str, Any]]:
        """Get the base character for a transformation"""
        char = self.get_character_by_id(char_id)
        if not char or not char.get('base_character_id'):
            return None
        return self.get_character_by_id(char['base_character_id'])
    
    def get_transformations_for_base(self, base_char_id: int) -> List[Dict[str, Any]]:
        """Get all transformations available for a base character"""
        if not self._cache:
            self.load_characters_from_csv()
        return [c for c in self._cache if c.get('base_character_id') == base_char_id]
    
    def get_transformation_chain(self, char_id: int) -> List[Dict[str, Any]]:
        """Get the full transformation chain starting from this character"""
        chain = []
        current_id = char_id
        visited = set()
        
        while current_id and current_id not in visited:
            visited.add(current_id)
            transforms = self.get_transformations_for_base(current_id)
            if transforms:
                chain.extend(transforms)
                # Continue with first transformation's ID for next level
                current_id = transforms[0]['id']
            else:
                break
        
        return chain
    
    def clear_cache(self):
        """Clear the cache (useful for testing or reloading data)"""
        self._cache = None
        self._cache_by_id = {}
        self._cache_by_name = {}

# Singleton instance
_character_loader = None

def get_character_loader() -> CharacterLoader:
    """Get singleton instance of CharacterLoader"""
    global _character_loader
    if _character_loader is None:
        _character_loader = CharacterLoader()
    return _character_loader

def get_character_image(character: Dict[str, Any], is_locked: bool = False):
    """
    Get image for character.
    Returns an open file object or None if not found.
    """
    if not character:
        return None
        
    # TODO: Check for telegram_file_id in character dict if we add it to CSV
    
    # Try local file
    # Normalize name: "Crash Bandicoot" -> "crash_bandicoot"
    safe_name = character['nome'].lower().replace(' ', '_')
    
    # Check possible extensions
    for ext in ['.png', '.jpg', '.jpeg']:
        path = f"images/characters/{safe_name}{ext}"
        if os.path.exists(path):
            try:
                return open(path, 'rb')
            except Exception as e:
                print(f"Error opening image {path}: {e}")
                return None
                
    return None
