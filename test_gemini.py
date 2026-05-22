import requests, os

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

def test():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{"parts": [{"text": "Say hello in Spanish in one sentence."}]}],
        "generationConfig": {"maxOutputTokens": 100}
    }
    r = requests.post(url, json=body, timeout=30)
    print("Status:", r.status_code)
    print("Response:", r.text[:2000])

test()
