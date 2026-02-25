# api/routes/pumps.py
from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional

router = APIRouter()

@router.get("/status")
async def get_pumps_status(request: Request, state: Optional[str] = Query(None)):
    core_manager = request.app.state.core_manager
    
    if state:
        # Se viene passato ?state=FAULTY
        data = core_manager.get_pumps_by_state(state)
    else:
        # Comportamento standard
        data = core_manager.get_all_pumps_status()
        
    return {"count": len(data), "pumps": data}

@router.get("/status/{device_id}")
async def get_pump_detail(device_id: str, request: Request):
    core_manager = request.app.state.core_manager
    pump = core_manager.get_pump_details(device_id)
    
    if not pump:
        raise HTTPException(status_code=404, detail=f"Pump {device_id} not found")
    return pump

@router.get("/alerts")
async def get_critical_pumps(request: Request):
    """Ritorna solo pompe in stato critico"""
    core_manager = request.app.state.core_manager
    all_pumps = core_manager.get_all_pumps_status()
    critical = [p for p in all_pumps if p.get("state") in ["WARNING", "FAULTY"]]
    return {"critical_count": len(critical), "alerts": critical}