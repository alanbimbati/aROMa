from database import Database
from models.system import Livello, CharacterTransformation

def populate_vegito():
    db = Database()
    session = db.get_session()
    
    # 1. Create Vegito Character
    vegito = session.query(Livello).filter_by(nome="Vegito").first()
    if not vegito:
        vegito = Livello(
            livello=999, # Special level
            nome="Vegito",
            lv_premium=1,
            price=0,
            elemental_type="Normal",
            crit_chance=20,
            crit_multiplier=2.0,
            special_attack_name="Final Kamehameha",
            special_attack_damage=500,
            special_attack_mana_cost=100,
            description="La fusione Potara tra Goku e Vegeta.",
            character_group="Dragon Ball"
        )
        session.add(vegito)
        session.commit()
        print("Created Vegito character.")
    else:
        print("Vegito already exists.")
        
    # 2. Create Transformation
    # We use base_character_id=0 as a wildcard/dummy
    trans = session.query(CharacterTransformation).filter_by(transformation_name="Potara Fusion").first()
    if not trans:
        trans = CharacterTransformation(
            base_character_id=0, 
            transformed_character_id=vegito.id,
            transformation_name="Potara Fusion",
            wumpa_cost=0,
            duration_days=0, # Handled manually
            health_bonus=500,
            mana_bonus=200,
            damage_bonus=100,
            is_progressive=False,
            required_level=1
        )
        session.add(trans)
        session.commit()
        print("Created Potara Fusion transformation.")
    else:
        print("Potara Fusion transformation already exists.")
        
    session.close()

if __name__ == "__main__":
    populate_vegito()
