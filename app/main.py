# ... (Keep all your imports and FastAPI setup the same)

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
                    height: 60vh; 
                    background: #000; 
                    border-top: 1px solid #1a1a1a; 
                    border-bottom: 1px solid #1a1a1a; 
                    overflow: hidden; 
                    position: relative; 
                    margin-bottom: 20px; 
                }
                
                #map_div { 
                    width: 100%; 
                    height: 100%; 
                    transition: transform 2s ease-in-out; 
                    transform-origin: center center;
                } 

                /* Force the markers to look sharper via CSS if the API struggles */
                #map_div circle { 
                    stroke-width: 0.5px !important; 
                    stroke: rgba(255,255,255,0.2) !important;
                }

                .map-label { position: absolute; top: 20px; left: 20px; font-size: 0.7rem; color: #555; text-transform: uppercase; z-index: 10; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; width: 95%; max-width: 1400px; margin-bottom: 40px;}
                .card { background: #050505; border: 1px solid #1a1a1a; padding: 20px; border-radius: 4px; display: flex; flex-direction: column; align-items: center;}
                canvas { width: 100% !important; height: 300px !important; }
                .label { font-size: 0.7rem; color: #555; margin-bottom: 15px; text-transform: uppercase; align-self: flex-start; }
                
                #map_div path { stroke: #222 !important; stroke-width: 0.2px !important; }
            </style>
        </head>
        <body>
            <h1>> COMMONS_EXHIBITION_MODE_V11.2</h1>
            
            <div class="map-wrapper">
                <div class="map-label">Geographic Context / Precision Zoom</div>
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

                    let lats = [], lons = [];
                    const mapGroups = {};
                    
                    data.forEach(d => {
                        if (geoDB[d.city]) {
                            const [lat, lon] = geoDB[d.city];
                            lats.push(lat);
                            lons.push(lon);
                            if(!mapGroups[d.city]) mapGroups[d.city] = [];
                            mapGroups[d.city].push(d.avgSteps);
                        }
                    });

                    Object.keys(mapGroups).forEach(city => {
                        const avg = mapGroups[city].reduce((a,b)=>a+b,0)/mapGroups[city].length;
                        const coords = geoDB[city.toLowerCase()];
                        dataTable.addRow([coords[0], coords[1], city, avg]);
                    });

                    // --- ENHANCED AUTO-ZOOM BRAIN ---
                    if (lats.length > 0) {
                        const minLat = Math.min(...lats), maxLat = Math.max(...lats);
                        const minLon = Math.min(...lons), maxLon = Math.max(...lons);
                        const latSpan = maxLat - minLat, lonSpan = maxLon - minLon;
                        const maxSpan = Math.max(latSpan, lonSpan);

                        // If it's just London/One city, zoom aggressively (8x instead of 4x)
                        let zoomScale = 1.2; 
                        if (maxSpan < 0.5) zoomScale = 8.5;     // Ultra-local (Street/City level)
                        else if (maxSpan < 2) zoomScale = 6.0;   // Metro area
                        else if (maxSpan < 10) zoomScale = 3.5;  // National
                        else if (maxSpan < 40) zoomScale = 1.8;  // Continental

                        const centerLat = (minLat + maxLat) / 2;
                        const centerLon = (minLon + maxLon) / 2;

                        // Adjusted transform math to center precisely on the cluster
                        const xOffset = centerLon * -1.8; 
                        const yOffset = centerLat * 2.2;

                        document.getElementById('map_div').style.transform = `scale(${zoomScale}) translate(${xOffset}px, ${yOffset}px)`;
                    }

                    const options = {
                        region: 'world', 
                        displayMode: 'markers',
                        colorAxis: {colors: ['#004411', '#00FF41']},
                        backgroundColor: '#000',
                        datalessRegionColor: '#080808', 
                        // Lock markers to a strictly small visual size
                        sizeAxis: { minValue: 0, maxValue: 100, minSize: 2, maxSize: 2 },
                        legend: 'none',
                        tooltip: { trigger: 'none' } // Cleaner for exhibition
                    };
                    const chart = new google.visualization.GeoChart(document.getElementById('map_div'));
                    chart.draw(dataTable, options);
                }

                function drawScatters(data) {
                    // ... (Keep scatter code as is)
                }

                google.charts.setOnLoadCallback(updateAll);
                setInterval(updateAll, 30000);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)
