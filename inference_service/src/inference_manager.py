import os
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger("InferenceManager")

class InferenceManager:
    def __init__(self, predictor, csv_path):
        self.predictor = predictor
        self.csv_path = csv_path

    def process_data(self, data):
        """
        Questa è la nostra CALLBACK FUNCTION.
        Viene chiamata ogni volta che il Fetcher riceve un messaggio MQTT.
        """
        logger.info(f"📥 Ricevuto pacchetto telemetry: {data.get('measurement_id', 'N/A')}")

        # 1. Chiediamo al modello di fare la predizione
        predicted_state = self.predictor.predict(data)
        
        # 2. Arricchiamo il dato con il risultato dell'IA
        data['predicted_state'] = predicted_state
        data['inference_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"🔮 Risultato Inferenza: {predicted_state}")

        # 3. Salvataggio su CSV
        self._save_to_csv(data)

    def _save_to_csv(self, data):
        df = pd.DataFrame([data])
        # Scriviamo l'header solo se il file è nuovo
        file_exists = os.path.isfile(self.csv_path)
        df.to_csv(self.csv_path, mode='a', index=False, header=not file_exists)