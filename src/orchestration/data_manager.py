import queue
import threading
import logging
import time
from typing import Optional
from datetime import datetime

from domain.models.schemas import MergedDataPoint
from infrastructure.storage.storage_interface import StorageInterface
from infrastructure.storage.influx_writer import InfluxDBWriter

logger = logging.getLogger(__name__)

class DataManager:
    """
    Worker thread che preleva dati dalla coda MQTT e li salva su storage.
    Gestisce batching e fallback se lo storage principale fallisce.
    """
    def __init__(self, 
                 data_queue: queue.Queue,
                 storage: Optional[StorageInterface] = None,
                 batch_size: int = 5,
                 max_queue_wait: float = 2.0):
        
        self.queue = data_queue
        self.storage = storage or InfluxDBWriter()  # Default Influx
        self.batch_size = batch_size
        self.max_queue_wait = max_queue_wait
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._buffer = []  # Buffer locale per batching
        
    def start(self):
        """Avvia il worker thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("DataManager avviato")

    def _run(self):
        """Loop principale del worker."""
        logger.info("DataManager worker in esecuzione...")
        
        while not self._stop_event.is_set():
            try:
                # Aspetta dati dalla coda con timeout
                data: MergedDataPoint = self.queue.get(timeout=self.max_queue_wait)
                self._buffer.append(data)
                
                # Flusso immediato se buffer pieno
                if len(self._buffer) >= self.batch_size:
                    self._flush_buffer()
                    
            except queue.Empty:
                # Nessun dato nuovo: svuota comunque il buffer se non vuoto
                if self._buffer:
                    self._flush_buffer()
                    
        # Flush finale alla chiusura
        if self._buffer:
            self._flush_buffer()
        self.storage.close()

    def _flush_buffer(self):
        """Salva il buffer corrente su storage."""
        if not self._buffer:
            return
            
        points_to_save = self._buffer.copy()
        self._buffer = []
        
        try:
            count = self.storage.write_batch(points_to_save)
            logger.info(f"Salvati {count}/{len(points_to_save)} punti su InfluxDB")
            
            # Log esempio dell'ultimo punto per debug
            if points_to_save:
                last = points_to_save[-1]
                logger.debug(f"Ultimo: MID {last.measurement_id} | "
                           f"Health {last.health_percent}% | {last.state}")
                           
        except Exception as e:
            logger.error(f"Errore salvataggio batch: {e}")
            # Qui potresti implementare fallback su CSV o reinserimento in coda
            self._handle_failed_write(points_to_save)

    def _handle_failed_write(self, failed_points):
        """Gestisce punti non salvati (es. salvataggio su CSV di emergenza)."""
        logger.warning(f"Scartati {len(failed_points)} punti per errore storage")
        # TODO: Implementare CSV fallback se necessario

    def stop(self):
        """Ferma gracefulmente il worker."""
        logger.info("Arresto DataManager...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("DataManager fermato")