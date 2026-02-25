import time
import json
import random
import math
import threading
import os
from datetime import datetime, timedelta  # <--- Aggiunto
import paho.mqtt.client as mqtt

class PumpSimulator:
    def __init__(self, pump_id, broker, port, base_topic, mode="NOMINAL", start_delay=0):
        self.pump_id = pump_id
        self.broker = broker
        self.port = port
        self.topic = f"{base_topic}/{pump_id}/telemetry"
        self.mode = mode
        self.start_delay = start_delay

        # --- GENERAZIONE DATA MANUTENZIONE FISSA ---
        # Genera una data casuale tra 10 e 200 giorni fa
        random_days_ago = random.randint(10, 200)
        self.last_maintenance = (datetime.now() - timedelta(days=random_days_ago)).strftime("%Y-%m-%d")

        self._setup_mode_params()

        self.health_percent = 100.0
        self.cycle_count = 0

        self.baseline = {
            "temp": 38.0 + random.uniform(-2, 2),
            "current": 7.8 + random.uniform(-0.5, 0.5),
            "pressure": 4.2 + random.uniform(-0.3, 0.3),
            "rpm": 2850 + random.randint(-15, 15),
            "vib_x": 1.1, "vib_y": 0.7, "vib_z": 0.9
        }

        self.client = mqtt.Client(client_id=f"Sim-{pump_id}")

    # ... [Metodi _setup_mode_params, update_degradation, generate_data, apply_chaos rimangono invariati] ...

    def _setup_mode_params(self):
        if self.mode == "STRESS":
            self.total_life_cycles = random.randint(120, 200)
            self.interval = 1 
        elif self.mode == "ACCELERATED":
            self.total_life_cycles = random.randint(500, 800)
            self.interval = 2
        else: # NOMINAL
            self.total_life_cycles = random.randint(8000, 12000)
            self.interval = 10

    def update_degradation(self):
        self.cycle_count += 1
        life_consumed = min(self.cycle_count / self.total_life_cycles, 1.0)
        factor = pow(life_consumed, 2.5)
        self.health_percent = max(0.0, 100.0 * (1.0 - factor))

    def generate_data(self):
        wear_f = (100.0 - self.health_percent) / 100.0
        wear_vib = pow(wear_f, 2.0) * 10.0
        v_x = self.baseline["vib_x"] + random.uniform(-0.1, 0.1) + (wear_vib * 1.2)
        v_y = self.baseline["vib_y"] + random.uniform(-0.1, 0.1) + (wear_vib * 0.8)
        v_z = self.baseline["vib_z"] + random.uniform(-0.1, 0.1) + (wear_vib * 0.6)
        v_rms = math.sqrt(v_x**2 + v_y**2 + v_z**2)
        temp = self.baseline["temp"] + (wear_f * 40.0) + (v_rms * 0.3)
        curr = self.baseline["current"] + (wear_f * 5.0)
        pres = self.baseline["pressure"] - (wear_f * 1.5)
        rpm = self.baseline["rpm"] - int(wear_f * 50)
        return v_x, v_y, v_z, v_rms, temp, curr, pres, rpm

    def apply_chaos(self, v_x, v_rms, t, p, curr, rpm):
        if random.random() < 0.02: v_x += 10.0; v_rms += 8.0
        if random.random() < 0.01: t += 15.0
        return v_x, v_rms, t, p, curr, rpm

    def run(self):
        try:
            if self.start_delay > 0:
                print(f"⏳ [{self.pump_id}] Waiting {self.start_delay:.1f}s before starting...")
                time.sleep(self.start_delay)

            self.client.connect(self.broker, self.port)
            print(f"🚀 [{self.pump_id}] STARTED (Mode: {self.mode}) | Last Maint: {self.last_maintenance}")

            while True:
                self.update_degradation()
                v_x, v_y, v_z, v_rms, t, curr, p, rpm = self.generate_data()
                v_x, v_rms, t, p, curr, rpm = self.apply_chaos(v_x, v_rms, t, p, curr, rpm)

                payload = {
                    "measurement_id": self.cycle_count,
                    "device_id": self.pump_id,
                    "vibration_x": round(v_x, 2),
                    "vibration_y": round(v_y, 2),
                    "vibration_z": round(v_z, 2),
                    "vibration_rms": round(v_rms, 2),
                    "temperature": round(t, 1),
                    "current": round(curr, 2),
                    "pressure": round(p, 2),
                    "rpm": int(rpm),
                    "health_percent": round(self.health_percent, 1),
                    "last_maintenance": self.last_maintenance  # <--- Inviata in ogni messaggio
                }

                self.client.publish(self.topic, json.dumps(payload))

                if self.cycle_count % 10 == 0:
                    print(f"📊 [{self.pump_id}] Life: {self.cycle_count}/{self.total_life_cycles} | Health: {self.health_percent:.1f}%")

                time.sleep(self.interval)
        except Exception as e:
            print(f"❌ [{self.pump_id}] Error: {e}")

# ... [Il resto del blocco __main__ rimane uguale] ...
if __name__ == "__main__":
    BROKER = os.getenv("MQTT_BROKER", "172.17.0.1")
    PORT = int(os.getenv("MQTT_PORT", 1883))
    MODE = os.getenv("SIMULATION_MODE", "NOMINAL")
    NUM_PUMPS = int(os.getenv("NUM_PUMPS", 5))

    print(f"🏗️ Starting simulation for {NUM_PUMPS} pumps in {MODE} mode...")

    threads = []
    for i in range(NUM_PUMPS):
        p_id = f"PUMP-{i+1:03d}"
        random_delay = random.uniform(2, 10) # Ho ridotto il delay per i test
        
        sim = PumpSimulator(p_id, BROKER, PORT, "factory/pumps", mode=MODE, start_delay=random_delay)
        
        t = threading.Thread(target=sim.run)
        t.daemon = True
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Simulazione interrotta.")