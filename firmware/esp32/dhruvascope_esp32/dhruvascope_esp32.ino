/* DhruvaScope ESP32 M3 test firmware
 * JSON Lines protocol over Wi-Fi TCP and Bluetooth Classic SPP.
 * Verify every pin and driver enable polarity before powering motors.
 */
#include <Arduino.h>
#include <WiFi.h>
#define ENABLE_BLUETOOTH 0  // Set to 1 after Wi-Fi-only boot is stable.
#define ENABLE_OPTIONAL_MOTORS 1  // Report the configured third driver as FOCUS.
#define WIFI_NETWORK_AP 0
#define WIFI_NETWORK_STA 1
#define WIFI_NETWORK_MODE WIFI_NETWORK_AP  // Change to WIFI_NETWORK_STA to join your router.
#if ENABLE_BLUETOOTH
#include <BluetoothSerial.h>
#endif

// Pin map for the current shared-driver wiring. The first two STEP/DIR pairs
// are RA and DEC; the third pair is reserved for FOCUS/AUX expansion.
#define ENABLE_PIN 25
#define RA_STEP_PIN 26
#define RA_DIR_PIN 27
#define DEC_STEP_PIN 14
#define DEC_DIR_PIN 13
#define FOCUS_STEP_PIN 18
#define FOCUS_DIR_PIN 19
#define AUX1_STEP_PIN 255  // Not wired in the current three-driver setup.
#define AUX1_DIR_PIN 255
#define MICROSTEP_M0_PIN 32
#define MICROSTEP_M1_PIN 33
#define MICROSTEP_M2_PIN 4
#define RA_STEPS_PER_DEGREE 9200.0
#define DEC_STEPS_PER_DEGREE 5866.6667
#define ENABLE_ACTIVE_LEVEL LOW
#define MAX_SPEED_DEG_PER_SECOND 0.1  // Conservative first-test limit; tune after acceleration is added.
#define STEP_PULSE_US 10
#define WIFI_PORT 9999

// AP mode: the ESP32 creates this network.
const char *AP_SSID = "DhruvaScope-ESP32-Test";
const char *AP_PASSWORD = "123456789";
IPAddress AP_IP(192, 168, 4, 1);
IPAddress AP_GATEWAY(192, 168, 4, 1);
IPAddress AP_SUBNET(255, 255, 255, 0);
// STA mode: the ESP32 joins this existing router network.
const char *ROUTER_SSID = "AP-2GHz";
const char *ROUTER_PASSWORD = "************";
const char *BLUETOOTH_NAME = "DhruvaScope-ESP32";

#if ENABLE_BLUETOOTH
BluetoothSerial bluetooth;
#endif
WiFiServer wifiServer(WIFI_PORT);
WiFiClient wifiClient;

struct Channel { const char *id; uint8_t stepPin, dirPin; float stepsPerDegree, speed; bool enabled, moving, positive; unsigned long lastStep; };
Channel channels[] = {
  {"RA", RA_STEP_PIN, RA_DIR_PIN, RA_STEPS_PER_DEGREE, 0, true, false, true, 0},
  {"DEC", DEC_STEP_PIN, DEC_DIR_PIN, DEC_STEPS_PER_DEGREE, 0, true, false, true, 0}
  #if ENABLE_OPTIONAL_MOTORS
  ,
  {"FOCUS", FOCUS_STEP_PIN, FOCUS_DIR_PIN, 1, 0, true, false, true, 0},
  {"AUX1", AUX1_STEP_PIN, AUX1_DIR_PIN, 1, 0, false, false, true, 0},
  {"AUX2", 255, 255, 1, 0, false, false, true, 0}
  #endif
};

String field(const String &line, const String &key) {
  String marker = "\"" + key + "\":"; int start = line.indexOf(marker); if (start < 0) return "";
  start += marker.length(); while (start < (int)line.length() && (line[start] == ' ' || line[start] == '"')) start++;
  bool quoted = start > 0 && line[start - 1] == '"'; int end = start;
  while (end < (int)line.length() && (quoted ? line[end] != '"' : line[end] != ',' && line[end] != '}')) end++;
  return line.substring(start, end);
}

