/*
  ============================================================
  BorderPulse ESP32 - Hardware Diagnostic Firmware
  ============================================================

  PURPOSE:
  Test ESP32 + Ground Sensor + Buzzer independently
  before connecting the full BorderPulse backend.

  CURRENT HARDWARE:
    GPIO 25 -> Buzzer
    GPIO 26 -> Ground Sensor Digital Output
    GPIO 27 -> Radar (NOT CONNECTED YET)

  Serial Monitor:
    115200 baud

  HTTP:
    Port 80

  Endpoints:
    GET  /status
    GET  /sensors
    POST /test/buzzer
    POST /alarm
    POST /alarm/stop

  IMPORTANT:
    This firmware assumes the ground sensor is ACTIVE-LOW:
      HIGH = not triggered
      LOW  = triggered

    If your Serial Monitor proves the opposite,
    change GROUND_ACTIVE_LOW to false.
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// ============================================================
// 1. WIFI CONFIGURATION
// ============================================================

const char* WIFI_SSID     = "THOUFIKUR RAHAMAN Y";
const char* WIFI_PASSWORD = "12345678";

// ============================================================
// 2. PIN CONFIGURATION
// ============================================================

const int PIN_BUZZER       = 25;
const int PIN_GROUND_SENSE = 26;
const int PIN_RADAR_OUT    = 27;

// ============================================================
// 3. GROUND SENSOR LOGIC
// ============================================================

// YOUR SENSOR: LOW = idle/off, HIGH = triggered/pressed
// Serial monitor confirmed: RAW=0 means NOT triggered, RAW=1 means TRIGGERED
const bool GROUND_ACTIVE_LOW = false;

// ============================================================
// 4. FIRMWARE INFORMATION
// ============================================================

const char* FIRMWARE_VERSION = "0.1.0-ground-test";

// ============================================================
// 5. WEB SERVER
// ============================================================

WebServer server(80);

// ============================================================
// 6. SYSTEM STATE
// ============================================================

bool alarmActive = false;

unsigned long alarmEndTime = 0;

String alarmReason = "";

// ============================================================
// 7. HELPER - SEND JSON
// ============================================================

void sendJSON(int code, String body) {

  server.sendHeader(
    "Access-Control-Allow-Origin",
    "*"
  );

  server.sendHeader(
    "Access-Control-Allow-Methods",
    "GET, POST, OPTIONS"
  );

  server.sendHeader(
    "Access-Control-Allow-Headers",
    "Content-Type"
  );

  server.send(
    code,
    "application/json",
    body
  );
}

// ============================================================
// 8. READ GROUND SENSOR
// ============================================================

bool readGroundSensor() {

  int rawPin = digitalRead(PIN_GROUND_SENSE);

  bool triggered;

  if (GROUND_ACTIVE_LOW) {

    triggered = (rawPin == LOW);

  } else {

    triggered = (rawPin == HIGH);
  }

  return triggered;
}

// ============================================================
// 9. PRINT GROUND SENSOR STATUS
// ============================================================

void printGroundSensorStatus() {

  int rawPin = digitalRead(PIN_GROUND_SENSE);

  bool triggered = readGroundSensor();

  Serial.println();
  Serial.println("========================================");

  Serial.println("[GROUND SENSOR TEST]");

  Serial.printf(
    "GPIO: %d\n",
    PIN_GROUND_SENSE
  );

  Serial.printf(
    "RAW GPIO VALUE: %d\n",
    rawPin
  );

  if (rawPin == HIGH) {

    Serial.println(
      "GPIO STATE: HIGH"
    );

  } else {

    Serial.println(
      "GPIO STATE: LOW"
    );
  }

  Serial.printf(
    "GROUND SENSOR: %s\n",
    triggered ? "TRIGGERED" : "NOT TRIGGERED"
  );

  Serial.printf(
    "LOGIC MODE: %s\n",
    GROUND_ACTIVE_LOW
      ? "ACTIVE-LOW"
      : "ACTIVE-HIGH"
  );

  Serial.println("========================================");
}

// ============================================================
// 10. STATUS ENDPOINT
// ============================================================

void handleStatus() {

  StaticJsonDocument<512> doc;

  doc["device"] = "ESP32-BorderPulse";

  doc["firmware"] = FIRMWARE_VERSION;

  doc["ip"] =
    WiFi.localIP().toString();

  doc["rssi"] =
    WiFi.RSSI();

  doc["uptime_ms"] =
    millis();

  doc["wifi_connected"] =
    WiFi.status() == WL_CONNECTED;

  doc["buzzer_active"] =
    alarmActive;

  doc["pins"]["buzzer"] =
    PIN_BUZZER;

  doc["pins"]["ground"] =
    PIN_GROUND_SENSE;

  doc["pins"]["radar"] =
    PIN_RADAR_OUT;

  doc["sensors"]["ground"]["mode"] =
    "REAL";

  doc["sensors"]["radar"]["mode"] =
    "NOT_CONNECTED";

  String output;

  serializeJson(
    doc,
    output
  );

  sendJSON(
    200,
    output
  );

  Serial.println();
  Serial.println("[HTTP] GET /status");
}

// ============================================================
// 11. SENSOR ENDPOINT
// ============================================================

void handleGetSensors() {

  int rawGround =
    digitalRead(PIN_GROUND_SENSE);

  bool groundTriggered =
    readGroundSensor();

  Serial.println();
  Serial.println("[HTTP] GET /sensors");

  Serial.printf(
    "[GROUND] GPIO %d RAW = %d\n",
    PIN_GROUND_SENSE,
    rawGround
  );

  Serial.printf(
    "[GROUND] TRIGGERED = %s\n",
    groundTriggered
      ? "YES"
      : "NO"
  );

  StaticJsonDocument<512> doc;

  // Radar is not connected yet
  doc["radar"]["triggered"] =
    false;

  doc["radar"]["mode"] =
    "NOT_CONNECTED";

  // Real ground sensor
  doc["ground"]["triggered"] =
    groundTriggered;

  doc["ground"]["mode"] =
    "REAL";

  doc["ground"]["gpio"] =
    PIN_GROUND_SENSE;

  doc["ground"]["raw"] =
    rawGround;

  doc["ground"]["logic"] =
    GROUND_ACTIVE_LOW
      ? "ACTIVE_LOW"
      : "ACTIVE_HIGH";

  doc["wifi"]["ip"] =
    WiFi.localIP().toString();

  String output;

  serializeJson(
    doc,
    output
  );

  sendJSON(
    200,
    output
  );
}

// ============================================================
// 12. BUZZER TEST
// ============================================================

void handleTestBuzzer() {

  Serial.println();
  Serial.println("========================================");
  Serial.println("[BUZZER TEST] START");
  Serial.println("========================================");

  // First beep
  Serial.println("[BUZZER] ON");

  digitalWrite(
    PIN_BUZZER,
    HIGH
  );

  delay(500);

  Serial.println("[BUZZER] OFF");

  digitalWrite(
    PIN_BUZZER,
    LOW
  );

  delay(250);

  // Second beep
  Serial.println("[BUZZER] ON");

  digitalWrite(
    PIN_BUZZER,
    HIGH
  );

  delay(500);

  Serial.println("[BUZZER] OFF");

  digitalWrite(
    PIN_BUZZER,
    LOW
  );

  Serial.println("[BUZZER TEST] COMPLETE");

  StaticJsonDocument<256> doc;

  doc["success"] =
    true;

  doc["message"] =
    "Buzzer test complete";

  doc["gpio"] =
    PIN_BUZZER;

  String output;

  serializeJson(
    doc,
    output
  );

  sendJSON(
    200,
    output
  );
}

// ============================================================
// 13. ALARM ON/OFF
// ============================================================

void handleAlarm() {

  if (server.method() != HTTP_POST) {

    sendJSON(
      405,
      "{\"success\":false,\"error\":\"POST required\"}"
    );

    return;
  }

  StaticJsonDocument<512> doc;

  DeserializationError error =
    deserializeJson(
      doc,
      server.arg("plain")
    );

  if (error) {

    Serial.println(
      "[ALARM] Invalid JSON"
    );

    sendJSON(
      400,
      "{\"success\":false,\"error\":\"Invalid JSON\"}"
    );

    return;
  }

  bool active =
    doc["active"] | false;

  int duration =
    doc["duration_ms"] | 3000;

  alarmReason =
    doc["reason"] | "unknown";

  if (active) {

    alarmActive = true;

    alarmEndTime =
      millis() + duration;

    digitalWrite(
      PIN_BUZZER,
      HIGH
    );

    Serial.println();
    Serial.println("========================================");

    Serial.println("[ALARM] ACTIVATED");

    Serial.printf(
      "[ALARM] Reason: %s\n",
      alarmReason.c_str()
    );

    Serial.printf(
      "[ALARM] Duration: %d ms\n",
      duration
    );

    Serial.println(
      "[ALARM] GPIO25 = HIGH"
    );

    Serial.println("========================================");

  } else {

    alarmActive = false;

    digitalWrite(
      PIN_BUZZER,
      LOW
    );

    Serial.println(
      "[ALARM] DEACTIVATED"
    );
  }

  StaticJsonDocument<256> response;

  response["success"] =
    true;

  response["alarm_active"] =
    alarmActive;

  response["reason"] =
    alarmReason;

  String output;

  serializeJson(
    response,
    output
  );

  sendJSON(
    200,
    output
  );
}

// ============================================================
// 14. STOP ALARM
// ============================================================

void handleAlarmStop() {

  alarmActive = false;

  digitalWrite(
    PIN_BUZZER,
    LOW
  );

  Serial.println(
    "[ALARM] STOPPED"
  );

  sendJSON(
    200,
    "{\"success\":true,\"alarm_active\":false}"
  );
}

// ============================================================
// 15. AUTO ALARM TIMEOUT
// ============================================================

void checkAlarmTimeout() {

  if (
    alarmActive &&
    millis() >= alarmEndTime
  ) {

    alarmActive = false;

    digitalWrite(
      PIN_BUZZER,
      LOW
    );

    Serial.println(
      "[ALARM] AUTO TIMEOUT -> BUZZER OFF"
    );
  }
}

// ============================================================
// 16. CORS
// ============================================================

void handleCORS() {

  server.sendHeader(
    "Access-Control-Allow-Origin",
    "*"
  );

  server.sendHeader(
    "Access-Control-Allow-Methods",
    "GET, POST, OPTIONS"
  );

  server.sendHeader(
    "Access-Control-Allow-Headers",
    "Content-Type"
  );

  server.send(
    204
  );
}

// ============================================================
// 17. WIFI CONNECTION
// ============================================================

void connectWiFi() {

  Serial.println();
  Serial.println("========================================");
  Serial.println("[WIFI] CONNECTING");
  Serial.println("========================================");

  Serial.printf(
    "SSID: %s\n",
    WIFI_SSID
  );

  WiFi.mode(
    WIFI_STA
  );

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD
  );

  int attempts = 0;

  while (
    WiFi.status() != WL_CONNECTED &&
    attempts < 40
  ) {

    delay(500);

    Serial.print(".");

    attempts++;
  }

  Serial.println();

  if (
    WiFi.status() == WL_CONNECTED
  ) {

    Serial.println(
      "[WIFI] CONNECTED"
    );

    Serial.print(
      "[WIFI] IP ADDRESS: "
    );

    Serial.println(
      WiFi.localIP()
    );

    Serial.print(
      "[WIFI] RSSI: "
    );

    Serial.println(
      WiFi.RSSI()
    );

  } else {

    Serial.println(
      "[WIFI] CONNECTION FAILED"
    );
  }
}

// ============================================================
// 18. SETUP
// ============================================================

void setup() {

  Serial.begin(
    115200
  );

  delay(1000);

  Serial.println();
  Serial.println();
  Serial.println("========================================");
  Serial.println("     BorderPulse ESP32");
  Serial.println("     HARDWARE TEST FIRMWARE");
  Serial.println("========================================");

  // ----------------------------------------------------------
  // PIN SETUP
  // ----------------------------------------------------------

  pinMode(
    PIN_BUZZER,
    OUTPUT
  );

  digitalWrite(
    PIN_BUZZER,
    LOW
  );

  pinMode(
    PIN_GROUND_SENSE,
    INPUT_PULLUP
  );

  // Radar is NOT connected.
  // Do not use GPIO27 yet.

  Serial.println();
  Serial.println("[PINS]");

  Serial.printf(
    "Buzzer       : GPIO %d\n",
    PIN_BUZZER
  );

  Serial.printf(
    "Ground       : GPIO %d\n",
    PIN_GROUND_SENSE
  );

  Serial.printf(
    "Radar        : GPIO %d (NOT CONNECTED)\n",
    PIN_RADAR_OUT
  );

  Serial.printf(
    "Ground Logic : %s\n",
    GROUND_ACTIVE_LOW
      ? "ACTIVE-LOW"
      : "ACTIVE-HIGH"
  );

  // ----------------------------------------------------------
  // INITIAL GROUND READING
  // ----------------------------------------------------------

  Serial.println();
  Serial.println(
    "[GROUND] Initial reading:"
  );

  printGroundSensorStatus();

  // ----------------------------------------------------------
  // WIFI
  // ----------------------------------------------------------

  connectWiFi();

  // ----------------------------------------------------------
  // HTTP ROUTES
  // ----------------------------------------------------------

  server.on(
    "/status",
    HTTP_GET,
    handleStatus
  );

  server.on(
    "/sensors",
    HTTP_GET,
    handleGetSensors
  );

  server.on(
    "/test/buzzer",
    HTTP_POST,
    handleTestBuzzer
  );

  server.on(
    "/alarm",
    HTTP_POST,
    handleAlarm
  );

  server.on(
    "/alarm/stop",
    HTTP_POST,
    handleAlarmStop
  );

  server.on(
    "/alarm",
    HTTP_OPTIONS,
    handleCORS
  );

  server.on(
    "/alarm/stop",
    HTTP_OPTIONS,
    handleCORS
  );

  server.on(
    "/test/buzzer",
    HTTP_OPTIONS,
    handleCORS
  );

  // ----------------------------------------------------------
  // START HTTP SERVER
  // ----------------------------------------------------------

  server.begin();

  Serial.println();
  Serial.println(
    "[HTTP] SERVER STARTED"
  );

  Serial.println(
    "[HTTP] PORT: 80"
  );

  // ----------------------------------------------------------
  // STARTUP INFORMATION
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("========================================");

  Serial.printf(
    "Firmware: %s\n",
    FIRMWARE_VERSION
  );

  if (
    WiFi.status() == WL_CONNECTED
  ) {

    Serial.print(
      "ESP32 URL: http://"
    );

    Serial.print(
      WiFi.localIP()
    );

    Serial.println(
      "/"
    );
  }

  Serial.println();
  Serial.println("Available endpoints:");

  Serial.println(
    "GET  /status"
  );

  Serial.println(
    "GET  /sensors"
  );

  Serial.println(
    "POST /test/buzzer"
  );

  Serial.println(
    "POST /alarm"
  );

  Serial.println(
    "POST /alarm/stop"
  );

  Serial.println("========================================");

  // ----------------------------------------------------------
  // STARTUP BUZZER
  // ----------------------------------------------------------

  Serial.println(
    "[BUZZER] Startup test"
  );

  digitalWrite(
    PIN_BUZZER,
    HIGH
  );

  delay(100);

  digitalWrite(
    PIN_BUZZER,
    LOW
  );

  Serial.println(
    "[SYSTEM] READY"
  );

  Serial.println();
  Serial.println(
    "Now trigger the ground sensor."
  );

  Serial.println(
    "GPIO26 state will be printed every 500 ms."
  );

  Serial.println();
}

// ============================================================
// 19. LOOP
// ============================================================

void loop() {

  // Handle HTTP requests
  server.handleClient();

  // Check alarm timeout
  checkAlarmTimeout();

  // ----------------------------------------------------------
  // CONTINUOUS GROUND SENSOR MONITORING
  // ----------------------------------------------------------

  static unsigned long lastSensorPrint = 0;

  if (
    millis() - lastSensorPrint >= 500
  ) {

    lastSensorPrint =
      millis();

    int rawPin =
      digitalRead(
        PIN_GROUND_SENSE
      );

    bool triggered =
      readGroundSensor();

    Serial.printf(
      "[GROUND] GPIO26 RAW=%d | TRIGGERED=%s\n",
      rawPin,
      triggered
        ? "YES"
        : "NO"
    );
  }

  delay(10);
}