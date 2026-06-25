import urllib.request
import json

API_KEY = "sk-or-...1759"
url = "https://openrouter.ai/api/v1/chat/completions"
data = json.dumps({
    "model": "openrouter/owl-alpha",
    "messages": [{"role": "user", "content": "oi"}]
}).encode()

req = urllib.request.Request(url, data=data, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "https://koldi.local",
    "X-Title": "Koldi"
})

try:
    resp = urllib.request.urlopen(req, timeout=30)
    print(f"Status: {resp.status}")
    body = resp.read().decode()
    print(body[:500])
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode()[:500])
except Exception as e:
    print(f"Error: {e}")
