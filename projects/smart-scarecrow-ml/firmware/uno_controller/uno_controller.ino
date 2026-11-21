// Host-classified events -> bounded RGB green LED pulse, actual scarecrow wiring.
// Adapt to the existing scarecrow driver only after checking its circuit/pins.
#include <Arduino.h>
#include <string.h>

const uint8_t OUTPUT_PIN = 7;  // D13 is ECHO2, so NEVER use LED_BUILTIN here.
const unsigned long PULSE_MS = 800, COOLDOWN_MS = 10000, HEARTBEAT_TIMEOUT_MS = 1500;
char command[24];
uint8_t used = 0;
bool active = false, heartbeatSeen = false, fired = false, discardLine = false;
unsigned long lastHeartbeat = 0, lastTrigger = 0;

void stopOutput() { digitalWrite(OUTPUT_PIN, LOW); active = false; }

void handleCommand() {
  unsigned long now = millis();
  if (!strcmp(command, "HEARTBEAT")) {
    heartbeatSeen = true;
    lastHeartbeat = now;
  } else if (!strcmp(command, "STOP")) {
    stopOutput();
  } else if (!strcmp(command, "TRIGGER")) {
    if (heartbeatSeen && now - lastHeartbeat <= HEARTBEAT_TIMEOUT_MS &&
        (!fired || now - lastTrigger >= COOLDOWN_MS)) {
      digitalWrite(OUTPUT_PIN, HIGH);
      active = true; fired = true; lastTrigger = now;
      Serial.println(F("ACK_TRIGGER"));
    }
  }
}

void setup() {
  pinMode(11, OUTPUT); digitalWrite(11, LOW);  // Buzzer off; no servo pulses.
  pinMode(6, OUTPUT); digitalWrite(6, LOW);
  pinMode(8, OUTPUT); digitalWrite(8, LOW);
  pinMode(2, OUTPUT); digitalWrite(2, LOW);
  pinMode(12, OUTPUT); digitalWrite(12, LOW);
  pinMode(OUTPUT_PIN, OUTPUT); stopOutput(); Serial.begin(115200);
}
void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      if (!discardLine) { command[used] = 0; handleCommand(); }
      used = 0; discardLine = false;
    } else if (c != '\r' && !discardLine) {
      if (used < sizeof(command) - 1) command[used++] = c;
      else { discardLine = true; used = 0; stopOutput(); }
    }
  }
  unsigned long now = millis();
  if (active && (now - lastTrigger >= PULSE_MS || now - lastHeartbeat > HEARTBEAT_TIMEOUT_MS)) stopOutput();
}
