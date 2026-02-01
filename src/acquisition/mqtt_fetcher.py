import os
import json
import threading
import queue
from typing import Callable
import yaml
import paho.mqtt.client as mqtt
from pydantic import ValidationError, TypeAdapter

from domain.models.schemas import TelemetryPayload, GroundTruthPayload, MergedDataPoint
from acquisition.buffer_merger import MeasurementBuffer

class MQTTPumpFetcher:
    """
    Fetcher dedicato al progetto Pump001.
    Gestisce due topic e li mergia tramite measurement_id.
    """
    def __init__(self, output_queue: queue.Queue, config_path: str = "config/mqtt.yaml"):
        self.output_queue = output_queue  # Coda verso il processing successivo
        
        # Carica config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.mqtt_config = self.config['mqtt']
        self.buffer_config = self.config['buffer']
        
        # Inizializza buffer di merge
        self.buffer = MeasurementBuffer(
            timeout_seconds=self.buffer_config['merge_timeout'],
            on_merge=self._on_data_merged  # Callback quando i dati sono pronti
        )
        
        # Setup MQTT client
        self.client = mqtt.Client(client_id=self.mqtt_config['broker']['client_id'])
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Threading
        self._thread: threading.Thread = None
        self._stop_event = threading.Event()
        
        # TypeAdapters per validazione veloce
        self._telemetry_adapter = TypeAdapter(TelemetryPayload)
        self._truth_adapter = TypeAdapter(GroundTruthPayload)

    def _on_connect(self, client, userdata, flags, rc):
        print(f"[MQTTFetcher] Connesso al broker (rc={rc})")
        
        # Subscribe ai due topic della pompa
        telemetry_topic = self.mqtt_config['topics']['telemetry']
        ground_truth_topic = self.mqtt_config['topics']['ground_truth']
        client.subscribe(telemetry_topic)
        client.subscribe(ground_truth_topic)
        print(f"[MQTTFetcher] Sottoscritto a: {telemetry_topic} and {ground_truth_topic}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"[MQTTFetcher] Disconnesso inaspettatamente (rc={rc}), riconnessione...")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic
            
            # Routing basato sul topic
            if topic == self.mqtt_config['topics']['telemetry']:
                self._handle_telemetry(payload)
                
            elif topic == self.mqtt_config['topics']['ground_truth']:
                self._handle_ground_truth(payload)
                
            else:
                print(f"[MQTTFetcher] Topic sconosciuto: {topic}")

        except ValidationError as e:
            print(f"[MQTTFetcher] Errore validazione: {e}")
            # Qui potresti salvare i raw data su un file "quarantena" per analisi
            
        except Exception as e:
            print(f"[MQTTFetcher] Errore generico: {e}")

    def _handle_telemetry(self, payload: dict):
        """Processa dati sensori"""
        validated = self._telemetry_adapter.validate_python(payload)
        self.buffer.add_telemetry(validated)
        print(f"[MQTTFetcher] Telemetry MID {validated.measurement_id} ricevuto: {payload}")

    def _handle_ground_truth(self, payload: dict):
        """Processa label/ground truth"""
        validated = self._truth_adapter.validate_python(payload)
        self.buffer.add_ground_truth(validated)
        print(f"[MQTTFetcher] GroundTruth MID {validated.measurement_id} ricevuto: {payload}")

    def _on_data_merged(self, merged_data: MergedDataPoint):
        """
        Callback chiamato quando buffer_merger ha matchato 
        telemetry + ground_truth con lo stesso MID
        """
        try:
            # Mette in coda verso il processing (validazione/feature eng)
            self.output_queue.put(merged_data, block=False)
            print(f"[MQTTFetcher] MATCH! MID {merged_data.measurement_id} -> Queue "
                  f"(State: {merged_data.state}, Health: {merged_data.health_percent}%)")
                  
        except queue.Full:
            print(f"[MQTTFetcher] ATTENZIONE: Coda piena, MID {merged_data.measurement_id} scartato")

    def start(self):
        """Avvia il fetcher in thread separato"""
        if self._thread and self._thread.is_alive():
            return
            
        def run():
            # Setup autenticazione se presente
            user = self.mqtt_config['broker'].get('username')
            pwd = self.mqtt_config['broker'].get('password')
            if user and pwd:
                self.client.username_pw_set(user, pwd)
            
            try:
                self.client.connect(
                    self.mqtt_config['broker']['host'],
                    self.mqtt_config['broker']['port'],
                    self.mqtt_config['keepalive']
                )
                self.client.loop_forever()
            except Exception as e:
                print(f"[MQTTFetcher] Errore connessione: {e}")
                self._stop_event.set()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        print("[MQTTFetcher] Thread avviato")

    def stop(self):
        """Ferma il fetcher gracefulmente"""
        self._stop_event.set()
        self.client.disconnect()
        if self._thread:
            self._thread.join(timeout=5)