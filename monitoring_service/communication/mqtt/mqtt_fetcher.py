import paho.mqtt.client as mqtt
import json
import logging

class MQTTFetcher:
    def __init__(self, broker, port, topic, core_manager):
        self.logger = logging.getLogger(__name__)
        self.broker = broker
        self.port = port
        self.topic = topic
        self.core_manager = core_manager
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"✅ Connected to MQTT Broker: {self.broker}")
            self.client.subscribe(self.topic)
            self.logger.info(f"📡 Subscribed to topic: {self.topic}")
        else:
            self.logger.error(f"❌ Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            self.core_manager.process_message(payload)
        except Exception as e:
            self.logger.error(f"❌ Error decoding MQTT message: {e}")

    def start(self):
        try:
            self.client.connect(self.broker, self.port)
            self.client.loop_start() # Esegue in un thread separato
        except Exception as e:
            self.logger.error(f"❌ Could not connect to MQTT Broker at {self.broker}:{self.port}")
            self.logger.error(str(e))