#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ================= CONFIGURAZIONE =================
const char* ssid = "iPhone di Andrea";
const char* password = "dogofiero";

const char* mqtt_server = "52.57.201.174"; // Cambia con il tuo broker
const int mqtt_port = 1883;
const char* mqtt_user = "";        // Oppure "" se anonimo
const char* mqtt_password = "";    // Oppure ""

// Topic separati per Fase 1
const char* topic_telemetry = "factory/pump001/telemetry";     // Features per ML (X)
const char* topic_ground_truth = "factory/pump001/ground_truth"; // Label per ML (y)

WiFiClient espClient;
PubSubClient client(espClient);

// ================= STATO INTERNO MACCHINA =================
// Queste variabili rappresentano lo "stato fisico reale" della pompa
// che nel mondo reale sarebbe sconosciuto, ma qui lo simuliamo
// per creare il dataset di training supervisionato

float health_percent = 100.0;        // Stato di salute reale (0-100%)
unsigned long total_operating_hours = 0;  // Ore totali di lavoro simulate
unsigned long start_time = 0;        // Timestamp avvio simulazione

// Fase di vita della macchina (0-100%)
// 0-70%: Usura normale (slope basso)
// 70-90%: Degradazione accelerata (cuscinetti)  
// 90-100%: Failure imminent (possibile catastrofe)
float life_consumed_percent = 0.0;   

// Contatore cicli - FUNGE DA CHIAVE PRIMARIA per correlare i due topic
// Ogni ciclo ha un ID univoco incrementale che identifica la misurazione
unsigned long cycle_count = 0;
const unsigned long CYCLES_PER_HOUR = 720; // Simula 1h ogni 5s (720 cicli = 1h)

// ================= PARAMETRI FISICI BASELINE =================
// Valori nominali di una pompa centrifuga industriale da 5kW
struct Baseline {
  float temp = 42.0;           // °C - temperatura normale cuscinetti
  float current = 8.2;         // A - assorbimento nominale
  float pressure = 4.2;        // Bar - pressione di mandata
  int rpm = 2850;              // RPM - velocità sincrona 2 poli @ 50Hz
  
  // Vibrazioni (mm/s RMS ISO 10816)
  float vib_x = 1.2;           // Asse orizzontale (normalmente più vibrante)
  float vib_y = 0.8;           // Asse verticale  
  float vib_z = 1.0;           // Asse assiale
} baseline;

// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("=== PUMP-001 Phase 1: Data Collection Mode ===");
  Serial.println("CHIAVE PRIMARIA: cycle_count come measurement_id");
  Serial.println("Topic 1: " + String(topic_telemetry) + " (features)");
  Serial.println("Topic 2: " + String(topic_ground_truth) + " (labels)");
  
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setBufferSize(1024);
  start_time = millis();
  randomSeed(analogRead(34)); // Pin floating per entropy
}

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP: " + WiFi.localIP().toString());
}

