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

# --- 5. Exhibition Dashboard (Interactive Map + Scatters) ---
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    html_content = """
    <html>
        <head>
            <title>Commons Multi-Node Visualisation</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
            <link href="https://fonts.googleapis.com/css2?family=Space+Mono&display=swap" rel="stylesheet">
            <style>
                body { background: #000; color: #fff; font-family: 'Space Mono', monospace; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
                h1 { font-size: 1.1rem; font-weight: 200; letter-spacing: 8px; margin: 30px 0; color: #00FF41; text-transform: uppercase; text-align: center;}
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; width: 95%; max-width: 1400px; }
                .card { background: #050505; border: 1px solid #1a1a1a; padding: 20px; border-radius: 4px; display: flex; flex-direction: column; align-items: center;}
                .full-width { grid-column: span 2; }
                canvas, #map_div { width: 100% !important; height: 400px; }
                .label { font-size: 0.7rem; color: #555; margin-bottom: 15px; text-transform: uppercase; align-self: flex-start; }
            </style>
        </head>
        <body>
            <h1>> COMMONS_EXHIBITION_MODE_v2</h1>
            
            <div class="grid">
                <div class="card full-width">
                    <div class="label">Geographic Distribution / Average Steps</div>
                    <div id="map_div"></div>
                </div>

                <div class="card">
                    <div class="label">Avg Distance (m) / User</div>
                    <canvas id="distChart"></canvas>
                </div>

                <div class="card">
                    <div class="label">Avg Active Energy / Region</div>
                    <canvas id="energyChart"></canvas>
                </div>
            </div>

            <script>
                google.charts.load('current', {'packages':['geochart']});
                let charts = {};

                async function updateAll() {
                    const response = await fetch('/api/stats');
                    const rawData = await response.json();
                    
                    // --- DATA PROCESSING (Averaging logic) ---
                    const group = {};
                    rawData.forEach(row => {
                        const key = `${row['USER NAME']}|${row['REGION']}`;
                        if (!group[key]) group[key] = { steps: [], dist: [], energy: [], user: row['USER NAME'], region: row['REGION'] };
                        group[key].steps.push(parseFloat(row['STEPS']) || 0);
                        group[key].dist.push(parseFloat(row['TOTAL DISTANCE (M)']) || 0);
                        group[key].energy.push(parseFloat(row['ACTIVE ENERGY']) || 0);
                    });

                    const processed = Object.values(group).map(d => ({
                        user: d.user, region: d.region,
                        avgSteps: d.steps.reduce((a,b)=>a+b,0)/d.steps.length,
                        avgDist: d.dist.reduce((a,b)=>a+b,0)/d.dist.length,
                        avgEnergy: d.energy.reduce((a,b)=>a+b,0)/d.energy.length
                    }));

                    drawMap(processed);
                    drawScatters(processed);
                }

                function drawMap(data) {
                    // Grouping by region for the map
                    const regionData = [['Region', 'Avg Steps']];
                    const regions = {};
                    data.forEach(d => {
                        if(!regions[d.region]) regions[d.region] = [];
                        regions[d.region].push(d.avgSteps);
                    });
                    Object.keys(regions).forEach(r => {
                        const avg = regions[r].reduce((a,b)=>a+b,0)/regions[r].length;
                        regionData.push([r, avg]);
                    });

                    const dataTable = google.visualization.arrayToDataTable(regionData);
                    const options = {
                        region: 'GB', // United Kingdom
                        displayMode: 'markers', // Using dots for cities
                        colorAxis: {colors: ['#003311', '#00FF41']},
                        backgroundColor: '#050505',
                        datalessRegionColor: '#0a0a0a',
                        keepAspectRatio: true
                    };
                    const chart = new google.visualization.GeoChart(document.getElementById('map_div'));
                    chart.draw(dataTable, options);
                }

                function drawScatters(data) {
                    const theme = '#00FF41';
                    
                    // Distance Chart
                    if(charts.dist) charts.dist.destroy();
                    charts.dist = new Chart(document.getElementById('distChart'), {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Distance',
                                data: data.map(d => ({ x: d.user, y: d.avgDist })),
                                backgroundColor: theme, pointRadius: 8
                            }]
                        },
                        options: { scales: { x: { type: 'category', labels: [...new Set(data.map(d=>d.user))], grid: {display:false} }, y: {grid:{color:'#111'}} }, plugins:{legend:{display:false}} }
                    });

                    // Energy Chart
                    if(charts.energy) charts.energy.destroy();
                    charts.energy = new Chart(document.getElementById('energyChart'), {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Energy',
                                data: data.map(d => ({ x: d.region, y: d.avgEnergy })),
                                backgroundColor: '#00ffff', pointRadius: 8
                            }]
                        },
                        options: { scales: { x: { type: 'category', labels: [...new Set(data.map(d=>d.region))], grid: {display:false} }, y: {grid:{color:'#111'}} }, plugins:{legend:{display:false}} }
                    });
                }

                google.charts.setOnLoadCallback(updateAll);
                setInterval(updateAll, 30000);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/")
async def root():
    return {"status": "Online", "project": "Material Futures"}
