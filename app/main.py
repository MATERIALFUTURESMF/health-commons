import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# --- 1. Setup Google Sheets Connection ---
def get_google_sheet():
    creds_json = os.environ.get("GOOGLE_CREDS")
    
    if not creds_json:
        print("ERROR: GOOGLE_CREDS environment variable not found on Render!")
        return None
    
    try:
        # These are the specific 'Keys' to the kingdom Google was asking for
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Open the sheet by name. 
        sheet_name = "Health Commons Data"
        return client.open(sheet_name).sheet1
    except Exception as e:
        print(f"CRITICAL GOOGLE ERROR: {e}")
        return None

# --- 2. Data Models ---
class HealthMetrics(BaseModel):
    steps: Any
    distance: Any
    energy: Any

class HealthData(BaseModel):
    region: Optional[str] = "Unknown"
    timestamp: Optional[str] = None
    anon_id: Optional[str] = "anonymous"
    metrics: HealthMetrics

# --- 3. The Data Ingest Route ---
@app.post("/ingest")
async def ingest_data(data: HealthData):
    print(f"--- ATTEMPTING SHEET SYNC: {data.anon_id} ---")
    
    try:
        sheet = get_google_sheet()
        if sheet:
            new_row = [
                str(data.timestamp),
                str(data.anon_id),
                str(data.region),
                str(data.metrics.steps),
                str(data.metrics.distance),
                str(data.metrics.energy)
            ]
            
            sheet.append_row(new_row)
            print(f"SUCCESS: Row added for {data.anon_id}")
            return {"status": "success", "message": "Synced to Commons"}
        else:
            print("FAILURE: Could not connect to the specific Sheet.")
            return {"status": "error", "message": "Sheet connection failed. Check logs."}
            
    except Exception as e:
        print(f"DETAILED UPLOAD ERROR: {e}")
        return {"status": "error", "message": str(e)}

# --- 4. Landing Page ---
@app.get("/")
async def root():
    return {"status": "Online", "project": "Material Futures"}