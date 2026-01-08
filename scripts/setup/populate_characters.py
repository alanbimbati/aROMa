import sqlite3
import csv

def populate_characters():
    """Populate livello table with character data from CSV"""
    conn = sqlite3.connect('points.db')
    cursor = conn.cursor()
    
    print("Populating characters...")
    
    with open('data/characters.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Check if character exists
                cursor.execute("SELECT id FROM livello WHERE id = ?", (row['id'],))
                if cursor.fetchone():
                    # Update existing
                    cursor.execute("""
                        UPDATE livello SET
                            nome = ?,
                            livello = ?,
                            lv_premium = ?,
                            exp_required = ?,
                            special_attack_name = ?,
                            special_attack_damage = ?,
                            special_attack_mana_cost = ?,
                            price = ?,
                            description = ?
                        WHERE id = ?
                    """, (
                        row['nome'],
                        int(row['livello']),
                        int(row['lv_premium']),
                        int(row['exp_required']),
                        row['special_attack_name'],
                        int(row['special_attack_damage']),
                        int(row['special_attack_mana_cost']),
                        int(row['price']),
                        row['description'],
                        int(row['id'])
                    ))
                    print(f"  Updated: {row['nome']}")
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO livello (
                            id, nome, livello, lv_premium, exp_required,
                            special_attack_name, special_attack_damage,
                            special_attack_mana_cost, price, description
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        int(row['id']),
                        row['nome'],
                        int(row['livello']),
                        int(row['lv_premium']),
                        int(row['exp_required']),
                        row['special_attack_name'],
                        int(row['special_attack_damage']),
                        int(row['special_attack_mana_cost']),
                        int(row['price']),
                        row['description']
                    ))
                    print(f"  ✓ Added: {row['nome']}")
            except Exception as e:
                print(f"  ✗ Error with {row['nome']}: {e}")
    
    conn.commit()
    conn.close()
    print("\n✅ Character data populated!")

if __name__ == "__main__":
    populate_characters()
