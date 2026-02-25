from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TrainingPayload(BaseModel):
    """Payload unico dal nuovo simulatore Python"""
    device_id: str
    vibration_x: float
    vibration_y: float
    vibration_z: float
    vibration_rms: float
    temperature: float
    current: float
    pressure: float
    rpm: int
    health_percent: float
    ground_truth: str  # es: "HEALTHY", "WARNING", "FAULTY", "BROKEN"
    timestamp_received: datetime = Field(default_factory=datetime.utcnow)

    # Questo campo serve per mantenere compatibilità con il DataManager 
    # che cercherà measurement_id per i log, ma nel simulatore nuovo non c'è.
    # Lo rendiamo opzionale o lo generiamo.
    measurement_id: Optional[int] = 0