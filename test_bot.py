import requests
import time

url = "http://127.0.0.1:8000/api/chat"

messages = [
    {"role": "assistant", "content": "Hello! Welcome to Qterra Property Management. Are you looking to rent a property (Tenant), or are you a property owner looking for a tenant?"},
    {"role": "user", "content": "I am a tenant looking for a basement in Mississauga."},
    {"role": "assistant", "content": "Great! I can help you with that. Can I get your phone number so we can reach out if needed?"},
    {"role": "user", "content": "Sure, it is 555-123-4567"}
]

print("Testing Tenant Flow...")
try:
    response = requests.post(url, json={"messages": messages}, timeout=20)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())
except Exception as e:
    print("Error:", e)
