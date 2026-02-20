import os
import logging
from mqtt_fetcher import MQTTPumpFetcher
from predictor import PumpPredictor
from inference_manager import InferenceManager

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Main")

def main():
    logger.info("🚀 Avvio Inference Service (Fase 2)")

    # 1. Caricamento configurazioni da .env
    broker = os.getenv("MQTT_BROKER", "mosquitto")
    port = int(os.getenv("MQTT_PORT", 1883))
    topic = os.getenv("MQTT_TOPIC")
    model_dir = os.getenv("MODEL_DIR", "/app/models")
    csv_path = os.getenv("CSV_OUTPUT_PATH", "/app/data/live_predictions.csv")

    # 2. Inizializzazione componenti
    try:
        predictor = PumpPredictor(model_dir)
        manager = InferenceManager(predictor, csv_path)
        fetcher = MQTTPumpFetcher(broker, port, topic)
        
        # 3. Avvio (passiamo la callback del manager al fetcher)
        logger.info(f"📡 In ascolto sul topic: {topic}")
        fetcher.start(callback_function=manager.process_data)
        
    except Exception as e:
        logger.error(f"❌ Errore fatale durante l'avvio: {e}")

if __name__ == "__main__":
    main()