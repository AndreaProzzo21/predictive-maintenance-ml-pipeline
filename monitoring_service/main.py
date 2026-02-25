import os
import logging
import threading
import uvicorn
from communication.mqtt.mqtt_fetcher import MQTTFetcher
from application.core_manager import CoreManager
from data.data_manager import DataManager
from communication.api.api_server import create_app  # Assicurati che il file si chiami così

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MonitoringService")

def main():
    logger.info("🚀 Starting Monitoring Service with API...")

    # 1. Caricamento Config (Environment Variables)
    mqtt_broker = os.getenv("MONITOR_MQTT_BROKER", "inference_broker")
    mqtt_port = int(os.getenv("MONITOR_MQTT_PORT", 1883))
    mqtt_topic = os.getenv("MONITOR_TOPIC", "factory/pumps/+/predictions")

    influx_url = os.getenv("INFLUX_URL", "http://pump_influxdb_monitor:8086")
    influx_token = os.getenv("INFLUX_TOKEN")
    influx_org = os.getenv("INFLUX_ORG")
    influx_bucket = os.getenv("INFLUX_BUCKET")

    try:
        # 2. Inizializzazione Layer
        data_manager = DataManager(influx_url, influx_token, influx_org, influx_bucket)
        core_manager = CoreManager(data_manager)
        fetcher = MQTTFetcher(mqtt_broker, mqtt_port, mqtt_topic, core_manager)

        # 3. Start MQTT Fetcher in a BACKGROUND THREAD
        # Usiamo un thread dedicato per non bloccare l'esecuzione di FastAPI
        mqtt_thread = threading.Thread(target=fetcher.start, daemon=True)
        mqtt_thread.start()
        logger.info(f"📡 MQTT Fetcher started in background on broker {mqtt_broker}")

        # 4. Inizializzazione FastAPI
        app = create_app(core_manager)

        # 5. Start API Server (Operazione Bloccante)
        logger.info("🌐 API Server starting on http://0.0.0.0:8080")
        # uvicorn.run è l'entry point che mantiene il servizio attivo
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

    except Exception as e:
        logger.error(f"❌ Fatal error during startup: {e}")
    finally:
        # Nota: uvicorn gestisce i segnali di stop (Ctrl+C), 
        # questo blocco verrà eseguito allo spegnimento
        logger.info("🛑 Shutting down service...")
        if 'data_manager' in locals():
            data_manager.close()

if __name__ == "__main__":
    main()