import os
import logging
from mqtt_fetcher import MQTTPumpFetcher
from predictor import PumpPredictor
from inference_manager import InferenceManager
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Main")

def main():
    logger.info("🚀 Avvio Inference Service (Scaling Mode - 100+ Devices)")

    broker = os.getenv("MQTT_BROKER", "mosquitto")
    port = int(os.getenv("MQTT_PORT", 1883))
        
    input_topic = os.getenv("MQTT_INPUT_TOPIC", "factory/pumps/+/telemetry")
    
    model_dir = os.getenv("MODEL_DIR", "/app/models")
    
    output_dir = os.getenv("OUTPUT_DATA_DIR", "/app/data/predictions")


    try:
        predictor = PumpPredictor(model_dir)
        fetcher = MQTTPumpFetcher(broker, port, input_topic)
        
        manager = InferenceManager(
            predictor=predictor, 
            base_output_path=output_dir, 
            mqtt_client=fetcher.client
        )
        
        logger.info(f"📡 In ascolto su: {input_topic}")
        logger.info(f"📂 Salvataggio stream dati in: {output_dir}")
   
        fetcher.start(callback_function=manager.process_data)
        
    except Exception as e:
        logger.error(f"❌ Errore fatale durante l'avvio: {e}")

if __name__ == "__main__":
    main()