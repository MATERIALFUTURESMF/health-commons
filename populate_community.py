import requests
import random
import time

# The address of your running FastAPI server
URL = "http://127.0.0.1:8000/ingest"

# A list of fake London neighborhoods
neighborhoods = ["Hackney", "Southwark", "Camden", "Brixton", "Islington"]

def generate_community(members=10):
    print(f"🚀 Injecting {members} community members into the Health Commons...")
    
    for i in range(members):
        data = {
            "anon_id": f"neighbor_{i}",
            "metric_type": "HRV",
            "value": random.uniform(40, 80), # Typical HRV range
            "region": random.choice(neighborhoods),
            "timestamp": int(time.time())
        }
        
        response = requests.post(URL, json=data)
        if response.status_code == 200:
            print(f"✅ Added member {i} from {data['region']}")
        else:
            print(f"❌ Failed to add member {i}")

if __name__ == "__main__":
    generate_community()
    
