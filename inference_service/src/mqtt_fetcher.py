import json
import logging
from paho.mqtt import client as mqtt_client

logger = logging.getLogger("InferenceFetcher")

class MQTTPumpFetcher:
    def __init__(self, broker, port, topic):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = self.connect_mqtt()

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"✅ Connesso al Broker MQTT ({self.broker})")
                client.subscribe(self.topic)
            else:
                logger.error(f"❌ Connessione fallita, codice: {rc}")

        client = mqtt_client.Client()
        client.on_connect = on_connect
        return client

    def start(self, callback_function):
        """
        Avvia l'ascolto. Ogni volta che arriva un messaggio, 
        chiama la callback_function passata come argomento.
        """
        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                # Passiamo il dato decodificato alla funzione che farà l'inferenza
                callback_function(payload)
            except Exception as e:
                logger.error(f"⚠️ Errore decodifica JSON: {e}")

        self.client.on_message = on_message
        self.client.connect(self.broker, self.port)
        self.client.loop_forever()