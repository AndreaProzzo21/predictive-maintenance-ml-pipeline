import json
import queue
import paho.mqtt.client as mqtt
from pydantic import TypeAdapter
from domain.schemas.telemetry_schemas import TrainingPayload

class MQTTPumpFetcher:
    def __init__(self, output_queue: queue.Queue, broker="localhost", port=1883, topic="factory/training/+/training_data"):
        self.output_queue = output_queue
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._adapter = TypeAdapter(TrainingPayload)
        self.broker = broker
        self.port = port

    def _on_connect(self, client, userdata, flags, rc):
        print(f"✅ Connesso al broker. Sottoscrizione a {self.topic}")
        client.subscribe(self.topic)

    def _on_message(self, client, userdata, msg):
        try:
            raw_payload = json.loads(msg.payload.decode())
            # Validazione immediata
            validated_data = self._adapter.validate_python(raw_payload)
            
            # Invio diretto alla coda verso InfluxDB
            self.output_queue.put(validated_data)
            
        except Exception as e:
            print(f"❌ Errore processamento messaggio: {e}")

    def start(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()