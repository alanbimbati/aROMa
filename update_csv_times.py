import csv
import shutil

# Config
TIMES = {
    1: 600,       # 10 min
    2: 1800,      # 30 min
    3: 14400,     # 4 hours
    4: 43200,     # 12 hours
    5: 86400      # 24 hours
}
POTARA_TIME = 172800 # 48 hours

input_file = 'data/equipment.csv'
output_file = 'data/equipment_updated.csv'

with open(input_file, 'r', encoding='utf-8') as infile, \
     open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in reader:
        rarity = int(row['rarity'])
        new_time = TIMES.get(rarity, 600)
        
        # Exception for Potara (ID 21) or based on name check if ID isn't reliable
        # CSV IDs: 21 is "Orecchini Potara"
        if row['id'] == '21' or 'Potara' in row['name']:
            new_time = POTARA_TIME
            
        row['crafting_time'] = str(new_time)
        writer.writerow(row)

shutil.move(output_file, input_file)
print("✅ equipment.csv updated successfully!")
