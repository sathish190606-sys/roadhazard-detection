/**
 * @file main.cpp
 * @brief ESP32 IoT Uplink Gateway for Road Hazard Robot
 * 
 * Functions:
 * 1. Non-blocking UART reader from Raspberry Pi edge computer.
 * 2. Parses newline-delimited JSON commands: HAZARD, TELEMETRY, PING.
 * 3. Immediately acknowledges with {"ack": seq, "status": "OK"}.
 * 4. Primary Uplink: MQTT pub to roadbot/{robot_id}/hazards.
 * 5. Secondary Uplink: HTTP POST fallback to /api/hazards.
 * 6. Ring buffer queue for offline storage during Wi-Fi drops.
 * 7. Periodic 10-second system heartbeat to roadbot/{robot_id}/heartbeat.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #define WIFI_SSID           "RoadBot_WiFi"
  #define WIFI_PASSWORD       "RoadBotPass123"
  #define ROBOT_ID            "robot-01"
  #define ROBOT_API_KEY       "robot-sec-key-771ac-roadbot-edge-2026"
  #define MQTT_BROKER_HOST    "192.168.1.100"
  #define MQTT_BROKER_PORT    1883
  #define MQTT_USERNAME       ""
  #define MQTT_PASSWORD       ""
  #define BACKEND_BASE_URL    "http://192.168.1.100:8000"
  #define HAZARD_ENDPOINT     "/api/hazards"
  #define HEARTBEAT_ENDPOINT  "/api/robots/heartbeat"
#endif

// Pin Definitions
#define STATUS_LED_PIN      2      // Built-in blue LED
#define BATTERY_ADC_PIN     34     // Voltage divider for battery voltage
#define PI_UART_RX_PIN      16     // ESP32 RX2 connected to Pi TX
#define PI_UART_TX_PIN      17     // ESP32 TX2 connected to Pi RX

// Networking & MQTT
WiFiClient espClient;
PubSubClient mqttClient(espClient);
HardwareSerial PiSerial(2);

// Offline Queue Buffer
struct QueuedHazard {
    char payload[1024];
    bool active;
};
#define QUEUE_SIZE 20
QueuedHazard offlineQueue[QUEUE_SIZE];
int queueHead = 0;
int queueTail = 0;

// Timing & Health
unsigned long lastHeartbeatMs = 0;
const unsigned long HEARTBEAT_INTERVAL_MS = 10000;
unsigned long lastWifiRetryMs = 0;
const unsigned long WIFI_RETRY_INTERVAL_MS = 5000;

// String line buffer for UART reading
String inputBuffer = "";

// Forward Declarations
void connectWiFi();
void connectMQTT();
void processIncomingUart();
void handleCommand(const String& jsonStr);
bool publishHazardMQTT(const String& payload);
bool publishHazardHTTP(const String& payload);
void sendHeartbeat();
void enqueueOffline(const String& payload);
void processOfflineQueue();
void sendUartAck(long seq, const char* status);
float readBatteryPercentage();

void setup() {
    // Debug Serial (USB)
    Serial.begin(115200);
    delay(500);
    Serial.println("\n[ESP32] Initializing Road Hazard IoT Gateway...");

    // Raspberry Pi UART Serial (Serial2)
    PiSerial.begin(115200, SERIAL_8N1, PI_UART_RX_PIN, PI_UART_TX_PIN);

    // Status LED
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);

    // Analog ADC
    analogReadResolution(12);

    // Initialize Offline Queue
    for (int i = 0; i < QUEUE_SIZE; i++) {
        offlineQueue[i].active = false;
    }

    // Initialize MQTT
    mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
    mqttClient.setBufferSize(2048);

    // Connect to Wi-Fi
    connectWiFi();
    Serial.println("[ESP32] Gateway initialized and listening for Raspberry Pi messages.");
}

void loop() {
    // 1. Maintain Wi-Fi Connection
    if (WiFi.status() != WL_CONNECTED) {
        if (millis() - lastWifiRetryMs > WIFI_RETRY_INTERVAL_MS) {
            lastWifiRetryMs = millis();
            connectWiFi();
        }
    } else {
        // 2. Maintain MQTT Connection
        if (!mqttClient.connected()) {
            connectMQTT();
        }
        mqttClient.loop();

        // 3. Process any queued offline hazards
        processOfflineQueue();
    }

    // 4. Read UART from Raspberry Pi
    processIncomingUart();

    // 5. Periodic 10-second Telemetry & Heartbeat
    if (millis() - lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatMs = millis();
        sendHeartbeat();
    }
}

void connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.printf("[WIFI] Connecting to SSID: %s\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 15) {
        delay(200);
        digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        digitalWrite(STATUS_LED_PIN, HIGH);
        Serial.println("\n[WIFI] Connected! IP Address: " + WiFi.localIP().toString());
    } else {
        digitalWrite(STATUS_LED_PIN, LOW);
        Serial.println("\n[WIFI] Connection failed. Operating in offline queueing mode.");
    }
}

void connectMQTT() {
    if (mqttClient.connected() || WiFi.status() != WL_CONNECTED) return;

    Serial.print("[MQTT] Connecting to broker...");
    String clientId = "esp32-roadbot-" + String(ROBOT_ID) + "-" + String(random(0xffff), HEX);

    bool ok = false;
    if (strlen(MQTT_USERNAME) > 0) {
        ok = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
    } else {
        ok = mqttClient.connect(clientId.c_str());
    }

    if (ok) {
        Serial.println(" Connected!");
    } else {
        Serial.printf(" Failed (state %d). Will retry.\n", mqttClient.state());
    }
}

void processIncomingUart() {
    // Read from PiSerial first; fall back to USB Serial for manual testing
    HardwareSerial* activeSerial = PiSerial.available() ? &PiSerial : (Serial.available() ? &Serial : nullptr);
    if (!activeSerial) return;

    while (activeSerial->available()) {
        char c = (char)activeSerial->read();
        if (c == '\n' || c == '\r') {
            if (inputBuffer.length() > 0) {
                handleCommand(inputBuffer);
                inputBuffer = "";
            }
        } else {
            if (inputBuffer.length() < 2048) {
                inputBuffer += c;
            }
        }
    }
}

void handleCommand(const String& jsonStr) {
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, jsonStr);
    if (err) {
        Serial.printf("[UART ERR] Invalid JSON: %s\n", err.c_str());
        return;
    }

    long seq = doc["seq"] | 0;
    const char* cmd = doc["cmd"] | "";

    if (strcmp(cmd, "HAZARD") == 0) {
        JsonObject hazardData = doc["data"].as<JsonObject>();
        // Ensure robot_id is present
        if (!hazardData.containsKey("robot_id")) {
            hazardData["robot_id"] = ROBOT_ID;
        }

        String serializedPayload;
        serializeJson(hazardData, serializedPayload);

        Serial.printf("[HAZARD RX] Seq %ld - Dispatching...\n", seq);

        // Attempt Primary: MQTT
        bool success = false;
        if (WiFi.status() == WL_CONNECTED && mqttClient.connected()) {
            success = publishHazardMQTT(serializedPayload);
        }

        // Attempt Secondary: HTTP POST fallback
        if (!success && WiFi.status() == WL_CONNECTED) {
            Serial.println("[UPLINK] MQTT failed/disconnected. Falling back to HTTP REST...");
            success = publishHazardHTTP(serializedPayload);
        }

        // Offline storage if all connections down
        if (!success) {
            Serial.println("[QUEUE] Network unavailable. Enqueueing in local buffer.");
            enqueueOffline(serializedPayload);
            // We still ACK to Pi so Pi knows ESP32 received it safely into non-volatile/RAM queue
            success = true;
        }

        // Return ACK to Pi
        sendUartAck(seq, success ? "OK" : "ERROR");

    } else if (strcmp(cmd, "PING") == 0) {
        sendUartAck(seq, "PONG");
    } else {
        Serial.printf("[UART] Unknown command: %s\n", cmd);
        sendUartAck(seq, "UNKNOWN_CMD");
    }
}

void sendUartAck(long seq, const char* status) {
    JsonDocument ackDoc;
    ackDoc["ack"] = seq;
    ackDoc["status"] = status;
    ackDoc["timestamp"] = millis();

    String ackStr;
    serializeJson(ackDoc, ackStr);
    ackStr += "\n";

    PiSerial.print(ackStr);
    Serial.print(ackStr); // Mirror to debug serial
}

bool publishHazardMQTT(const String& payload) {
    char topic[64];
    snprintf(topic, sizeof(topic), "roadbot/%s/hazards", ROBOT_ID);

    bool res = mqttClient.publish(topic, payload.c_str(), false);
    if (res) {
        Serial.printf("[MQTT TX] Published hazard to %s (%d bytes)\n", topic, payload.length());
    } else {
        Serial.println("[MQTT TX] Publish failed.");
    }
    return res;
}

bool publishHazardHTTP(const String& payload) {
    HTTPClient http;
    String url = String(BACKEND_BASE_URL) + String(HAZARD_ENDPOINT);

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Robot-Key", ROBOT_API_KEY);
    http.setTimeout(3000);

    int httpCode = http.POST(payload);
    bool ok = (httpCode >= 200 && httpCode < 300);
    if (ok) {
        Serial.printf("[HTTP TX] Successfully POSTed hazard (HTTP %d)\n", httpCode);
    } else {
        Serial.printf("[HTTP TX] HTTP POST failed with code %d\n", httpCode);
    }
    http.end();
    return ok;
}

void sendHeartbeat() {
    float battery = readBatteryPercentage();
    int rssi = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -100;
    uint32_t freeHeap = ESP.getFreeHeap();
    unsigned long uptimeSec = millis() / 1000;

    JsonDocument hb;
    hb["robot_id"] = ROBOT_ID;
    hb["battery"] = battery;
    hb["status"] = (battery < 15.0) ? "low_battery" : "patrol";
    hb["wifi_rssi"] = rssi;
    hb["free_heap"] = freeHeap;
    hb["uptime_seconds"] = uptimeSec;
    hb["ip_address"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "0.0.0.0";

    String hbPayload;
    serializeJson(hb, hbPayload);

    // 1. MQTT publication
    if (WiFi.status() == WL_CONNECTED && mqttClient.connected()) {
        char topic[64];
        snprintf(topic, sizeof(topic), "roadbot/%s/heartbeat", ROBOT_ID);
        mqttClient.publish(topic, hbPayload.c_str());
    }

    // 2. HTTP heartbeat fallback if MQTT disconnected
    if (WiFi.status() == WL_CONNECTED && !mqttClient.connected()) {
        HTTPClient http;
        String url = String(BACKEND_BASE_URL) + String(HEARTBEAT_ENDPOINT);
        http.begin(url);
        http.addHeader("Content-Type", "application/json");
        http.addHeader("X-Robot-Key", ROBOT_API_KEY);
        http.setTimeout(1500);
        http.POST(hbPayload);
        http.end();
    }

    Serial.printf("[HEARTBEAT] Sent: Battery=%.1f%%, RSSI=%d dBm, Heap=%u, Uptime=%lus\n",
                  battery, rssi, freeHeap, uptimeSec);
}

float readBatteryPercentage() {
    // Read 12-bit ADC value on GPIO 34 (0-4095)
    // Assuming voltage divider calibrated for 2S or 3S LiPo battery
    int raw = analogRead(BATTERY_ADC_PIN);
    float voltage = (raw / 4095.0) * 3.3 * 4.0; // Example 4:1 divider
    // Clamp 7.0V (0%) to 8.4V (100%) for 2S LiPo
    float pct = ((voltage - 7.0) / 1.4) * 100.0;
    pct = constrain(pct, 5.0, 100.0);
    return round(pct * 10.0) / 10.0;
}

void enqueueOffline(const String& payload) {
    if (offlineQueue[queueHead].active) {
        Serial.println("[QUEUE] Buffer overflow! Overwriting oldest queued hazard.");
        queueTail = (queueTail + 1) % QUEUE_SIZE;
    }
    strncpy(offlineQueue[queueHead].payload, payload.c_str(), sizeof(offlineQueue[queueHead].payload) - 1);
    offlineQueue[queueHead].active = true;
    queueHead = (queueHead + 1) % QUEUE_SIZE;
}

void processOfflineQueue() {
    if (!offlineQueue[queueTail].active) return;
    if (WiFi.status() != WL_CONNECTED) return;

    Serial.printf("[QUEUE] Re-transmitting queued hazard from slot %d...\n", queueTail);
    String payload = String(offlineQueue[queueTail].payload);

    bool ok = false;
    if (mqttClient.connected()) {
        ok = publishHazardMQTT(payload);
    }
    if (!ok) {
        ok = publishHazardHTTP(payload);
    }

    if (ok) {
        offlineQueue[queueTail].active = false;
        queueTail = (queueTail + 1) % QUEUE_SIZE;
        Serial.println("[QUEUE] Successfully synced queued item.");
    }
}
