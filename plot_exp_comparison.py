import matplotlib.pyplot as plt
import csv

levels = []
formula_vals = []
min_vals = []
max_vals = []

try:
    with open('analysis_result.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lvl = int(row['Level'])
                formula = int(row['Formula_EXP']) if row['Formula_EXP'] else 0
                min_csv = int(row['Min_CSV']) if row['Min_CSV'] else None
                max_csv = int(row['Max_CSV']) if row['Max_CSV'] else None
                
                levels.append(lvl)
                formula_vals.append(formula)
                min_vals.append(min_csv)
                max_vals.append(max_csv)
            except ValueError:
                continue
except FileNotFoundError:
    print("CSV not found. Run analyze_exp_curve.py first.")
    exit(1)

plt.figure(figsize=(12, 6))

# Plot Formula Line
plt.plot(levels, formula_vals, label='Formula (Standard)', color='blue', linewidth=2)

# Plot scatter for CSV values to show spread
# Filter None values
valid_min = [(l, v) for l, v in zip(levels, min_vals) if v is not None]
valid_max = [(l, v) for l, v in zip(levels, max_vals) if v is not None]

# Scatter plot for CSV points
plt.scatter([x[0] for x in valid_min], [x[1] for x in valid_min], color='green', label='Min CSV Value', s=20, alpha=0.6)
plt.scatter([x[0] for x in valid_max], [x[1] for x in valid_max], color='red', label='Max CSV Value', s=20, alpha=0.6)

plt.title('EXP Curve Comparison: Formula vs CSV Overrides')
plt.xlabel('Level')
plt.ylabel('EXP Required')
plt.legend()
plt.grid(True)
plt.tight_layout()

output_path = '/home/alan/.gemini/antigravity/brain/1a146db8-9d2a-4694-b9eb-144ecd35935e/exp_curve_comparison.png'
plt.savefig(output_path)
print(f"Plot saved to {output_path}")
