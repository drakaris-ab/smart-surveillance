import requests
import json
import datetime

url = "http://localhost:8000/alert-mute"
headers = {"Content-Type": "application/json"}
data = {
    "start_time": "2026-09-01T21:32:00",
    "end_time": "2026-09-01T22:32:00",
    "days": "Mon,Tue,Wed",
    "is_active": True
}

auth_url = "http://localhost:8000/auth/login"
r = requests.post(auth_url, json={"username": "admin", "password": "pass#"})
print("Auth:", r.status_code)

if r.status_code == 200:
    token = r.json().get("access_token")
    headers["Authorization"] = f"Bearer {token}"
    
    # Let's post one
    r = requests.post(url, json=data, headers=headers)
    print("Post mute:", r.status_code, r.text)
    
    # Get ID
    mute_id = r.json().get("id")
    print(f"Got id {mute_id}")
    
    # Delete it
    r = requests.delete(f"{url}/{mute_id}", headers=headers)
    print("Delete mute:", r.status_code, r.text)
