import csv
import os

input_file = 'data/characters.csv'
output_file = 'data/characters_updated_gif.csv'

def add_gif_column():
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8', newline='') as f_out:
        
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames
        if 'special_attack_gif' not in fieldnames:
            fieldnames.append('special_attack_gif')
            
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            # Initialize with empty string
            if 'special_attack_gif' not in row:
                row['special_attack_gif'] = ''
            writer.writerow(row)
            
    # Replace original file
    os.replace(output_file, input_file)
    print("Added special_attack_gif column to characters.csv successfully.")

if __name__ == "__main__":
    add_gif_column()
