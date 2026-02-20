import joblib
import numpy as np
import os
import logging

logger = logging.getLogger("Predictor")

class PumpPredictor:
    def __init__(self, model_dir):
        # Carichiamo i file .pkl
        try:
            self.scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))
            self.clf = joblib.load(os.path.join(model_dir, 'classifier_state.pkl'))
            self.le = joblib.load(os.path.join(model_dir, 'label_encoder.pkl'))
            logger.info("🧠 Modelli ML caricati correttamente in memoria.")
        except Exception as e:
            logger.critical(f"💀 Impossibile caricare i modelli: {e}")
            raise

    def predict(self, data):
        """
        Riceve il dizionario dei sensori e restituisce lo stato predetto.
        """
        # L'ordine deve essere IDENTICO a quello del training sul tuo PC
        feature_order = [
            'current', 'pressure', 'rpm', 'temperature', 
            'vibration_rms', 'vibration_x', 'vibration_y', 'vibration_z'
        ]
        
        try:
            # Estraiamo i valori nell'ordine corretto
            input_data = [data[f] for f in feature_order]
            
            # Trasformazione per Scikit-Learn
            X = np.array(input_data).reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            
            # Predizione numerica
            class_idx = self.clf.predict(X_scaled)[0]
            
            # Traduzione in stringa (HEALTHY, WARNING, ecc.)
            state_label = self.le.inverse_transform([class_idx])[0]
            
            return state_label
        except KeyError as e:
            logger.error(f"❌ Dato mancante nel JSON MQTT: {e}")
            return "DATA_ERROR"