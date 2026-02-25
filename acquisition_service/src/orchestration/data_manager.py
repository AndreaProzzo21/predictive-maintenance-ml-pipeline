import queue
import threading
import logging
from typing import Optional, List
from domain.schemas.telemetry_schemas import TrainingPayload
from infrastructure.storage.storage_interface import StorageInterface
from infrastructure.storage.influx_writer import InfluxDBWriter

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, data_queue: queue.Queue, storage: Optional[StorageInterface] = None, batch_size: int = 5):
        self.queue = data_queue
        self.storage = storage or InfluxDBWriter()
        self.batch_size = batch_size
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._buffer: List[TrainingPayload] = []

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                data: TrainingPayload = self.queue.get(timeout=2.0)
                self._buffer.append(data)
                if len(self._buffer) >= self.batch_size:
                    self._flush_buffer()
            except queue.Empty:
                if self._buffer: self._flush_buffer()
        
        if self._buffer: self._flush_buffer()
        self.storage.close()

    def _flush_buffer(self):
        points = self._buffer.copy()
        self._buffer = []
        try:
            self.storage.write_batch(points)
            logger.info(f"💾 Salvati {len(points)} punti. Ultimo stato: {points[-1].ground_truth}")
        except Exception as e:
            logger.error(f"Errore flush: {e}")

    def stop(self):
        self._stop_event.set()
        if self._thread: self._thread.join()