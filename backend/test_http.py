import requests
import json

data = {
    "title": "Mandatory Voting",
    "description": "Vote or pay fine",
    "goals": "100% turnout"
}

try:
    res = requests.post("http://localhost:8000/api/v1/conversation/start", json={"user_id": "test", "resume": True})
    print("STATUS", res.status_code)
    print("TEXT", res.text)
except Exception as e:
    print("ERROR", e)
