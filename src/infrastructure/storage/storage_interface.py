from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models.schemas import MergedDataPoint

class StorageInterface(ABC):
    """Contratto per tutti gli storage (Influx, CSV, etc.)"""
    
    @abstractmethod
    def write(self, point: MergedDataPoint) -> bool:
        """Salva un singolo punto dati. Ritorna True se successo."""
        pass
    
    @abstractmethod
    def write_batch(self, points: List[MergedDataPoint]) -> int:
        """Salva un batch di punti. Ritorna numero di punti salvati."""
        pass
    
    @abstractmethod
    def flush(self):
        """Forza lo svuotamento dei buffer interni."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Verifica connessione/storage disponibile."""
        pass
    
    def close(self):
        """Cleanup risorse."""
        pass