import google.generativeai as genai

# --- PASTE YOUR API KEY BELOW ---
GOOGLE_API_KEY = "PASTE_YOUR_GEMINI_KEY_HERE" 
# --------------------------------

genai.configure(api_key=GOOGLE_API_KEY)

print("--- Contacting Google to see available brains ---")
try:
    found_any = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"AVAILABLE MODEL: {m.name}")
            found_any = True
    
    if not found_any:
        print("No chat models found. Your key might be inactive.")
        
except Exception as e:
    print(f"CRITICAL ERROR: {e}")