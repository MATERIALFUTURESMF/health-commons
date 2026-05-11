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

# --- 3. Ingest Route ---
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

# --- 4. API Route ---
@app.get("/api/stats")
async def get_stats():
    sheet = get_google_sheet()
    if not sheet: return {"error": "Connection failed"}
    return sheet.get_all_records()

# --- 5. Multi-Chart Exhibition Dashboard ---
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    html_content = """
    <html>
        <head>
            <title>Commons Multi-Node Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <link href="https://fonts.googleapis.com/css2?family=Space+Mono&display=swap" rel="stylesheet">
            <style>
                body { background: #000; color: #fff; font-family: 'Space Mono', monospace; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
                h1 { font-size: 1.2rem; font-weight: 200; letter-spacing: 8px; margin: 40px 0; color: #00FF41; text-transform: uppercase; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; width: 95%; max-width: 1400px; }
                .card { background: #050505; border: 1px solid #1a1a1a; padding: 20px; border-radius: 4px; }
                .full-width { grid-column: span 2; }
                canvas { width: 100% !important; max-height: 400px; }
                .label { font-size: 0.7rem; color: #444; margin-bottom: 10px; text-transform: uppercase; }
            </style>
        </head>
        <body>
            <h1>> COMMONS_MULTI_NODE_VISUALISATION</h1>
            
            <div class="grid">
                <div class="card full-width">
                    <div class="label">Average Daily Steps / Unique User</div>
                    <canvas id="barChart"></canvas>
                </div>

                <div class="card">
                    <div class="label">Average Distance / Region / User</div>
                    <canvas id="distanceScatter"></canvas>
                </div>

                <div class="card">
                    <div class="label">Average Active Energy / Region / User</div>
                    <canvas id="energyScatter"></canvas>
                </div>
            </div>

            <script>
                let charts = {};

                async function fetchData() {
                    const response = await fetch('/api/stats');
                    const rawData = await response.json();
                    
                    // --- DATA PROCESSING (Averaging logic) ---
                    const userStats = {}; 

                    rawData.forEach(row => {
                        const user = row['USER NAME'] || 'ANON';
                        const region = row['REGION'] || 'Unknown';
                        const key = `${user}|${region}`;

                        if (!userStats[key]) {
                            userStats[key] = { steps: [], distance: [], energy: [], user, region };
                        }
                        userStats[key].steps.push(parseFloat(row['STEPS']) || 0);
                        userStats[key].distance.push(parseFloat(row['TOTAL DISTANCE (M)']) || 0);
                        userStats[key].energy.push(parseFloat(row['ACTIVE ENERGY']) || 0);
                    });

                    const processed = Object.values(userStats).map(d => ({
                        user: d.user,
                        region: d.region,
                        avgSteps: d.steps.reduce((a,b) => a+b, 0) / d.steps.length,
                        avgDist: d.distance.reduce((a,b) => a+b, 0) / d.distance.length,
                        avgEnergy: d.energy.reduce((a,b) => a+b, 0) / d.energy.length
                    }));

                    updateVisuals(processed);
                }

                function updateVisuals(data) {
                    const ctxBar = document.getElementById('barChart').getContext('2d');
                    const ctxDist = document.getElementById('distanceScatter').getContext('2d');
                    const ctxEng = document.getElementById('energyScatter').getContext('2d');

                    // Standard aesthetics
                    const themeColor = '#00FF41';
                    const scatterStyle = { pointBackgroundColor: themeColor, pointRadius: 6, borderColor: '#1a1a1a' };

                    // 1. BAR CHART (Averaged)
                    if(charts.bar) charts.bar.destroy();
                    charts.bar = new Chart(ctxBar, {
                        type: 'bar',
                        data: {
                            labels: data.map(d => d.user),
                            datasets: [{
                                label: 'Avg Steps',
                                data: data.map(d => d.avgSteps),
                                backgroundColor: 'rgba(0, 255, 65, 0.2)',
                                borderColor: themeColor,
                                borderWidth: 1
                            }]
                        },
                        options: { scales: { y: { beginAtZero: true, grid: {color: '#111'} } } }
                    });

                    // 2. DISTANCE SCATTER
                    if(charts.dist) charts.dist.destroy();
                    charts.dist = new Chart(ctxDist, {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Distance (m)',
                                data: data.map(d => ({ x: d.user, y: d.avgDist })),
                                ...scatterStyle
                            }]
                        },
                        options: { 
                            scales: { 
                                x: { type: 'category', labels: data.map(d => d.user), grid: {display: false} },
                                y: { grid: {color: '#111'} }
                            }
                        }
                    });

                    // 3. ENERGY SCATTER
                    if(charts.eng) charts.eng.destroy();
                    charts.eng = new Chart(ctxEng, {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Energy (kcal)',
                                data: data.map(d => ({ x: d.region, y: d.avgEnergy })),
                                ...scatterStyle,
                                pointBackgroundColor: '#00ffff'
                            }]
                        },
                        options: { 
                            scales: { 
                                x: { type: 'category', labels: [...new Set(data.map(d => d.region))], grid: {display: false} },
                                y: { grid: {color: '#111'} }
                            }
                        }
                    });
                }

                fetchData();
                setInterval(fetchData, 30000);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/")
async def root():
    return {"status": "Online", "project": "Material Futures"}
