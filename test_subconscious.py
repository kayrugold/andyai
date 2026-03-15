import os
import requests

# Pull the API key from the bash environment
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("Error: Could not find GEMINI_API_KEY. Did you run 'source ~/.bashrc'?")
    exit()

# The standard endpoint for Gemini 
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

# A simple test payload for the subconscious to send
payload = {
    "contents": [{
        "parts": [{"text": "Reply with exactly one sentence: 'The subconscious connection to Gemini is fully active.'"}]
    }]
}

print("Pinging Gemini API...")

try:
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    
    # Dig into the JSON response to grab the actual text
    result_text = response.json()['candidates'][0]['content']['parts'][0]['text']
    print(f"\nResponse received:\n{result_text}")
    
except requests.exceptions.RequestException as e:
    print(f"\nConnection failed: {e}")
