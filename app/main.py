from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any

app = FastAPI()

class HealthMetrics(BaseModel):
    # We use 'Any' here so the server doesn't care if it's 26 or "26"
    steps: Any
    distance: Any
    energy: Any

class HealthData(BaseModel):
    region: Optional[str] = "Unknown"
    timestamp: Optional[str] = None
    anon_id: Optional[str] = "anonymous"
    metrics: HealthMetrics

@app.post("/ingest")
async def ingest_data(data: HealthData):
    print(f"--- DATA RECEIVED ---")
    print(f"User: {data.anon_id}")
    print(f"Metrics: {data.metrics}")
    return {"status": "success", "received_id": data.anon_id}

@app.get("/")
async def root():
    return {"status": "Online", "project": "Material Futures"}

import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# 1. Setup Google Sheets Connection
def get_google_sheet():
    # This looks for the 'GOOGLE_CREDS' variable you will set in Render
    creds_json = os.environ.get("GOOGLE_CREDS")
    if not creds_json:
        print("ERROR: GOOGLE_CREDS environment variable not set!")
        return None
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Replace with the EXACT name of your Google Sheet
    return client.open("Health Commons Data").sheet1

# 2. Data Models (Matching your fixed Shortcut)
class HealthMetrics(BaseModel):
    steps: float
    distance: float
    energy: float

class HealthData(BaseModel):
    region: str
    timestamp: str
    anon_id: str
    metrics: HealthMetrics

@app.post("/ingest")
async def ingest_data(data: HealthData):
    try:
        sheet = get_google_sheet()
        if sheet:
            # Prepare the row for the Commons
            new_row = [
                data.timestamp,
                data.anon_id,
                data.region,
                data.metrics.steps,
                data.metrics.distance,
                data.metrics.energy
            ]
            sheet.append_row(new_row)
            print(f"Successfully added data for {data.anon_id}")
            return {"status": "success", "message": "Contribution added to the Commons"}
    except Exception as e:
        print(f"Error adding to sheet: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Online", "project": "Material Futures / Datamind"}
