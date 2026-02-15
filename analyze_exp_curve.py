import csv
import math

# Formula from user_service.py
def get_formula_exp(level):
    if level >= 50:
        exp_at_50 = 100 * (50 ** 2) # 250,000
        if 50 < level <= 55:
            return exp_at_50 + (level - 50) * 5000
        elif level > 55:
            exp_at_55 = exp_at_50 + (5 * 5000) # 275,000
            n = level - 55
            return exp_at_55 + (n * 5000) + (n * (n - 1) // 2) * 2000
    
    if level >= 45:
        return int(85 * (level ** 2))
    
    return 100 * (level ** 2)

# Read CSV Data
csv_data = {}
try:
    with open('data/characters.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lvl = int(row['livello'])
                exp = int(row['exp_required'])
                if lvl not in csv_data:
                    csv_data[lvl] = []
                csv_data[lvl].append(exp)
            except:
                continue
except FileNotFoundError:
    print("CSV not found")

# Generate Comparison
print("Level,Formula_EXP,Min_CSV,Max_CSV,Gap")
for lvl in range(1, 101):
    formula = get_formula_exp(lvl)
    csv_vals = csv_data.get(lvl, [])
    
    min_csv = min(csv_vals) if csv_vals else ""
    max_csv = max(csv_vals) if csv_vals else ""
    
    gap = ""
    if min_csv and isinstance(min_csv, int):
        gap = min_csv - formula

    print(f"{lvl},{formula},{min_csv},{max_csv},{gap}")