void reply(Stream &out, int id, const String &status, const String &data = "{}", const String &error = "") {
  out.print("{\"v\":1,\"id\":"); out.print(id); out.print(",\"status\":\""); out.print(status); out.print("\"");
  if (status == "OK") { out.print(",\"data\":"); out.print(data); } else { out.print(",\"error\":\""); out.print(error); out.print("\""); }
  out.println("}");
}

Channel *findChannel(const String &id) { for (auto &channel : channels) if (id == channel.id) return &channel; return nullptr; }
void setDriverEnabled(bool enabled) { digitalWrite(ENABLE_PIN, enabled ? ENABLE_ACTIVE_LEVEL : !ENABLE_ACTIVE_LEVEL); }
void stopChannel(Channel *channel) { if (channel) { channel->moving = false; channel->speed = 0; } }
void stopAll() { for (auto &channel : channels) stopChannel(&channel); setDriverEnabled(false); }

String statusJson() {
  String data = "{\"device\":\"DhruvaScope-ESP32\",\"motors\":{";
  const size_t channelCount = sizeof(channels) / sizeof(channels[0]);
  for (size_t i = 0; i < channelCount; i++) { if (i) data += ","; data += "\"" + String(channels[i].id) + "\":{";
    data += "\"available\":" + String(channels[i].stepPin != 255 ? "true" : "false");
    data += ",\"enabled\":" + String(channels[i].enabled ? "true" : "false");
    data += ",\"state\":\"" + String(channels[i].moving ? "MOVING" : (channels[i].enabled ? "IDLE" : "DISABLED")) + "\"";
    data += ",\"speed\":" + String(channels[i].speed, 3) + "}"; }
  return data + "}}";
}

void command(Stream &out, const String &line) {
  int id = field(line, "id").toInt(); String cmd = field(line, "cmd"); String motorId = field(line, "motor");
  if (field(line, "v").toInt() != 1) { reply(out, id, "ERROR", "{}", "BAD_VERSION"); return; }
  if (cmd == "STATUS") { reply(out, id, "OK", statusJson()); return; }
  if (cmd == "STOP") {
    if (motorId == "ALL") { stopAll(); Serial.println("STOP ALL"); }
    else { Channel *c = findChannel(motorId); if (!c) { reply(out, id, "ERROR", "{}", "UNKNOWN_MOTOR"); return; } stopChannel(c); Serial.print("STOP "); Serial.println(motorId); }
    reply(out, id, "OK"); return;
  }
  Channel *channel = findChannel(motorId); if (!channel) { reply(out, id, "ERROR", "{}", "UNKNOWN_MOTOR"); return; }
  if (channel->stepPin == 255) { reply(out, id, "ERROR", "{}", "MOTOR_NOT_WIRED"); return; }
  if (cmd == "ENABLE" || cmd == "DISABLE") { channel->enabled = cmd == "ENABLE"; stopChannel(channel); if (cmd == "DISABLE") setDriverEnabled(false); reply(out, id, "OK"); return; }
  if (cmd == "SET_SPEED" || cmd == "MOVE") { float speed = field(line, "speed").toFloat();
    if (!channel->enabled || speed <= 0 || speed > MAX_SPEED_DEG_PER_SECOND) { reply(out, id, "ERROR", "{}", "INVALID_SPEED_OR_DISABLED"); return; }
    channel->speed = speed;
    if (cmd == "MOVE") {
      setDriverEnabled(true);
      channel->positive = field(line, "direction") == "POS";
      digitalWrite(channel->dirPin, channel->positive ? HIGH : LOW);
      channel->lastStep = micros();
      channel->moving = true;
      Serial.print("MOVE "); Serial.print(channel->id);
      Serial.print(channel->positive ? " POS " : " NEG "); Serial.print(speed, 3);
      Serial.println(" deg/s (continuous until STOP)");
    }
    reply(out, id, "OK"); return; }
  reply(out, id, "ERROR", "{}", "UNKNOWN_COMMAND");
}

