import os
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Any
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# --- 1. Setup Google Sheets Connection ---
def get_google_sheet():
    creds_json = os.environ.get("GOOGLE_CREDS")
    if not creds_json:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("Health Commons Data").sheet1
    except Exception as e:
        print(f"Connection Error: {e}")
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

# --- 3. The Ingest Route ---
@app.post("/ingest")
async def ingest_data(data: HealthData):
    try:
        sheet = get_google_sheet()
        if sheet:
            new_row = [str(data.timestamp), str(data.anon_id), str(data.region), str(data.metrics.steps), str(data.metrics.distance), str(data.metrics.energy)]
            sheet.append_row(new_row)
            return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 4. The Data API ---
@app.get("/api/stats")
async def get_stats():
    sheet = get_google_sheet()
    if not sheet: return {"error": "Connection failed"}
    return sheet.get_all_records()

# --- 5. The Exhibition Dashboard (Formatted) ---
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    html_content = """
    <html>
        <head>
            <title>Commons Sync Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <link href="https://fonts.googleapis.com/css2?family=Space+Mono&display=swap" rel="stylesheet">
            <style>
                body { 
                    background: #000; 
                    color: #fff; 
                    font-family: 'Space Mono', monospace; 
                    margin: 0; padding: 40px; 
                    display: flex; flex-direction: column; align-items: center; 
                }
                .container { 
                    width: 95%; max-width: 1200px; 
                    background: #050505; 
                    padding: 30px; 
                    border: 1px solid #1a1a1a; 
                    border-radius: 4px; 
                }
                h1 { 
                    font-size: 1.2rem; font-weight: 200; letter-spacing: 8px; 
                    margin-bottom: 40px; color: #00FF41; /* Matrix Green */
                }
                canvas { max-height: 600px; }
            </style>
        </head>
        <body>
            <h1>> COMMONS_SYNC_DATA_STREAM</h1>
            <div class="container">
                <canvas id="commonsChart"></canvas>
            </div>

            <script>
                let myChart;

                async function updateChart() {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    const labels = data.map(row => row['USER NAME'] || 'ANON');
                    const steps = data.map(row => row['STEPS']);

                    const ctx = document.getElementById('commonsChart').getContext('2d');
                    
                    // Create a gradient for the bars
                    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                    gradient.addColorStop(0, '#00FF41');
                    gradient.addColorStop(1, 'rgba(0, 255, 65, 0)');

                    if (myChart) { myChart.destroy(); }

                    myChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Steps',
                                data: steps,
                                backgroundColor: gradient,
                                borderColor: '#00FF41',
                                borderWidth: 1,
                                borderRadius: 2,
                            }]
                        },
                        options: {
                            animation: { duration: 2000, easing: 'easeOutQuart' },
                            scales: {
                                y: { 
                                    beginAtZero: true, 
                                    grid: { color: '#111' }, 
                                    ticks: { color: '#444', font: { family: 'Space Mono' } } 
                                },
                                x: { 
                                    grid: { display: false }, 
                                    ticks: { color: '#00FF41', font: { family: 'Space Mono' } } 
                                }
                            },
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    backgroundColor: '#000',
                                    titleColor: '#00FF41',
                                    bodyColor: '#fff',
                                    borderColor: '#00FF41',
                                    borderWidth: 1,
                                    displayColors: false
                                }
                            }
                        }
                    });
                }
                
                updateChart();
                setInterval(updateChart, 20000); // Syncs every 20 seconds
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/")
async def root():
    return {"status": "Online", "project": "Material Futures"}
