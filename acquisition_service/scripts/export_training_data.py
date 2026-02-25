import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from influxdb_client import InfluxDBClient
from infrastructure.storage.training_exporter import TrainingDataExporter

def main():
    parser = argparse.ArgumentParser(description='Esporta dati pompa da InfluxDB a CSV')
    parser.add_argument('--hours', type=int, default=12, help='Ore di dati (default: 12)')
    parser.add_argument('--output', type=str, help='Path output CSV custom')
    parser.add_argument('--summary-only', action='store_true', help='Solo statistiche')
    
    args = parser.parse_args()
    
    # Se l'output non è specificato, creiamo un nome file con timestamp
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f'data/processed/training_{timestamp}.csv'
    
    url = os.getenv("INFLUX_URL", "http://localhost:8086")
    token = os.getenv("INFLUX_TOKEN", "your-super-secret-token")
    org = os.getenv("INFLUX_ORG", "pump-org")
    bucket = os.getenv("INFLUX_BUCKET", "pump-data")
    
    client = InfluxDBClient(url=url, token=token, org=org)
    exporter = TrainingDataExporter(client, bucket, org)
    
    try:
        if args.summary_only:
            print(f"=== Dataset Summary (ultime {args.hours}h) ===")
            summary = exporter.get_dataset_summary(args.hours)
            if not summary:
                print("Nessun dato trovato.")
            for state, count in summary.items():
                print(f"  {state}: {count} campioni")
        else:
            df = exporter.export_to_csv(args.output, hours_back=args.hours)
            if not df.empty:
                print(f"\n✅ Export completato con successo.")
                
    except Exception as e:
        print(f"❌ Errore durante l'esportazione: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()