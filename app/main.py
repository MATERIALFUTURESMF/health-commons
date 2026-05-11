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
    energy: Any

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
            new_row = [str(data.timestamp), str(data.anon_id), str(data.region), str(data.metrics.steps), str(data.metrics.distance), str(data.metrics.energy)]
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
                body { background: #000; color: #fff; font-family: 'Space Mono', monospace; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
                h1 { font-size: 1.1rem; font-weight: 200; letter-spacing: 8px; margin: 30px 0; color: #00FF41; text-transform: uppercase; text-align: center;}
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; width: 95%; max-width: 1400px; }
                .card { background: #050505; border: 1px solid #1a1a1a; padding: 20px; border-radius: 4px; display: flex; flex-direction: column; align-items: center;}
                .full-width { grid-column: span 2; }
                canvas, #map_div { width: 100% !important; height: 450px; }
                .label { font-size: 0.7rem; color: #555; margin-bottom: 15px; text-transform: uppercase; align-self: flex-start; }
            </style>
        </head>
        <body>
            <h1>> COMMONS_EXHIBITION_MODE_V5</h1>
            
            <div class="grid">
                <div class="card full-width">
                    <div class="label">Geographic Distribution / Avg Steps by Region</div>
                    <div id="map_div"></div>
                </div>
                <div class="card">
                    <div class="label">Avg Distance (m) / Per User</div>
                    <canvas id="distChart"></canvas>
                </div>
                <div class="card">
                    <div class="label">Avg Active Energy / Per Region</div>
                    <canvas id="energyChart"></canvas>
                </div>
            </div>

            <script>
                google.charts.load('current', {'packages':['geochart']});
                let charts = {};

                async function updateAll() {
                    const response = await fetch('/api/stats');
                    const rawData = await response.json();
                    
                    const group = {};
                    rawData.forEach(row => {
                        // --- DATA SANITIZATION ENGINE ---
                        let rawReg = row['REGION'] || 'Unknown';
                        let parts = rawReg.split(',');
                        
                        // 1. Clean the city name (capitalize first letter, lowercase rest)
                        let city = parts[0].trim();
                        if(city.length > 0) {
                            city = city.charAt(0).toUpperCase() + city.slice(1).toLowerCase();
                        }
                        
                        // 2. Clean the country code
                        let country = parts.length > 1 ? parts[1].trim().toUpperCase() : '';
                        if (country === 'UK' || country === 'U.K.') country = 'GB';
                        if (country === 'USA') country = 'US';
                        
                        // 3. Rebuild a perfect string for the scatter charts (e.g., "Hammersmith, GB")
                        let cleanRegion = country ? `${city}, ${country}` : city;
                        
                        const key = `${row['USER NAME']}|${cleanRegion}`;
                        if (!group[key]) group[key] = { steps: [], dist: [], energy: [], user: row['USER NAME'], region: cleanRegion, city: city, country: country };
                        group[key].steps.push(parseFloat(row['STEPS']) || 0);
                        group[key].dist.push(parseFloat(row['TOTAL DISTANCE (M)']) || 0);
                        group[key].energy.push(parseFloat(row['ACTIVE ENERGY']) || 0);
                    });

                    const processed = Object.values(group).map(d => ({
                        user: d.user, region: d.region, city: d.city, country: d.country,
                        avgSteps: d.steps.reduce((a,b)=>a+b,0)/d.steps.length,
                        avgDist: d.dist.reduce((a,b)=>a+b,0)/d.dist.length,
                        avgEnergy: d.energy.reduce((a,b)=>a+b,0)/d.energy.length
                    }));

                    drawMap(processed);
                    drawScatters(processed);
                }

                function drawMap(data) {
                    const discoveredCountries = new Set();
                    let containsUnformattedData = false;

                    data.forEach(d => {
                        if (d.country) {
                            discoveredCountries.add(d.country);
                        } else {
                            containsUnformattedData = true;
                        }
                    });

                    // Auto-Zoom Clause
                    let autoRegion = 'world'; 
                    if (discoveredCountries.size === 1 && !containsUnformattedData) {
                        autoRegion = Array.from(discoveredCountries)[0]; 
                    }

                    // Map Rendering
                    const regionData = [['Location', 'Avg Steps']];
                    const mapGroups = {};
                    
                    data.forEach(d => {
                        // If zoomed into a specific country, only hand the Map the City name!
                        let mapLoc = (autoRegion !== 'world' && d.city) ? d.city : d.region;
                        
                        if(!mapGroups[mapLoc]) mapGroups[mapLoc] = [];
                        mapGroups[mapLoc].push(d.avgSteps);
                    });

                    Object.keys(mapGroups).forEach(loc => {
                        const avg = mapGroups[loc].reduce((a,b)=>a+b,0)/mapGroups[loc].length;
                        regionData.push([loc, avg]);
                    });

                    const dataTable = google.visualization.arrayToDataTable(regionData);
                    const options = {
                        region: autoRegion,
                        displayMode: 'markers',
                        colorAxis: {colors: ['#004411', '#00FF41']},
                        backgroundColor: '#050505',
                        datalessRegionColor: '#2a2a2a', 
                        sizeAxis: { minValue: 0, maxValue: 50, minSize: 8, maxSize: 25 }
                    };
                    const chart = new google.visualization.GeoChart(document.getElementById('map_div'));
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
                                backgroundColor: theme, pointRadius: 10
                            }]
                        },
                        options: { scales: { x: { type: 'category', labels: [...new Set(data.map(d=>d.user))], grid: {display:false} }, y: {grid:{color:'#111'}} }, plugins:{legend:{display:false}} }
                    });

                    if(charts.energy) charts.energy.destroy();
                    charts.energy = new Chart(document.getElementById('energyChart'), {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Energy',
                                data: data.map(d => ({ x: d.region, y: d.avgEnergy })),
                                backgroundColor: '#00ffff', pointRadius: 10
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