import time
import json
import random
import math
import threading
import os
import paho.mqtt.client as mqtt

class TrainingSimulator:
    def __init__(self, pump_id, broker, port, base_topic):
        self.pump_id = pump_id
        self.broker = broker
        self.port = port
        self.topic = f"{base_topic}/{pump_id}/training_data"
        
        self.health_percent = 100.0
        self.cycle_count = 0
        # Per il training, usiamo una vita variabile per avere campioni diversificati
        self.total_life_cycles = random.randint(1000, 3000) 
        
        self.baseline = {
            "temp": 38.0 + random.uniform(-2, 2),
            "current": 7.8 + random.uniform(-0.5, 0.5),
            "pressure": 4.2 + random.uniform(-0.3, 0.3),
            "rpm": 2850 + random.randint(-15, 15),
            "vib_x": 1.1, "vib_y": 0.7, "vib_z": 0.9
        }
        self.client = mqtt.Client(client_id=f"Train-{pump_id}")

    def get_ground_truth(self):
        """Assegna la label basata sulla salute reale (Ground Truth)"""
        if self.health_percent > 75:
            return "HEALTHY"
        elif self.health_percent > 35:
            return "WARNING"
        elif self.health_percent > 10:
            return "FAULTY"
        else:
            return "BROKEN"

    def update_degradation(self):
        self.cycle_count += 1
        life_consumed = min(self.cycle_count / self.total_life_cycles, 1.0)
        # Esponenziale per simulare l'usura meccanica reale
        factor = pow(life_consumed, 2.0)
        self.health_percent = max(0.0, 100.0 * (1.0 - factor))

    def generate_sensor_data(self):
        wear_f = (100.0 - self.health_percent) / 100.0
        wear_vib = pow(wear_f, 2.0) * 10.0 

        v_x = self.baseline["vib_x"] + random.uniform(-0.1, 0.1) + (wear_vib * 1.2)
        v_y = self.baseline["vib_y"] + random.uniform(-0.1, 0.1) + (wear_vib * 0.8)
        v_z = self.baseline["vib_z"] + random.uniform(-0.1, 0.1) + (wear_vib * 0.6)
        v_rms = math.sqrt(v_x**2 + v_y**2 + v_z**2)

        temp = self.baseline["temp"] + (wear_f * 40.0) + (v_rms * 0.3) + random.uniform(-0.5, 0.5)
        curr = self.baseline["current"] + (wear_f * 5.0) + random.uniform(-0.2, 0.2)
        pres = self.baseline["pressure"] - (wear_f * 1.5) + random.uniform(-0.1, 0.1)
        rpm = self.baseline["rpm"] - int(wear_f * 60) + random.randint(-10, 10)

        return v_x, v_y, v_z, v_rms, temp, curr, pres, rpm

    def run(self, interval=0.5):
        """In modalità training inviamo dati più velocemente"""
        try:
            self.client.connect(self.broker, self.port)
            while self.cycle_count < self.total_life_cycles + 50: # Continua un po' dopo la 'rottura'
                self.update_degradation()
                v_x, v_y, v_z, v_rms, t, curr, p, rpm = self.generate_sensor_data()
                
                # Includiamo gli spike nel training? 
                # SI, ma solo raramente, così il modello impara a ignorarli o classificarli
                if random.random() < 0.01: # 1% di probabilità spike
                    v_rms += random.uniform(5, 10)
                    t += random.uniform(5, 10)

                payload = {
                    "device_id": self.pump_id,
                    "vibration_x": round(v_x, 2),
                    "vibration_y": round(v_y, 2),
                    "vibration_z": round(v_z, 2),
                    "vibration_rms": round(v_rms, 2),
                    "temperature": round(t, 1),
                    "current": round(curr, 2),
                    "pressure": round(p, 2),
                    "rpm": int(rpm),
                    "ground_truth": self.get_ground_truth(), # LA LABEL PER IL TRAINING
                    "health_percent": round(self.health_percent, 1)
                }

                self.client.publish(self.topic, json.dumps(payload))
                time.sleep(interval)
                
                if self.cycle_count % 100 == 0:
                    print(f"📡 [{self.pump_id}] Progress: {self.health_percent}% - Label: {payload['ground_truth']}")
            
            print(f"🏁 [{self.pump_id}] Training sequence complete.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
   
    BROKER = os.getenv("MQTT_BROKER_HOST", "172.17.0.1") 
    PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
    TOPIC_BASE = os.getenv("MQTT_TRAINING_TOPIC", "factory/training")
    
    # Quante pompe simulare contemporaneamente
    NUM_PUMPS_FOR_TRAIN = int(os.getenv("NUM_TRAIN_PUMPS", 3))
    # Velocità di invio (secondi tra un messaggio e l'altro)
    INTERVAL = float(os.getenv("SIM_INTERVAL", 0.1)) 
    
    print(f"🚀 Avvio simulazione training su {BROKER}:{PORT}")
    print(f"📊 Pompe in parallelo: {NUM_PUMPS_FOR_TRAIN} | Intervallo: {INTERVAL}s")

    threads = []
    for i in range(NUM_PUMPS_FOR_TRAIN):
        sim = TrainingSimulator(f"TRAIN-PUMP-{i+1:03d}", BROKER, PORT, TOPIC_BASE)
        t = threading.Thread(target=sim.run, args=(INTERVAL,)) 
        t.start()
        threads.append(t)
        
    for t in threads:
        t.join()