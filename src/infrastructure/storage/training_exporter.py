import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from influxdb_client import InfluxDBClient

class TrainingDataExporter:
    """Estrae dati da InfluxDB in formato CSV pronto per ML (flat table)."""
    
    def __init__(self, client: InfluxDBClient, bucket: str, org: str):
        self.client = client
        self.bucket = bucket
        self.org = org
        self.query_api = client.query_api()
    
    def export_to_csv(self, 
                      output_path: str,
                      hours_back: Optional[int] = None,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Estrae dati in formato flat (una riga = un measurement_id).
        
        Args:
            hours_back: quante ore indietro (es. 12 per ultimi 12h)
            start_time: datetime specifico (override hours_back)
            output_path: dove salvare il CSV
        """
        
        # Calcolo range temporale
        if start_time and end_time:
            start = start_time.isoformat() + "Z"
            stop = end_time.isoformat() + "Z"
        elif hours_back:
            stop = datetime.utcnow().isoformat() + "Z"
            start = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat() + "Z"
        else:
            raise ValueError("Specificare hours_back o start_time/end_time")
        
        # Query Flux: pivot per avere colonne flat (wide format)
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r._measurement == "pump_telemetry")
            |> pivot(
                rowKey: ["_time", "device_id", "state"],  
                columnKey: ["_field"],                     
                valueColumn: "_value"
            )
        '''
        
        print(f"[Exporter] Query da {start} a {stop}...")
        df = self.query_api.query_data_frame(query, org=self.org)
        
        if df.empty:
            print("[Exporter] Nessun dato trovato nel range specificato")
            return pd.DataFrame()
        
        # Pulizia colonne (Influx aggiunge _time, _start, _stop, etc)
        cols_to_drop = ['_start', '_stop', '_measurement', 'table', 'result']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        
        # Rinomina _time in timestamp
        if '_time' in df.columns:
            df = df.rename(columns={'_time': 'timestamp'})
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Ordina per measurement_id (se presente) o timestamp
        if 'measurement_id' in df.columns:
            df = df.sort_values('measurement_id')
        
        # Salva CSV
        df.to_csv(output_path, index=False)
        print(f"[Exporter] Salvati {len(df)} campioni in {output_path}")
        print(f"[Exporter] Colonne: {list(df.columns)}")
        print(f"[Exporter] Distribuzione stati:\n{df['state'].value_counts()}")
        
        return df
    
    def get_dataset_summary(self, hours_back: int = 24) -> dict:
        """Ritorna statistiche rapide senza scaricare tutto."""
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -{hours_back}h)
            |> filter(fn: (r) => r._measurement == "pump_telemetry")
            |> group(columns: ["state"])
            |> count()
        '''
        result = self.query_api.query(query, org=self.org)
        
        summary = {}
        for table in result:
            for record in table.records:
                state = record.values.get('state', 'unknown')
                count = record.get_value()
                summary[state] = count
        
        return summary