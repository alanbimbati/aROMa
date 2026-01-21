import os
import time
import requests
# import openai  # Requires: pip install openai

import google.generativeai as genai
from google.api_core import exceptions

# ================= CONFIGURATION =================
# Get your API key from https://aistudio.google.com/
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDfFBvCLSFPQfmj-YVzG_Jg4LF2Q5omF8Y")
SOURCE_FILE = "prioritized_missing_images.txt"
MODEL_NAME = "models/imagen-3.0-generate-001" # Or "gemini-pro" if using for text, but for images check availability
# =================================================

def generate_image_api(prompt, output_path):
    """
    Generates an image using Google Gemini API (Imagen).
    """
    if API_KEY == "YOUR_GOOGLE_API_KEY_HERE":
        raise ValueError("Please configure your GOOGLE_API_KEY in the script!")

    print(f"🎨 Generating image for: {prompt}")
    
    # Using generateContent endpoint which is standard for Gemini models
    # Trying gemini-3-pro-image-preview as it was listed in available models
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent?key={API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            # Check for image data in the response
            # Gemini API image response structure might vary, usually it's in candidates -> content -> parts -> inlineData
            try:
                if "candidates" in result and result["candidates"]:
                    parts = result["candidates"][0]["content"]["parts"]
                    for part in parts:
                        if "inlineData" in part:
                            b64_data = part["inlineData"]["data"]
                            import base64
                            img_bytes = base64.b64decode(b64_data)
                            with open(output_path, "wb") as f:
                                f.write(img_bytes)
                            print(f"✅ Saved to {output_path}")
                            return True
                        elif "executableCode" in part:
                             print(f"⚠️  Model returned code instead of image.")
                        elif "text" in part:
                             print(f"⚠️  Model returned text: {part['text'][:100]}...")
                
                print(f"❌ No image data found in response: {result}")
                return False
            except Exception as parse_err:
                 print(f"❌ Error parsing response: {parse_err} - Response: {result}")
                 return False

        elif response.status_code == 429:
            raise RateLimitError("Quota exceeded")
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return False

    except RateLimitError:
        raise
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

class RateLimitError(Exception):
    pass

def main():
    if not os.path.exists(SOURCE_FILE):
        print(f"Error: {SOURCE_FILE} not found. Run 'prioritize_images.py' first.")
        return

    with open(SOURCE_FILE, 'r') as f:
        lines = f.readlines()

    print(f"Found {len(lines)} potential images to generate.")

    for line in lines:
        parts = line.strip().split('|')
        if len(parts) < 4:
            continue
        
        priority, item_type, name, relative_path = parts
        full_path = os.path.abspath(relative_path)
        
        # Check if image already exists
        if os.path.exists(full_path):
            print(f"⏭️  Skipping {name} (Already exists)")
            continue

        # Construct Prompt
        prompt = f"Epic digital art of {name} from {item_type}, high quality, detailed, 4k resolution"
        if item_type == "character":
            prompt += ", character portrait, dynamic pose"
        elif item_type == "boss":
            prompt += ", boss battle, menacing, powerful"

        # Retry Loop
        while True:
            try:
                success = generate_image_api(prompt, full_path)
                if success:
                    break # Move to next image
                else:
                    print("Skipping due to error.")
                    break
            except RateLimitError:
                wait_time = 60 * 5 # Wait 5 minutes
                print(f"⏳ Quota limit reached. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                print("🔄 Retrying...")
            except ValueError as ve:
                print(f"❌ Configuration Error: {ve}")
                return
            except Exception as e:
                print(f"❌ Unexpected Error: {e}")
                break

if __name__ == "__main__":
    main()
