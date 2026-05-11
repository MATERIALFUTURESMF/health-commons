from pydantic import BaseModel
from typing import Dict, Any, Optional

class HealthPacket(BaseModel):
    anon_id: str
    region: str
    timestamp: str
    # metrics will look like {"steps": 5000, "hrv": 65}
    metrics: Dict[str, float]