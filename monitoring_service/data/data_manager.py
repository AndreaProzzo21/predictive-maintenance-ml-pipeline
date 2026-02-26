from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import WriteOptions
import random
from datetime import datetime, timedelta

class DataManager:
    def __init__(self, url, token, org, bucket):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.bucket = bucket
        
        # Ottimizzazione InfluxDB: Invio a batch ogni 50 record o 5 secondi
        self.write_api = self.client.write_api(write_options=WriteOptions(
            batch_size=50,
            flush_interval=5_000,
            retry_interval=2_000,
            max_retries=3
        ))

    def _generate_random_maintenance_date(self):
        """Fallback: Genera una data casuale negli ultimi 180 giorni"""
        days_ago = random.randint(1, 180)
        date = datetime.now() - timedelta(days=days_ago)
        return date.strftime("%Y-%m-%d")

    def save_prediction(self, data: dict):
        """Converte il JSON ricevuto in un punto InfluxDB e lo salva"""
        point = Point("pump_diagnostics") \
            .tag("device_id", data.get("device_id", "unknown")) \
            .field("state", data.get("state", "UNKNOWN")) \
            .field("health_score", float(data.get("health_percent", 0.0))) \
            .field("vibration_rms", float(data.get("vibration_rms", 0.0))) \
            .field("temperature", float(data.get("temperature", 0.0))) \
            .field("is_ai_prediction", bool(data.get("is_ai_prediction", False))) \
            .field("current", float(data.get("current", 0.0))) \
            .field("pressure", float(data.get("pressure", 0.0))) \
            .field("vibration_x", float(data.get("vibration_x", 0.0))) \
            .field("vibration_y", float(data.get("vibration_y", 0.0))) \
            .field("vibration_z", float(data.get("vibration_z", 0.0)))
        
        # Gestione data manutenzione: usa quella del payload o ne genera una
        last_maint = data.get("last_maintenance")
        if not last_maint:
            last_maint = self._generate_random_maintenance_date()
            
        point.field("last_maintenance", str(last_maint))
            
        self.write_api.write(bucket=self.bucket, record=point)
    
    def get_latest_pumps_data(self):
        """Esegue query Flux per ottenere l'ultimo stato noto di ogni pompa"""
        query_api = self.client.query_api()
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "pump_diagnostics")
          |> last()
          |> pivot(rowKey:["device_id"], columnKey: ["_field"], valueColumn: "_value")
        '''
        tables = query_api.query(query)
        
        results = []
        for table in tables:
            for record in table.records:
                results.append(record.values)
        return results

    def close(self):
        if self.client:
            self.client.close()