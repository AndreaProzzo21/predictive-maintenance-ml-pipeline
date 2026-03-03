import joblib
import numpy as np
import os
import logging

logger = logging.getLogger("Predictor")

class PumpPredictor:
    def __init__(self, model_dir):
        try:
            self.scaler = joblib.load(os.path.join(model_dir, 'scaler_v2.pkl'))
            self.clf = joblib.load(os.path.join(model_dir, 'classifier_state_v2.pkl'))
            self.reg = joblib.load(os.path.join(model_dir, 'regressor_health_v2.pkl')) # Carichiamo il regressore
            self.le = joblib.load(os.path.join(model_dir, 'label_encoder_v2.pkl'))
            logger.info("🧠 Modelli ML (Classificatore + Regressore) caricati correttamente.")
        except Exception as e:
            logger.critical(f"💀 Impossibile caricare i modelli: {e}")
            raise

    def predict(self, data):
        feature_order = [
            'current', 'pressure', 'rpm', 'temperature', 
            'vibration_rms', 'vibration_x', 'vibration_y', 'vibration_z'
        ]
        
        try:
            input_data = [data[f] for f in feature_order]
            X = np.array(input_data).reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            
            # 1. Predizione dello STATO (Classificazione)
            class_idx = self.clf.predict(X_scaled)[0]
            state_label = self.le.inverse_transform([class_idx])[0]
            
            # 2. Predizione della SALUTE (Regressione)
            predicted_health = float(self.reg.predict(X_scaled)[0])
            predicted_health = max(0, min(100, predicted_health))
            
            return {
                "state": state_label,
                "health": round(predicted_health, 2)
            }
            
        except KeyError as e:
            logger.error(f"❌ Dato mancante nel JSON MQTT: {e}")
            return None