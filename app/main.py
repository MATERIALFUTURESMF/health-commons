import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any
import gspread
from google.oauth2.service_account import Credentials

# Initialize the FastAPI app
app = FastAPI()

# --- 1. Setup Google Sheets Connection ---
def get_google_sheet():
    # This looks for the 'GOOGLE_CREDS' variable you set in the Render Dashboard
    creds_json = os.environ.get("GOOGLE_CREDS")
    
    if not creds_json:
        print("ERROR: GOOGLE_CREDS environment variable not found on Render!")
        return None
    
    try:
        # Define the permissions needed (Sheets and Drive)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Load the JSON credentials from the environment variable
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # IMPORTANT: Ensure your Google Sheet is named exactly "Health Commons Data"
        # and shared with the client_email found in your JSON key.
        return client.open("Health Commons Data").sheet1
    except Exception as e:
        print(f"FAILED TO CONNECT TO GOOGLE SHEETS: {e}")
        return None

# --- 2. Data Models (Matching your iPhone Shortcut structure) ---
class HealthMetrics(BaseModel):
    # Using 'Any' prevents 422 errors if numbers arrive as strings
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
    print(f"--- INCOMING SYNC: {data.anon_id} ---")
    
    try:
        sheet = get_google_sheet()
        if sheet:
            # Prepare the row data
            new_row = [
                str(data.timestamp),
                str(data.anon_id),
                str(data.region),
                str(data.metrics.steps),
                str(data.metrics.distance),
                str(data.metrics.energy)
            ]
            
            # Add the row to the bottom of the spreadsheet
            sheet.append_row(new_row)
            print(f"SUCCESS: Recorded data for {data.anon_id} from {data.region}")
            return {"status": "success", "message": "Data synced to the Commons"}
        else:
            return {"status": "error", "message": "Server could not connect to Google Sheets"}
            
    except Exception as e:
        print(f"ERROR DURING SHEET UPDATE: {e}")
        return {"status": "error", "message": str(e)}

# --- 4. The Root Landing Page ---
@app.get("/")
async def root():
    return {
        "status": "Online", 
        "project": "Material Futures / Datamind",
        "node": "London"
    }
