import os
import queue
import logging
import time
import sys

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Pipeline")

# Imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acquisition.mqtt_fetcher import MQTTPumpFetcher
from orchestration.data_manager import DataManager

def main():
    logger.info("🚀 Avvio Pipeline Phase 1 - Acquisition + Storage")
    
    # Coda condivisa tra Fetcher e DataManager
    data_queue = queue.Queue(maxsize=1000)
    
    # 1. Avvia Fetcher MQTT
    fetcher = MQTTPumpFetcher(output_queue=data_queue)
    fetcher.start()
    
    # 2. Avvia DataManager (InfluxDB)
    try:
        data_manager = DataManager(
            data_queue=data_queue,
            batch_size=5,  # Salva ogni 5 punti o ogni 2 secondi
            max_queue_wait=2.0
        )
        data_manager.start()
        
        logger.info("✅ Pipeline attiva. In attesa di dati dall'ESP32...")
        logger.info("📊 Dashboard InfluxDB: http://localhost:8086 (admin/adminpassword123)")
        
        # Loop di monitoraggio
        while True:
            time.sleep(10)
            logger.info(f"📈 Queue size: {data_queue.qsize()} | "
                       f"Stato storage: {'OK' if data_manager.storage.health_check() else 'DOWN'}")
            
    except Exception as e:
        logger.error(f"❌ Errore avvio DataManager: {e}")
        logger.error("Verifica che InfluxDB sia accessibile (docker-compose ps)")
        fetcher.stop()
        return

    # Gestione arresto
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Arresto pipeline...")
        fetcher.stop()
        data_manager.stop()
        logger.info("✅ Pipeline fermata")

if __name__ == "__main__":
    main()