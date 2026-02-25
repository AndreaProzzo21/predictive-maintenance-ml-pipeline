import os
import queue
import logging
import time
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AcquisitionService")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acquisition.mqtt_fetcher import MQTTPumpFetcher
from orchestration.data_manager import DataManager

def main():
    logger.info("🚀 Avvio Servizio Acquisizione (Python Simulator Mode)")
    
    data_queue = queue.Queue(maxsize=1000)
    
    # Configura il Fetcher (Assicurati che il topic sia quello del nuovo simulatore)
    fetcher = MQTTPumpFetcher(
        output_queue=data_queue, 
        broker="172.17.0.1", # IP del broker
        topic="factory/training/+/training_data"
    )
    
    data_manager = DataManager(data_queue=data_queue, batch_size=10)

    try:
        fetcher.start()
        data_manager.start()
        
        while True:
            time.sleep(10)
            status = "OK" if data_manager.storage.health_check() else "DOWN"
            logger.info(f"📊 Queue: {data_queue.qsize()} | Storage: {status}")
            
    except KeyboardInterrupt:
        logger.info("🛑 Arresto...")
        fetcher.stop()
        data_manager.stop()

if __name__ == "__main__":
    main()