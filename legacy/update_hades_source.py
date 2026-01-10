import json
import time

TRACKING_FILE = "image_sources.json"
CHAR_NAME = "hades"

try:
    with open(TRACKING_FILE, 'r') as f:
        data = json.load(f)
    
    if CHAR_NAME in data:
        data[CHAR_NAME]['source'] = 'gemini_antigravity'
        data[CHAR_NAME]['generated_at'] = time.time()
        print(f"Updated {CHAR_NAME}")
    else:
        print(f"{CHAR_NAME} not found")

    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

except Exception as e:
    print(f"Error: {e}")
