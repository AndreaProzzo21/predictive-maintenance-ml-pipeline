import os
import logging
from typing import List
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import WriteOptions
from domain.schemas.telemetry_schemas import TrainingPayload
from infrastructure.storage.storage_interface import StorageInterface

logger = logging.getLogger(__name__)

class InfluxDBWriter(StorageInterface):
    def __init__(self, url: str = None, token: str = None, org: str = None, bucket: str = None):
        self.url = url or os.getenv("INFLUX_URL", "http://localhost:8086")
        self.token = token or os.getenv("INFLUX_TOKEN")
        self.org = org or os.getenv("INFLUX_ORG", "pump-org")
        self.bucket = bucket or os.getenv("INFLUX_BUCKET", "pump-data")
        
        if not self.token:
            raise ValueError("InfluxDB token mancante.")
        
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=WriteOptions(batch_size=10))

    def _to_influx_point(self, data: TrainingPayload) -> Point:
        return Point("pump_telemetry") \
            .tag("device_id", data.device_id) \
            .tag("state", data.ground_truth) \
            .field("vibration_x", data.vibration_x) \
            .field("vibration_y", data.vibration_y) \
            .field("vibration_z", data.vibration_z) \
            .field("vibration_rms", data.vibration_rms) \
            .field("temperature", data.temperature) \
            .field("current", data.current) \
            .field("pressure", data.pressure) \
            .field("rpm", data.rpm) \
            .field("health_percent", data.health_percent) \
            .time(data.timestamp_received)

    def write(self, point: TrainingPayload) -> bool:
        try:
            self.write_api.write(bucket=self.bucket, record=self._to_influx_point(point))
            return True
        except Exception as e:
            logger.error(f"Errore scrittura: {e}")
            return False

    def write_batch(self, points: List[TrainingPayload]) -> int:
        if not points: return 0
        try:
            influx_points = [self._to_influx_point(p) for p in points]
            self.write_api.write(bucket=self.bucket, record=influx_points)
            return len(points)
        except Exception as e:
            logger.error(f"Errore batch: {e}")
            return 0

    def flush(self): self.write_api.flush()
    def health_check(self) -> bool: return self.client.ping()
    def close(self):
        self.write_api.close()
        self.client.close()