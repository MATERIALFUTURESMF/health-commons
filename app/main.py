import os
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Any
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

def get_google_sheet():
    creds_json = os.environ.get("GOOGLE_CREDS")
    if not creds_json: return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("Health Commons Data").sheet1
    except Exception as e:
        return None

class HealthMetrics(BaseModel):
    steps: Any
    distance: Any
    asymmetry: Any 

class HealthData(BaseModel):
    region: Optional[str] = "Unknown"
    timestamp: Optional[str] = None
    anon_id: Optional[str] = "anonymous"
    metrics: HealthMetrics

@app.post("/ingest")
async def ingest_data(data: HealthData):
    try:
        sheet = get_google_sheet()
        if sheet:
            new_row = [str(data.timestamp), str(data.anon_id), str(data.region), str(data.metrics.steps), str(data.metrics.distance), str(data.metrics.asymmetry)]
            sheet.append_row(new_row)
            return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/stats")
async def get_stats():
    sheet = get_google_sheet()
    if not sheet: return {"error": "Connection failed"}
    return sheet.get_all_records()

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
                body { background: #000; color: #fff; font-family: 'Space Mono', monospace; margin: 0; padding: 0; display: flex; flex-direction: column; align-items: center; overflow-x: hidden; }
                h1 { font-size: 1.1rem; font-weight: 200; letter-spacing: 8px; margin: 30px 0; color: #00FF41; text-transform: uppercase; text-align: center;}
                
                .map-wrapper { 
                    width: 100vw; 
                    height: 65vh; 
                    background: #000; 
                    border-top: 1px solid #1a1a1a; 
                    border-bottom: 1px solid #1a1a1a; 
                    overflow: hidden; 
                    position: relative; 
                    margin-bottom: 20px; 
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                
                #map_div { 
                    width: 100%; 
                    height: 110%; 
                    transform: scale(1.5); /* Fixed wide-crop to fill desktop screens */
                } 

                /* Sharp, Minimalist Data Points */
                .exhibition-pin {
                    stroke: #fff !important;
                    stroke-width: 0.3px !important;
                    filter: drop-shadow(0 0 2px rgba(0, 255, 65, 0.5));
                }

                .map-label { position: absolute; top: 20px; left: 20px; font-size: 0.7rem; color: #555; text-transform: uppercase; z-index: 10; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; width: 95%; max-width: 1400px; margin-bottom: 40px;}
                .card { background: #050505; border: 1px solid #1a1a1a; padding: 20px; border-radius: 4px; display: flex; flex-direction: column; align-items: center;}
                canvas { width: 100% !important; height: 280px !important; }
                .label { font-size: 0.7rem; color: #555; margin-bottom: 15px; text-transform: uppercase; align-self: flex-start; }
                
                #map_div path { stroke: #222 !important; stroke-width: 0.2px !important; }
            </style>
        </head>
        <body>
            <h1>> COMMONS_EXHIBITION_MODE_V12</h1>
            
            <div class="map-wrapper">
                <div class="map-label">Global Geographic Distribution / 3px Precision</div>
                <div id="map_div"></div>
            </div>

            <div class="grid">
                <div class="card">
                    <div class="label">Max Distance (m) / Per User</div>
                    <canvas id="distChart"></canvas>
                </div>
                <div class="card">
                    <div class="label">Avg Walking Asymmetry (%) / Per Region</div>
                    <canvas id="asymChart"></canvas>
                </div>
            </div>

            <script>
                google.charts.load('current', {'packages':['geochart']});
                let charts = {};

                const geoDB = {
                    'london': [51.5072, -0.1276],
                    'hammersmith': [51.4928, -0.2253],
                    'bristol': [51.4545, -2.5879],
                    'paris': [48.8566, 2.3522],
                    'new york': [40.7128, -74.0060],
                    'tokyo': [35.6762, 139.6503],
                    'sydney': [-33.8688, 151.2093],
                    'cape town': [-33.9249, 18.4241],
                    'são paulo': [-23.5505, -46.6333],
                    'berlin': [52.5200, 13.4050]
                };

                async function updateAll() {
                    const response = await fetch('/api/stats');
                    const rawData = await response.json();
                    
                    const group = {};
                    rawData.forEach(row => {
                        let rawReg = row['REGION'] || 'Unknown';
                        let city = rawReg.split(',')[0].trim().toLowerCase();
                        
                        const key = `${row['USER NAME']}|${city}`;
                        if (!group[key]) group[key] = { steps: [], dist: [], asym: [], user: row['USER NAME'], city: city };
                        
                        group[key].steps.push(parseFloat(row['STEPS']) || 0);
                        group[key].dist.push(parseFloat(row['TOTAL DISTANCE (M)']) || 0);
                        group[key].asym.push(parseFloat(row['WALKING ASYMMETRY']) || 0); 
                    });

                    const processed = Object.values(group).map(d => ({
                        user: d.user, city: d.city,
                        avgSteps: d.steps.reduce((a,b)=>a+b,0)/d.steps.length,
                        avgDist: d.dist.reduce((a,b)=>a+b,0)/d.dist.length,
                        avgAsym: d.asym.reduce((a,b)=>a+b,0)/d.asym.length
                    }));

                    drawMap(processed);
                    drawScatters(processed);
                }

                function drawMap(data) {
                    const dataTable = new google.visualization.DataTable();
                    dataTable.addColumn('number', 'Latitude');
                    dataTable.addColumn('number', 'Longitude');
                    dataTable.addColumn('string', 'Location');
                    dataTable.addColumn('number', 'Avg Steps');

                    data.forEach(d => {
                        if (geoDB[d.city]) {
                            const [lat, lon] = geoDB[d.city];
                            dataTable.addRow([lat, lon, d.city, d.avgSteps]);
                        }
                    });

                    const options = {
                        region: 'world', 
                        displayMode: 'markers',
                        colorAxis: {colors: ['#004411', '#00FF41']}, // Gradient preserved
                        backgroundColor: '#000',
                        datalessRegionColor: '#0A0A0A', 
                        sizeAxis: { minValue: 0, maxValue: 100, minSize: 3, maxSize: 3 }, // Fixed 3px size
                        legend: 'none',
                        tooltip: { trigger: 'none' },
                        enableInteractivity: false
                    };

                    const chart = new google.visualization.GeoChart(document.getElementById('map_div'));
                    
                    google.visualization.events.addListener(chart, 'ready', function() {
                        const circles = document.getElementsByTagName('circle');
                        for(let i=0; i<circles.length; i++) {
                            circles[i].setAttribute('class', 'exhibition-pin');
                            circles[i].setAttribute('r', '1.5'); // Radius for 3px diameter
                        }
                    });

                    chart.draw(dataTable, options);
                }

                function drawScatters(data) {
                    const theme = '#00FF41';
                    if(charts.dist) charts.dist.destroy();
                    charts.dist = new Chart(document.getElementById('distChart'), {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Distance',
                                data: data.map(d => ({ x: d.user, y: d.avgDist })),
                                backgroundColor: theme, pointRadius: 6
                            }]
                        },
                        options: { scales: { x: { type: 'category', labels: [...new Set(data.map(d=>d.user))], grid: {display:false} }, y: {grid:{color:'#111'}} }, plugins:{legend:{display:false}} }
                    });

                    if(charts.asym) charts.asym.destroy();
                    charts.asym = new Chart(document.getElementById('asymChart'), {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Asymmetry',
                                data: data.map(d => ({ x: d.city, y: d.avgAsym })),
                                backgroundColor: '#00ffff', pointRadius: 6
                            }]
                        },
                        options: { scales: { x: { type: 'category', labels: [...new Set(data.map(d=>d.city))], grid: {display:false} }, y: {grid:{color:'#111'}} }, plugins:{legend:{display:false}} }
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
