#!/usr/bin/env python3
"""
Script standalone per esportare dati training da InfluxDB a CSV.
Da eseguire manualmente quando si vuole fare il training.
"""

import sys
import os
import argparse
from datetime import datetime

# Aggiungi src al path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from influxdb_client import InfluxDBClient
from infrastructure.storage.training_exporter import TrainingDataExporter

def main():
    parser = argparse.ArgumentParser(description='Esporta dati pompa da InfluxDB a CSV')
    parser.add_argument('--hours', type=int, default=12, 
                       help='Quante ore di dati estrarre (default: 12)')
    parser.add_argument('--output', type=str, 
                       default=f'data/processed/training_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                       help='Path output CSV')
    parser.add_argument('--summary-only', action='store_true',
                       help='Solo statistiche, non esportare')
    
    args = parser.parse_args()
    
    # Config (stesse env var della pipeline)
    url = os.getenv("INFLUX_URL", "http://localhost:8086")
    token = os.getenv("INFLUX_TOKEN", "pump-super-secret-token")
    org = os.getenv("INFLUX_ORG", "pump-org")
    bucket = os.getenv("INFLUX_BUCKET", "pump-data")
    
    client = InfluxDBClient(url=url, token=token, org=org)
    exporter = TrainingDataExporter(client, bucket, org)
    
    try:
        if args.summary_only:
            print("=== Dataset Summary ===")
            summary = exporter.get_dataset_summary(args.hours)
            for state, count in summary.items():
                print(f"  {state}: {count} campioni")
        else:
            print(f"Esportazione ultimi {args.hours}h...")
            df = exporter.export_to_csv(args.output, hours_back=args.hours)
            
            if not df.empty:
                print(f"\n✅ Dataset pronto in: {args.output}")
                print(f"Shape: {df.shape}")
                print("\nPrime righe:")
                print(df.head())
                
    except Exception as e:
        print(f"❌ Errore: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()