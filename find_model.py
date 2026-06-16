import google.generativeai as genai

# Your working key
GOOGLE_API_KEY = "AIzaSyAvZx9phNmXdCSyOkdnIjydLIdHvHHxQtA"
genai.configure(api_key=GOOGLE_API_KEY)

print("\n------ CONTACTING GOOGLE SERVERS ------")
try:
    model_list = []
    # Ask Google to list every model this key can access
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"FOUND AVAILABLE MODEL: {m.name}")
            model_list.append(m.name)
    
    if not model_list:
        print("❌ ERROR: Connection successful, but NO chat models were found.")
        print("This usually means the API is blocked in your region (try a VPN to USA).")
    else:
        print("\n✅ GREAT! We found working models.")
        print(f"Please copy this EXACT text: {model_list[0]}")
        
except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")