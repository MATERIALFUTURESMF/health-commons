from fastapi import FastAPI
from .models import HealthPacket
from .ledger import global_ledger
from .representation import get_avatar_state
from .security import cloak_identity

# 1. Initialize the FastAPI Engine
app = FastAPI(title="Global Health Commons")

@app.get("/")
def home():
    """The landing page for the Local Node."""
    return {
        "status": "Online",
        "node_location": "London",
        "project": "Material Futures / Datamind"
    }

@app.post("/ingest")
async def ingest_health_data(packet: HealthPacket):
    # Step 1: Cloak the identity
    packet.anon_id = cloak_identity(packet.anon_id)
    return {"status": "success", "message": "Data received"}
    
    # Step 2: Save to Ledger
    new_block_hash = global_ledger.add_entry(packet.model_dump())
    
    # Step 3: Multi-Metric Analysis
    results = {}
    for metric_name, value in packet.metrics.items():
        world_avg = global_ledger.get_average(metric_name)
        avatar_trait = get_avatar_state(value, world_avg)
        
        results[metric_name] = {
            "global_average": round(world_avg, 2),
            "resonance": round(value / world_avg, 2) if world_avg > 0 else 1.0,
            "trait": avatar_trait
        }

    return {
        "status": "success",
        "identity_shadow": f"{packet.anon_id[:8]}...",
        "block_hash": new_block_hash,
        "community_comparison": results
    }