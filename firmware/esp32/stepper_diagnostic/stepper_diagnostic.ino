/* DhruvaScope stepper diagnostic
 * Hardware-only test for the current ESP32 Dev Module + DRV8825 wiring.
 * Upload this sketch instead of the network firmware, then use Serial Monitor
 * at 115200 baud. Disconnect motor power before changing wiring.
 * No telescope control or Wi-Fi is used here.
 */

#include <Arduino.h>

// Current shared-driver wiring: STEP/DIR pairs are RA, DEC, FOCUS/AUX.
constexpr uint8_t ENABLE_PIN = 25;       // shared, active LOW
constexpr uint8_t RA_STEP_PIN = 26;
constexpr uint8_t RA_DIR_PIN = 27;
constexpr uint8_t DEC_STEP_PIN = 14;
constexpr uint8_t DEC_DIR_PIN = 13;
constexpr uint8_t FOCUS_STEP_PIN = 18;
constexpr uint8_t FOCUS_DIR_PIN = 19;
constexpr uint8_t MICROSTEP_M0_PIN = 32;
constexpr uint8_t MICROSTEP_M1_PIN = 33;
constexpr uint8_t MICROSTEP_M2_PIN = 4;

constexpr uint16_t TEST_STEPS = 1000;
constexpr uint16_t STEP_HIGH_US = 3;    // DRV8825 minimum is 1.9 us
constexpr uint16_t START_LOW_US = 8000; // start slowly: about 125 steps/s
constexpr uint16_t END_LOW_US = 3000;   // finish at about 333 steps/s

void stepMotor(uint8_t stepPin, uint8_t dirPin, bool positive) {
  digitalWrite(dirPin, positive ? HIGH : LOW);
  delayMicroseconds(20); // allow DIR to settle before STEP
  for (uint16_t i = 0; i < TEST_STEPS; ++i) {
    const uint32_t lowUs = START_LOW_US -
      ((uint32_t)(START_LOW_US - END_LOW_US) * i / TEST_STEPS);
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(STEP_HIGH_US);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(lowUs);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(RA_STEP_PIN, OUTPUT);
  pinMode(RA_DIR_PIN, OUTPUT);
  pinMode(DEC_STEP_PIN, OUTPUT);
  pinMode(DEC_DIR_PIN, OUTPUT);
  pinMode(FOCUS_STEP_PIN, OUTPUT);
  pinMode(FOCUS_DIR_PIN, OUTPUT);
  pinMode(MICROSTEP_M0_PIN, OUTPUT);
  pinMode(MICROSTEP_M1_PIN, OUTPUT);
  pinMode(MICROSTEP_M2_PIN, OUTPUT);

  digitalWrite(RA_STEP_PIN, LOW);
  digitalWrite(DEC_STEP_PIN, LOW);
  digitalWrite(FOCUS_STEP_PIN, LOW);
  digitalWrite(RA_DIR_PIN, HIGH);
  digitalWrite(DEC_DIR_PIN, HIGH);
  digitalWrite(FOCUS_DIR_PIN, HIGH);
  // Shared DRV8825 pins: LOW = full-step mode.
  digitalWrite(MICROSTEP_M0_PIN, LOW);
  digitalWrite(MICROSTEP_M1_PIN, LOW);
  digitalWrite(MICROSTEP_M2_PIN, LOW);
  digitalWrite(ENABLE_PIN, HIGH); // disabled while waiting

  Serial.println("DhruvaScope stepper diagnostic ready");
  Serial.println("Commands: r/R = RA, d/D = DEC, f/F = FOCUS; lowercase/uppercase selects direction; x = disable");
}

void loop() {
  if (!Serial.available()) return;

  const char command = Serial.read();
  if (command == 'x' || command == 'X') {
    digitalWrite(ENABLE_PIN, HIGH);
    Serial.println("Drivers disabled");
  } else if (command == 'r' || command == 'R') {
    digitalWrite(ENABLE_PIN, LOW);
    stepMotor(RA_STEP_PIN, RA_DIR_PIN, command == 'r');
    digitalWrite(ENABLE_PIN, HIGH);
    Serial.println("RA test complete");
  } else if (command == 'd' || command == 'D') {
    digitalWrite(ENABLE_PIN, LOW);
    stepMotor(DEC_STEP_PIN, DEC_DIR_PIN, command == 'd');
    digitalWrite(ENABLE_PIN, HIGH);
    Serial.println("DEC test complete");
  } else if (command == 'f' || command == 'F') {
    digitalWrite(ENABLE_PIN, LOW);
    stepMotor(FOCUS_STEP_PIN, FOCUS_DIR_PIN, command == 'f');
    digitalWrite(ENABLE_PIN, HIGH);
    Serial.println("FOCUS test complete");
  }
}
