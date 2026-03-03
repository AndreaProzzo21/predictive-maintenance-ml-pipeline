from abc import ABC, abstractmethod
from typing import List
from domain.schemas.telemetry_schemas import TrainingPayload

class StorageInterface(ABC):
    """Contratto per tutti gli storage (Influx, CSV, etc.)"""
    
    @abstractmethod
    def write(self, point: TrainingPayload) -> bool:
        pass
    
    @abstractmethod
    def write_batch(self, points: List[TrainingPayload]) -> int:
        pass
    
    @abstractmethod
    def flush(self):
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        pass
    
    @abstractmethod
    def close(self):
        pass