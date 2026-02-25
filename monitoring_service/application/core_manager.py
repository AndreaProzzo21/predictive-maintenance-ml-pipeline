import logging

class CoreManager:
    def __init__(self, data_manager, log_interval=50):
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)
        self.message_count = 0
        self.log_interval = log_interval

    def process_message(self, raw_payload):
        try:
            # Salvataggio dati completi (DataManager ora gestisce i nuovi campi)
            self.data_manager.save_prediction(raw_payload)
            self.message_count += 1

            state = raw_payload.get("state", "UNKNOWN")
            pump_id = raw_payload.get("device_id", "unknown")
            
            if state in ["WARNING", "BROKEN", "FAULTY"]:
                health = raw_payload.get('health_percent', 0)
                # Log più dettagliato per stati critici
                self.logger.warning(
                    f"🚨 CRITICAL: {pump_id} is {state}! Health: {health}% | "
                    f"Vib: {raw_payload.get('vibration_rms')} | Temp: {raw_payload.get('temperature')}"
                )
            
            elif self.message_count % self.log_interval == 0:
                self.logger.info(f"📊 Processed {self.message_count} messages. Last: {pump_id} is {state}")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def get_all_pumps_status(self):
        return self.data_manager.get_latest_pumps_data()

    def get_pumps_by_state(self, state: str):
        all_pumps = self.data_manager.get_latest_pumps_data()
        return [p for p in all_pumps if p.get("state", "").upper() == state.upper()]

    def get_pump_details(self, device_id: str):
        all_pumps = self.data_manager.get_latest_pumps_data()
        return next((p for p in all_pumps if p.get("device_id") == device_id), None)