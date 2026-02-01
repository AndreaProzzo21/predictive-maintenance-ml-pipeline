import time
import threading
from collections import deque
from typing import Optional, Dict, Callable
from domain.models.schemas import TelemetryPayload, GroundTruthPayload, MergedDataPoint

class MeasurementBuffer:
    """
    Buffer che accumula i messaggi da entrambi i topic e li matcha 
    tramite measurement_id. Thread-safe.
    """
    def __init__(self, timeout_seconds: float = 30.0, on_merge: Optional[Callable] = None):
        self._telemetry_buffer: Dict[int, TelemetryPayload] = {}
        self._ground_truth_buffer: Dict[int, GroundTruthPayload] = {}
        self._timestamps: Dict[int, float] = {}  # Per pulizia vecchi messaggi orphan
        
        self.timeout = timeout_seconds
        self.on_merge = on_merge  # Callback quando match avviene
        
        self._lock = threading.Lock()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def add_telemetry(self, payload: TelemetryPayload):
        """Chiamato quando arriva un messaggio sul topic telemetry"""
        with self._lock:
            mid = payload.measurement_id
            
            # Controllo se ground_truth è già arrivato
            if mid in self._ground_truth_buffer:
                # MATCH! Creo il dato mergiato
                truth = self._ground_truth_buffer.pop(mid)
                self._timestamps.pop(mid, None)
                merged = self._create_merged(payload, truth)
                if self.on_merge:
                    self.on_merge(merged)
            else:
                # Buffering in attesa di ground_truth
                self._telemetry_buffer[mid] = payload
                self._timestamps[mid] = time.time()
    
    def add_ground_truth(self, payload: GroundTruthPayload):
        """Chiamato quando arriva un messaggio sul topic ground_truth"""
        with self._lock:
            mid = payload.measurement_id
            
            if mid in self._telemetry_buffer:
                # MATCH!
                telem = self._telemetry_buffer.pop(mid)
                self._timestamps.pop(mid, None)
                merged = self._create_merged(telem, payload)
                if self.on_merge:
                    self.on_merge(merged)
            else:
                self._ground_truth_buffer[mid] = payload
                self._timestamps[mid] = time.time()
    
    def _create_merged(self, telem: TelemetryPayload, truth: GroundTruthPayload) -> MergedDataPoint:
        print(f"[DEBUG] Creating merged object ID: {telem.device_id}, Truth ID: {truth.device_id}")
        # Debug: verifica che i dati esistano
        if not telem.device_id:
            raise ValueError("Telemetry manca device_id")
        if not truth.device_id:
            raise ValueError("GroundTruth manca device_id")
    
        data = MergedDataPoint(
            measurement_id=telem.measurement_id,
            device_id=telem.device_id,  # ESPLICITAMENTE QUI
            operating_hours=telem.operating_hours,
            sensors=telem.sensors,
            health_percent=truth.health_percent,
            rul_hours=truth.rul_hours,
            state=truth.state,
            failure_mode=truth.failure_mode,
            life_consumed_pct=truth.life_consumed_pct,
            esp_uptime_telemetry=telem.esp_uptime,
            esp_uptime_truth=truth.esp_uptime
        )
        print(f"[DEBUG] Merged object ID: {data.device_id}")
        return data
    
    def _cleanup_loop(self):
        """Pulisce messaggi orfani che non hanno trovatocorrispondenza"""
        while True:
            time.sleep(self.timeout)
            current_time = time.time()
            
            with self._lock:
                expired = [
                    mid for mid, ts in self._timestamps.items() 
                    if current_time - ts > self.timeout
                ]
                
                for mid in expired:
                    if mid in self._telemetry_buffer:
                        print(f"[Buffer] Timeout telemetry MID {mid}, scartato")
                        del self._telemetry_buffer[mid]
                    if mid in self._ground_truth_buffer:
                        print(f"[Buffer] Timeout ground_truth MID {mid}, scartato")
                        del self._ground_truth_buffer[mid]
                    del self._timestamps[mid]