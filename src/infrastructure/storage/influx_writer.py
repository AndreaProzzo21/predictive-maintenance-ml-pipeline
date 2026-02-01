import os
import logging
from datetime import datetime
from typing import List
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions

from domain.models.schemas import MergedDataPoint
from infrastructure.storage.storage_interface import StorageInterface

logger = logging.getLogger(__name__)

class InfluxDBWriter(StorageInterface):
    def __init__(self, 
                 url: str = None, 
                 token: str = None, 
                 org: str = None, 
                 bucket: str = None,
                 batch_size: int = 10,
                 flush_interval: int = 5000):
        
        self.url = url or os.getenv("INFLUX_URL", "http://localhost:8086")
        self.token = token or os.getenv("INFLUX_TOKEN")
        self.org = org or os.getenv("INFLUX_ORG", "pump-org")
        self.bucket = bucket or os.getenv("INFLUX_BUCKET", "pump-data")
        
        if not self.token:
            raise ValueError("InfluxDB token mancante. Setta INFLUX_TOKEN env var.")
        
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        
        # Write API con batching automatico per performance
        write_options = WriteOptions(
            batch_size=batch_size,
            flush_interval=flush_interval,  # ms
            jitter_interval=1000,
            retry_interval=3000,
            max_retries=3,
            max_retry_delay=15000,
            exponential_base=2
        )
        self.write_api = self.client.write_api(write_options=write_options)
        self.query_api = self.client.query_api()
        
        logger.info(f"InfluxDBWriter connesso a {self.url}, bucket: {self.bucket}")

    def _to_influx_point(self, data: MergedDataPoint) -> Point:
        """Converte MergedDataPoint in Point InfluxDB."""

        print(f"[Influx] Ricevuto: MID={data.measurement_id}, device_id={data.device_id}, state={data.state}")
        point = Point("pump_telemetry") \
            .tag("device_id", data.device_id) \
            .tag("state", data.state) \
            .tag("failure_mode", data.failure_mode) \
            .field("measurement_id", data.measurement_id) \
            .field("vibration_x", data.sensors.vibration_x) \
            .field("vibration_y", data.sensors.vibration_y) \
            .field("vibration_z", data.sensors.vibration_z) \
            .field("vibration_rms", data.sensors.vibration_rms) \
            .field("temperature", data.sensors.temperature) \
            .field("current", data.sensors.current) \
            .field("pressure", data.sensors.pressure) \
            .field("rpm", data.sensors.rpm) \
            .field("health_percent", data.health_percent) \
            .field("rul_hours", data.rul_hours) \
            .field("life_consumed_pct", data.life_consumed_pct) \
            .field("operating_hours", data.operating_hours) \
            .time(data.timestamp_received)
            
        return point

    def write(self, point: MergedDataPoint) -> bool:
        try:
            influx_point = self._to_influx_point(point)
            self.write_api.write(bucket=self.bucket, record=influx_point)
            return True
        except Exception as e:
            logger.error(f"Errore scrittura InfluxDB: {e}")
            return False

    def write_batch(self, points: List[MergedDataPoint]) -> int:
        if not points:
            return 0
            
        try:
            influx_points = [self._to_influx_point(p) for p in points]
            self.write_api.write(bucket=self.bucket, record=influx_points)
            return len(points)
        except Exception as e:
            logger.error(f"Errore batch write InfluxDB: {e}")
            return 0

    def flush(self):
        """Forza lo svuotamento del buffer di scrittura."""
        self.write_api.flush()
        logger.debug("Buffer InfluxDB flushato")

    def health_check(self) -> bool:
        try:
            # Verifica connessione con ping
            return self.client.ping()
        except Exception:
            return False

    def close(self):
        self.write_api.close()
        self.client.close()
        logger.info("Connessione InfluxDB chiusa")