void service(Stream &stream, const char *source) {
  static String line;
  while (stream.available()) {
    char c = stream.read();
    if (c == '\n') {
      if (line.length() > 0) {
        Serial.print("[RX "); Serial.print(source); Serial.print("] "); Serial.println(line);
        command(stream, line);
      }
      line = "";
    } else if (c != '\r') {
      line += c;
    }
  }
}

void setup() {
  Serial.begin(115200); delay(250);
  Serial.println(); Serial.println("DhruvaScope ESP32 starting");
  pinMode(ENABLE_PIN, OUTPUT); setDriverEnabled(false);
  // All drivers share these pins. LOW selects full-step mode on DRV8825.
  pinMode(MICROSTEP_M0_PIN, OUTPUT); digitalWrite(MICROSTEP_M0_PIN, LOW);
  pinMode(MICROSTEP_M1_PIN, OUTPUT); digitalWrite(MICROSTEP_M1_PIN, LOW);
  pinMode(MICROSTEP_M2_PIN, OUTPUT); digitalWrite(MICROSTEP_M2_PIN, LOW);
  for (auto &channel : channels) if (channel.stepPin != 255) {
    pinMode(channel.stepPin, OUTPUT); pinMode(channel.dirPin, OUTPUT);
    digitalWrite(channel.stepPin, LOW); digitalWrite(channel.dirPin, HIGH);
  }
  #if ENABLE_BLUETOOTH
  bluetooth.begin(BLUETOOTH_NAME);
  #endif
  #if WIFI_NETWORK_MODE == WIFI_NETWORK_AP
  WiFi.mode(WIFI_AP);
  if (!WiFi.softAPConfig(AP_IP, AP_GATEWAY, AP_SUBNET)) {
    Serial.println("ERROR: Wi-Fi AP address configuration failed");
  }
  if (!WiFi.softAP(AP_SSID, AP_PASSWORD)) {
    Serial.println("ERROR: Wi-Fi AP startup failed");
  } else {
    Serial.print("Wi-Fi AP SSID: "); Serial.println(AP_SSID);
    Serial.print("Wi-Fi AP IP: "); Serial.println(WiFi.softAPIP());
  }
  #else
  WiFi.mode(WIFI_STA); WiFi.begin(ROUTER_SSID, ROUTER_PASSWORD);
  Serial.print("Connecting to router");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) { delay(250); Serial.print('.'); }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) { Serial.print("DhruvaScope router IP: "); Serial.println(WiFi.localIP()); }
  else Serial.println("Router connection failed; check ROUTER_SSID and ROUTER_PASSWORD");
  #endif
  wifiServer.begin();
  Serial.print("TCP command server listening on port "); Serial.println(WIFI_PORT);
}

void loop() {
  if (!wifiClient || !wifiClient.connected()) {
    if (wifiClient) wifiClient.stop();
    WiFiClient incoming = wifiServer.accept();
    if (incoming) {
      wifiClient = incoming;
      Serial.println("TCP client connected");
    }
  }
  if (wifiClient && wifiClient.connected()) service(wifiClient, "WiFi");
  #if ENABLE_BLUETOOTH
  service(bluetooth, "Bluetooth");
  #endif
  unsigned long now = micros(); for (auto &channel : channels) if (channel.moving && channel.speed > 0 && channel.stepPin != 255) {
    unsigned long interval = (unsigned long)(1000000.0 / (channel.speed * channel.stepsPerDegree));
    if (interval < 2) interval = 2;
    if (now - channel.lastStep >= interval) {
      channel.lastStep = now; digitalWrite(channel.stepPin, HIGH);
      delayMicroseconds(STEP_PULSE_US); digitalWrite(channel.stepPin, LOW);
    }
  }
}
