from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 1. This defines the "Inner Box" (the health numbers)
class HealthMetrics(BaseModel):
    steps: float
    distance: float
    energy: float

# 2. This defines the "Outer Box" (the whole packet)
class HealthData(BaseModel):
    region: str
    timestamp: str
    anon_id: str
    metrics: HealthMetrics  # This tells the server to look inside 'metrics'

@app.post("/ingest")
async def ingest_data(data: HealthData):
    # This will print the data in your Render logs so you can see it arrived
    print(f"Success! Received data for {data.anon_id} from {data.region}")
    print(f"Stats: {data.metrics.steps} steps, {data.metrics.distance}m distance")
    
    return {"status": "success", "message": f"Data recorded for {data.anon_id}"}

@app.get("/")
async def root():
    return {"status": "Online", "project": "Material Futures / Datamind"}