void reconnect() {
  while (!client.connected()) {
    String clientId = "ESP32-Pump001-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
      Serial.println("MQTT connected");
    } else {
      Serial.print("MQTT fail, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

// ================= SIMULAZIONE DEGRADAZIONE FISICA =================
/*
 * LOGICA DI DEGRADAZIONE:
 * Simula l'usura realistica di una pompa industriale con focus su cuscinetti.
 * La curva di degradazione NON è lineare:
 * - Fase I (0-70%): Usura normale, lenta degradazione
 * - Fase II (70-90%): Pitting su cuscinetti, vibrazioni crescono esponenzialmente
 * - Fase III (90-100%): Failure zone, possibili fenomeni di cavitazione e surriscaldamento
 */
void updateMachineDegradation() {
  cycle_count++;  // INCREMENTA CHIAVE PRIMARIA
  
  // Simula passaggio del tempo: ogni 720 cicli = 1 ora operativa
  if (cycle_count % CYCLES_PER_HOUR == 0) {
    total_operating_hours++;
  }
  
  // Calcola percentuale vita consumata (0-100)
  // Impostiamo vita totale simulata = 7200 cicli = 10 ore simulate
  // In produzione reale sarebbero mesi/anni
  float total_life_cycles = 7200.0; 
  life_consumed_percent = (cycle_count / total_life_cycles) * 100.0;
  
  if (life_consumed_percent > 100.0) life_consumed_percent = 100.0;
  
  // CURVA DI DEGRADAZIONE REALISTICA (Weibull-like semplificata)
  // Health = 100 * (1 - life_consumed)^k dove k varia per simulare bathtub curve
  float degradation_factor;
  if (life_consumed_percent < 70.0) {
    // Fase iniziale: degradazione lenta (burn-in period inverso)
    degradation_factor = pow(life_consumed_percent / 100.0, 1.5);
  } else if (life_consumed_percent < 90.0) {
    // Fase utile: degradazione lineare
    degradation_factor = 0.5 + (life_consumed_percent - 70.0) / 40.0;
  } else {
    // Fase wear-out: degradazione accelerata (cuscinetti collassano)
    degradation_factor = 0.9 + pow((life_consumed_percent - 90.0) / 10.0, 2) * 0.1;
  }
  
  health_percent = 100.0 * (1.0 - degradation_factor);
  if (health_percent < 0) health_percent = 0;
  
  // Simula eventi random di manutenzione che ripristinano parzialmente la salute
  // (opzionale, per avere dati più realistici nel dataset)
  if (random(0, 10000) == 42 && life_consumed_percent > 50) {
    Serial.println(">>> SIMULATED MAINTENANCE EVENT <<<");
    life_consumed_percent *= 0.7; // Ripristina al 70% dello stato attuale
    health_percent = 85.0;
  }
}

// ================= GENERAZIONE DATI SENSORI =================
/*
 * CORRELAZIONI FISICHE:
 * 1. Cuscinetti usurati -> Aumento vibrazioni (soprattutto asse X orizzontale)
 * 2. Attrito aumentato -> Temperatura su (correlazione diretta con vibrazioni)
 * 3. Inefficienza meccanica -> Corrente assorbita maggiore per stesso lavoro
 * 4. Usura girante -> Pressione in calo (non riesce a spingere come prima)
 * 5. RPM controllato, ma con jitter che aumenta con le vibrazioni
 */
void generateSensorData(float &vib_x, float &vib_y, float &vib_z, 
                       float &temp, float &current, float &pressure, 
                       int &rpm, float &vib_rms) {
  
  // Fattore di usura 0.0 (nuovo) a 1.0 (rotto)
  float wear_factor = (100.0 - health_percent) / 100.0;
  
  // 1. VIBRAZIONI (ISO 10816 - velocità RMS mm/s)
  // Baseline + rumore + componente usura (esponenziale!)
  // Quando health < 30%, le vibrazioni esplodono (cuscinetti danneggiati)
  float wear_vibration = pow(wear_factor, 1.8) * 8.0; // Fino a +8 mm/s quando rotto
  
  vib_x = baseline.vib_x + (random(-20, 20) / 100.0) + wear_vibration * 1.2; // Asse orizzontale più colpito
  vib_y = baseline.vib_y + (random(-15, 15) / 100.0) + wear_vibration * 0.8; // Asse verticale
  vib_z = baseline.vib_z + (random(-10, 10) / 100.0) + wear_vibration * 0.5; // Asse assiale meno colpito
  
  // Shock spikes occasionali quando health < 40% (impatti meccanici)
  if (health_percent < 40.0 && random(0, 100) < (40.0 - health_percent)) {
    float shock = random(20, 50) / 10.0; // Spike 2-5 mm/s
    vib_x += shock;
    Serial.println("!!! Mechanical shock detected !!!");
  }
  
  // Calcolo RMS totale (feature importante per ML)
  vib_rms = sqrt(vib_x*vib_x + vib_y*vib_y + vib_z*vib_z);
  
  // 2. TEMPERATURA
  // Legge di aumento: ogni 10% di usura = +3.5°C circa
  // Max 95°C (soglia allarme cuscinetti)
  float temp_rise = wear_factor * 35.0; // Da 42°C a 77°C
  temp = baseline.temp + temp_rise + (random(-5, 5) / 10.0);
  
  // Surriscaldamento rapido in fase critica (>90% usura)
  if (wear_factor > 0.9) {
    temp += random(5, 15); // Picchi termici casuali
  }
  
  // 3. CORRENTE ELETTRICA
  // Aumenta per superare attrito maggiore
  // Legge: +0.4A ogni 10% usura
  float current_rise = wear_factor * 4.0; // Da 8.2A a 12.2A
  current = baseline.current + current_rise + (random(-10, 10) / 100.0);
  
  // 4. PRESSIONE
  // Diminuisce per usura girante/tenute
  // Perdita efficienza idraulica
  float pressure_drop = wear_factor * 1.2; // Da 4.2 Bar a 3.0 Bar
  pressure = baseline.pressure - pressure_drop + (random(-5, 5) / 100.0);
  
  // Fluttuazioni pressione in fase critica (cavitazione)
  if (wear_factor > 0.85) {
    pressure += (random(-20, 0) / 100.0); // Drop improvvisi
  }
  
  // 5. RPM
  // Controllato dal variatore, ma con jitter di controllo che aumenta con carico/vibrazioni
  int rpm_jitter = random(-30, 30) + (int)(wear_factor * 50); // Più instabile quando usurata
  rpm = baseline.rpm + rpm_jitter;
}

// ================= CALCOLO GROUND TRUTH =================
/*
 * DETERMINAZIONE DELLO STATO "REALE" (label per ML):
 * In una pompa reale, lo stato è determinato da ispezioni tecniche o soglie fisiche.
 * Qui applichiamo standard industriali (ISO 10816 per vibrazioni, NEMA per temp)
 * 
 * HEALTHY: Tutti i parametri within specs
 * WARNING: Un parametro sopra soglia di attenzione  
 * CRITICAL: Un parametro sopra soglia di allarme
 * FAILURE: Condizioni estreme che richiederebbero arresto immediato
 */
void calculateGroundTruth(float vib_rms, float temp, float current, String &state, String &failure_mode, int &rul_hours) {
  
  // Soglie fisiche reali (standard industriali)
  const float VIB_WARNING = 4.5;   // mm/s RMS - ISO 10816 limite
  const float VIB_CRITICAL = 7.1;  // mm/s RMS - Stop macchina
  const float TEMP_WARNING = 70.0; // °C
  const float TEMP_CRITICAL = 85.0;// °C - Danneggiamento permanente
  const float CURR_WARNING = 11.0; // A - Sovraccarico 130%
  
  // Logica decisionale a cascata
  if (health_percent <= 5.0 || vib_rms > VIB_CRITICAL || temp > TEMP_CRITICAL) {
    state = "FAILURE";
    failure_mode = (temp > TEMP_CRITICAL) ? "thermal_runaway" : (vib_rms > VIB_CRITICAL) ? "bearing_collapse" : "seizure";
    rul_hours = 0; // RUL = Remaining Useful Life
  }
  else if (health_percent <= 25.0 || vib_rms > VIB_WARNING || temp > TEMP_WARNING || current > CURR_WARNING) {
    state = "CRITICAL";
    failure_mode = (vib_rms > VIB_WARNING) ? "bearing_wear" : (temp > TEMP_WARNING) ? "lubrication_degradation" : "overload";
    rul_hours = (int)((health_percent / 25.0) * 48); // Stima: max 48h rimanenti
  }
  else if (health_percent <= 60.0 || vib_rms > 2.8 || temp > 60.0) {
    state = "WARNING";
    failure_mode = (health_percent < 50) ? "early_wear" : "none";
    rul_hours = (int)(health_percent * 12); // Stima approssimativa ore rimanenti
  }
  else {
    state = "HEALTHY";
    failure_mode = "none";
    rul_hours = 9999; // Indefinito/nuova
  }
}

// ================= LOOP PRINCIPALE =================
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  // Aggiorna lo stato fisico interno della macchina (degradazione)
  // Incrementa anche cycle_count che sarà la nostra chiave primaria
  updateMachineDegradation();
  
  // Genera letture sensori basate sullo stato fisico attuale
  float vib_x, vib_y, vib_z, temp, current, pressure, vib_rms;
  int rpm;
  generateSensorData(vib_x, vib_y, vib_z, temp, current, pressure, rpm, vib_rms);
  
  // Calcola ground truth basato su soglie fisiche (come farebbe un tecnico esperto)
  String actual_state, failure_mode;
  int rul_hours;
  calculateGroundTruth(vib_rms, temp, current, actual_state, failure_mode, rul_hours);
  
  // Recupera timestamp uptime per debug (non per join tra tabelle)
  unsigned long esp_uptime = millis();
  
  // ============== PUBBLICAZIONE TOPIC 1: TELEMETRY (Features X) ==============
  // Questo è ciò che vedrebbe un operatore o un sistema SCADA
  // Il modello ML userà solo questi dati per predire lo stato
  StaticJsonDocument<1024> doc_telemetry;
  
  // CHIAVE PRIMARIA: measurement_id = cycle_count (univoco per ogni iterazione)
  doc_telemetry["measurement_id"] = cycle_count;
  doc_telemetry["esp_uptime"] = esp_uptime;  // Solo per debug/sincronizzazione
  doc_telemetry["device_id"] = "PUMP-001";
  doc_telemetry["operating_hours"] = total_operating_hours;
  
  JsonObject sensors = doc_telemetry.createNestedObject("sensors");
  sensors["vibration_x"] = round(vib_x * 100) / 100.0;
  sensors["vibration_y"] = round(vib_y * 100) / 100.0;
  sensors["vibration_z"] = round(vib_z * 100) / 100.0;
  sensors["vibration_rms"] = round(vib_rms * 100) / 100.0; // Feature engineering pre-calcolata
  sensors["temperature"] = round(temp * 10) / 10.0;
  sensors["current"] = round(current * 100) / 100.0;
  sensors["pressure"] = round(pressure * 100) / 100.0;
  sensors["rpm"] = rpm;
  
  char payload_telemetry[1024];
  serializeJson(doc_telemetry, payload_telemetry);
  // ============== PUBBLICAZIONE TOPIC 2: GROUND TRUTH (Label y) ==============
  // Questo è il "segreto" che useremo per addestrare il ML
  // Nella Fase 3 (produzione), questo topic non esisterà più!
  StaticJsonDocument<1024> doc_truth;
  
  // STESSA CHIAVE PRIMARIA per permettere il join con telemetry
  doc_truth["measurement_id"] = cycle_count;  // Join key con topic_telemetry
  doc_truth["esp_uptime"] = esp_uptime;       // Debug: verifica invio contemporaneo
  doc_truth["device_id"] = "PUMP-001";
  
  // Label per supervised learning
  doc_truth["health_percent"] = round(health_percent * 10) / 10.0; // Ground truth continuo
  doc_truth["rul_hours"] = rul_hours; // Remaining Useful Life (target per regression)
  doc_truth["state"] = actual_state;  // Classe (target per classification)
  doc_truth["failure_mode"] = failure_mode; // Tipo di guasto (multiclass)
  
  // Metadati aggiuntivi per analisi
  doc_truth["life_consumed_pct"] = round(life_consumed_percent * 10) / 10.0;
  
  char payload_truth[1024];
  serializeJson(doc_truth, payload_truth);
  client.publish(topic_telemetry, payload_telemetry);
  delay(100);
  client.publish(topic_ground_truth, payload_truth);
  
  // Debug seriale formattato
  Serial.println("========================================");
  Serial.printf("MID: %d | Cycle: %d | Hours: %d\n", cycle_count, cycle_count, total_operating_hours);
  Serial.printf("Health: %.1f%% | Life: %.1f%% | State: %s\n", health_percent, life_consumed_percent, actual_state.c_str());
  Serial.printf("Sensors -> Vib RMS: %.2f mm/s | Temp: %.1f°C | Curr: %.2fA | Press: %.2fB\n", vib_rms, temp, current, pressure);
  Serial.println("----------------------------------------");
  
  // Frequenza campionamento: ogni 5 secondi
  // In produzione reale sarebbe ogni 1-10 minuti
  delay(5000);
}