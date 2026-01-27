import csv
import os

input_file = 'data/characters.csv'
output_file = 'data/characters_updated_goku_gif.csv'

def update_goku_gif():
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8', newline='') as f_out:
        
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            if row['nome'] == 'Goku':
                row['special_attack_gif'] = 'kamehameha.gif'
            writer.writerow(row)
            
    # Replace original file
    os.replace(output_file, input_file)
    print("Updated Goku with GIF successfully.")

if __name__ == "__main__":
    update_goku_gif()
