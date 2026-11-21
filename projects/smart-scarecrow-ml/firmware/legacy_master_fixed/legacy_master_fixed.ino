// Repaired copy: flash-backed serial strings and honest nominal FFT sample rate.
// Original preserved under firmware/originals/. This sketch still actuates existing servos.
/*
 * Project: Smart Scarecrow - Complete 5-Sensor Master Code
 *          (High-Pass FFT Bird Filter + Anti-Latch Edge-Triggered PIR + Smooth Servos)
 * Hardware Platform: Orangepip Kona328 (ATmega328P / Arduino Uno Compatible)
 * Complete Pin Mapping:
 *   - HC-SR04 Ultrasonic 1: TRIG -> D2,  ECHO -> D3
 *   - HC-SR04 Ultrasonic 2: TRIG -> D12, ECHO -> D13
 *   - PIR Motion Sensor 1:  OUT  -> D4
 *   - PIR Motion Sensor 2:  OUT  -> A0
 *   - Waveshare Sound V2:   DOUT -> D5,  AOUT -> A1 (Analog Waveform for FFT)
 *   - RGB LED (Common -):   R -> D6, G -> D7, B -> D8, GND -> GND
 *   - Servo 2 (Right Arm):  Signal -> D9
 *   - Servo 1 (Left Arm):   Signal -> D10
 *   - Buzzer:               Positive(+) -> D11, Negative(-) -> GND
 */

#include <Servo.h>
#include <arduinoFFT.h>

Servo servo1; // Left arm actuator (D10)
Servo servo2; // Right arm actuator (D9)

// 1. Pin Definitions
const int trigPin1     = 2;   // Ultrasonic 1 TRIG (D2)
const int echoPin1     = 3;   // Ultrasonic 1 ECHO (D3)
const int trigPin2     = 12;  // Ultrasonic 2 TRIG (D12)
const int echoPin2     = 13;  // Ultrasonic 2 ECHO (D13)

const int pirPin1      = 4;   // PIR Motion Sensor 1 OUT (D4)
const int pirPin2      = A0;  // PIR Motion Sensor 2 OUT (A0)
const int soundDoutPin = 5;   // Waveshare Sound V2 DOUT (D5)
const int soundAoutPin = A1;  // Waveshare Sound V2 AOUT (A1)

const int ledRedPin    = 6;   // RGB LED Red (D6)
const int ledGreenPin  = 7;   // RGB LED Green (D7)
const int ledBluePin   = 8;   // RGB LED Blue (D8)
const int servoPin2    = 9;   // Servo 2 Right Arm (D9)
const int servoPin1    = 10;  // Servo 1 Left Arm (D10)
const int buzzerPin    = 11;  // Buzzer Positive (D11)

// 2. FFT Configuration & Bird Frequency Filter (1800 - 4500 Hz)
const uint16_t SAMPLES = 64;
const float SAMPLING_FREQUENCY = 1000000.0f / 104.0f; // 9600 Hz -> Max frequency 4800 Hz (150 Hz per bin)

int16_t rawAdc[SAMPLES];                 // Fast integer buffer for jitter-free sampling
float vReal[SAMPLES];
float vImag[SAMPLES];

ArduinoFFT<float> FFT = ArduinoFFT<float>(vReal, vImag, SAMPLES, SAMPLING_FREQUENCY);

const float BIRD_FREQ_MIN_HZ = 1800.0;   // Lower bound for bird calls (3000 Hz is centered)
const float BIRD_FREQ_MAX_HZ = 4500.0;   // Upper bound for bird calls
float dynamicAmpThreshold    = 40.0;     // Auto-calibrated in setup() above baseline noise

unsigned int samplingPeriodUs;

// 3. Ultrasonic, PIR Anti-Latch & FSM Timing Parameters
const float MIN_DIST_CM = 2.0;
const float MAX_DIST_CM = 50.0;

const unsigned long ALARM_DURATION_MS    = 20000; // 20s alarm lockout duration
const unsigned long COOLDOWN_DURATION_MS = 3000;  // 3s post-alarm cooldown period
const unsigned long SOUND_STABLE_MS      = 500;   // 0.5s continuous quiet check for audio
const unsigned long PIR_DEBOUNCE_MS      = 150;   // 150ms glitch verification for PIR rising edge
const unsigned long PIR_SETTLE_MS        = 2000;  // 2s power-rail settling window after cooldown

// 4. Sensor State Trackers & Lock Flags
int lastPir1State      = LOW;            // Tracks previous PIR 1 state for LOW->HIGH edge detection
int lastPir2State      = LOW;            // Tracks previous PIR 2 state for LOW->HIGH edge detection
bool soundAlarmEnabled = true;           // Independent lock flag for sound channel
unsigned long quietStartTime     = 0;
unsigned long pirSettleStartTime = 0;

// 5. Finite State Machine (FSM) States
enum SystemState {
  STATE_STANDBY,   // Monitor all 5 sensors
  STATE_ALARM,     // 20s alarm lockout
  STATE_COOLDOWN   // 3s cooldown with buzzer OFF
};

SystemState currentState = STATE_STANDBY;
unsigned long stateStartTime = 0;

void setRGB(bool r, bool g, bool b) {
  digitalWrite(ledRedPin,   r ? HIGH : LOW);
  digitalWrite(ledGreenPin, g ? HIGH : LOW);
  digitalWrite(ledBluePin,  b ? HIGH : LOW);
}

// Micro-stepped servo movement to prevent 5V voltage drop and USB port disconnection
void smoothMoveArms(int target1, int target2) {
  int curr1 = servo1.read();
  int curr2 = servo2.read();
  for (int step = 1; step <= 5; step++) {
    servo1.write(curr1 + (target1 - curr1) * step / 5);
    servo2.write(curr2 + (target2 - curr2) * step / 5);
    delay(35);
  }
}

float readUltrasonicDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 15000);
  if (duration == 0) {
    return 999.0;
  }
  return (duration * 0.0343) / 2.0;
}

// High-speed integer sampling + First-Order High-Pass Pre-emphasis FFT
bool detectBirdSoundFFT(float &outPeakFreq, float &outHighFreqAmp) {
  // Pre-read A1 once to settle ADC multiplexer after checking A0
  analogRead(soundAoutPin);
  delayMicroseconds(50);

  // Step A: Integer sampling with nominal 104 us intervals; Servo interrupts add jitter
  for (uint16_t i = 0; i < SAMPLES; i++) {
    unsigned long t0 = micros();
    rawAdc[i] = analogRead(soundAoutPin);
    while ((micros() - t0) < samplingPeriodUs) {
      // Wait for nominal 104 us interval; verify timing on hardware
    }
  }

  // Step B: First-order High-Pass Pre-emphasis (vReal[i] = raw[i] - raw[i-1])
  float maxDiffAmp = 0.0;
  vReal[0] = 0.0;
  vImag[0] = 0.0;
  for (uint16_t i = 1; i < SAMPLES; i++) {
    float diff = (float)(rawAdc[i] - rawAdc[i - 1]);
    vReal[i] = diff;
    vImag[i] = 0.0;
    if (abs(diff) > maxDiffAmp) {
      maxDiffAmp = abs(diff);
    }
  }
  outHighFreqAmp = maxDiffAmp;

  // Step C: Apply Hamming Window & compute 64-point FFT
  FFT.windowing(FFTWindow::Hamming, FFTDirection::Forward);
  FFT.compute(FFTDirection::Forward);
  FFT.complexToMagnitude();

  // Suppress DC and sub-300Hz power supply hum bins
  vReal[0] = 0.0;
  vReal[1] = 0.0;

  // Step D: Extract dominant frequency peak
  outPeakFreq = FFT.majorPeak();

  if (outHighFreqAmp < dynamicAmpThreshold) {
    return false;
  }

  return (outPeakFreq >= BIRD_FREQ_MIN_HZ && outPeakFreq <= BIRD_FREQ_MAX_HZ);
}

void setup() {
  Serial.begin(9600);

  // Set ADC prescaler to 32 (500 kHz ADC clock -> ~28 us analogRead)
  ADCSRA = (ADCSRA & 0xF8) | 0x05;
  samplingPeriodUs = round(1000000.0 / SAMPLING_FREQUENCY);

  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);

  pinMode(pirPin1, INPUT);
  pinMode(pirPin2, INPUT);
  pinMode(soundDoutPin, INPUT);
  pinMode(soundAoutPin, INPUT);

  pinMode(ledRedPin, OUTPUT);
  pinMode(ledGreenPin, OUTPUT);
  pinMode(ledBluePin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  servo1.attach(servoPin1);
  servo2.attach(servoPin2);

  // Default Standby outputs: Arms at 90 deg, Buzzer OFF, Green LED ON
  servo1.write(90);
  servo2.write(90);
  digitalWrite(buzzerPin, LOW);
  setRGB(false, true, false);

  Serial.println(F("=== Smart Scarecrow 5-Sensor Master System Initializing ==="));
  delay(1500); // Allow sensors and 5V rail to stabilize

  // Sample initial PIR states (prevents immediate false alarm if a PIR starts HIGH)
  lastPir1State = digitalRead(pirPin1);
  lastPir2State = digitalRead(pirPin2);
  pirSettleStartTime = millis();

  if (lastPir1State == HIGH) {
    Serial.println(F("[NOTICE] PIR1(D4) is currently HIGH -> Waiting for LOW reset before arming PIR1."));
  }
  if (lastPir2State == HIGH) {
    Serial.println(F("[NOTICE] PIR2(A0) is currently HIGH -> Waiting for LOW reset before arming PIR2."));
  }

  // Auto-calibrate quiet baseline amplitude on A1 over 10 frames
  float maxBaseline = 0.0;
  for (int k = 0; k < 10; k++) {
    float fDummy, ampSample;
    detectBirdSoundFFT(fDummy, ampSample);
    if (ampSample > maxBaseline) maxBaseline = ampSample;
    delay(20);
  }
  dynamicAmpThreshold = maxBaseline + 25.0;

  Serial.print(F("Calibrated Audio Threshold: "));
  Serial.print(dynamicAmpThreshold, 0);
  Serial.println(F(" | Bird Band: 1800 - 4500 Hz"));
}

void loop() {
  unsigned long currentMillis = millis();

  switch (currentState) {

    // -------------------------------------------------------------------------
    // STEP 1, 5 & 6: STANDBY MODE - Monitor 2x Ultrasonic, 2x Edge-PIR, and FFT
    // -------------------------------------------------------------------------
    case STATE_STANDBY: {
      // 1. Read Ultrasonic 1 & 2 (with 15ms cross-talk delay)
      float dist1 = readUltrasonicDistance(trigPin1, echoPin1);
      delay(15);
      float dist2 = readUltrasonicDistance(trigPin2, echoPin2);

      // 2. Read PIR 1 & 2 with Rising-Edge Detection + 150ms Debounce + 2s Power Settling
      int pir1 = digitalRead(pirPin1);
      int pir2 = digitalRead(pirPin2);
      bool pir1Trig = false;
      bool pir2Trig = false;

      if (currentMillis - pirSettleStartTime >= PIR_SETTLE_MS) {
        // Trigger ONLY on fresh LOW -> HIGH edge that stays HIGH for 150ms
        if (pir1 == HIGH && lastPir1State == LOW) {
          delay(PIR_DEBOUNCE_MS);
          if (digitalRead(pirPin1) == HIGH) {
            pir1Trig = true;
          }
        }
        if (pir2 == HIGH && lastPir2State == LOW) {
          delay(PIR_DEBOUNCE_MS);
          if (digitalRead(pirPin2) == HIGH) {
            pir2Trig = true;
          }
        }
      }
      // Update edge trackers (if a PIR is stuck HIGH, lastPirState stays HIGH and won't lock the system)
      lastPir1State = pir1;
      lastPir2State = pir2;

      // 3. Sample Audio from A1 & run FFT Bird Filter
      float peakFreq = 0.0;
      float audioAmp = 0.0;
      bool birdSoundDetected = detectBirdSoundFFT(peakFreq, audioAmp);

      // Step 5: Re-enable sound channel after 500ms of continuous quiet
      if (!soundAlarmEnabled) {
        if (audioAmp >= dynamicAmpThreshold) {
          quietStartTime = currentMillis;
        } else if (currentMillis - quietStartTime >= SOUND_STABLE_MS) {
          soundAlarmEnabled = true;
          Serial.println(F(">>> [Step 5] Acoustic channel quiet & re-enabled!"));
        }
      }

      // Evaluate Ultrasonic and Sound trigger conditions
      bool ultra1Trig = (dist1 >= MIN_DIST_CM && dist1 <= MAX_DIST_CM);
      bool ultra2Trig = (dist2 >= MIN_DIST_CM && dist2 <= MAX_DIST_CM);
      bool soundTrig  = soundAlarmEnabled && birdSoundDetected;

      // Real-time telemetry output
      Serial.print(F("[STANDBY] U1:"));
      if (dist1 > 300.0) Serial.print(F("--")); else Serial.print(dist1, 0);
      Serial.print(F("cm | U2:"));
      if (dist2 > 300.0) Serial.print(F("--")); else Serial.print(dist2, 0);
      Serial.print(F("cm | PIR1:")); Serial.print(pir1 ? "H" : "L");
      Serial.print(F(" | PIR2:"));   Serial.print(pir2 ? "H" : "L");
      Serial.print(F(" | Amp:"));    Serial.print(audioAmp, 0);
      Serial.print(F("/"));          Serial.print(dynamicAmpThreshold, 0);
      Serial.print(F(" | PeakFreq:")); Serial.print(peakFreq, 0);
      Serial.println(F("Hz"));

      if (audioAmp >= dynamicAmpThreshold && !birdSoundDetected) {
        Serial.print(F("   [Noise Rejected] Loud sound at "));
        Serial.print(peakFreq, 0);
        Serial.println(F(" Hz is outside Bird Band (1800-4500 Hz)."));
      }

      // Step 2: Activate 20s alarm if any sensor triggers
      if (ultra1Trig || ultra2Trig || pir1Trig || pir2Trig || soundTrig) {
        Serial.print(F(">>> ALARM TRIGGERED BY: "));
        if (ultra1Trig) Serial.print(F("[Ultrasonic 1 (D2/D3)] "));
        if (ultra2Trig) Serial.print(F("[Ultrasonic 2 (D12/D13)] "));
        if (pir1Trig)   Serial.print(F("[PIR 1 Rising-Edge (D4)] "));
        if (pir2Trig)   Serial.print(F("[PIR 2 Rising-Edge (A0)] "));
        if (soundTrig) {
          Serial.print(F("[Bird Sound FFT (A1): "));
          Serial.print(peakFreq, 0);
          Serial.print(F(" Hz] "));
        }
        Serial.println(F("-> Entering 20s Alarm Lockout!"));

        stateStartTime = millis();
        currentState = STATE_ALARM;
      }
      break;
    }

    // -------------------------------------------------------------------------
    // STEP 2 & 3: ALARM MODE (20s) - Actuate outputs & ignore new triggers
    // -------------------------------------------------------------------------
    case STATE_ALARM: {
      unsigned long elapsed = currentMillis - stateStartTime;

      if (elapsed < ALARM_DURATION_MS) {
        Serial.print(F("[ALARM ACTIVE] Time remaining: "));
        Serial.print((ALARM_DURATION_MS - elapsed) / 1000.0, 1);
        Serial.println(F(" s"));

        // Half-cycle 1: Smooth sweep out + Red LED + Buzzer ON
        setRGB(true, false, false);
        smoothMoveArms(65, 115);         // 175ms smooth motion
        digitalWrite(buzzerPin, HIGH);
        delay(225);

        // Half-cycle 2: Smooth sweep back to 90 deg + Blue LED + Buzzer OFF
        setRGB(false, false, true);
        digitalWrite(buzzerPin, LOW);
        smoothMoveArms(90, 90);          // 175ms smooth motion
        delay(225);
      } 
      else {
        // Step 4: Switch off buzzer and enter 3s Cooldown
        Serial.println(F(">>> 20s Alarm Finished -> Buzzer OFF, entering 3s Cooldown..."));
        digitalWrite(buzzerPin, LOW);
        smoothMoveArms(90, 90);
        setRGB(true, true, false);       // Yellow LED indicates Cooldown

        soundAlarmEnabled = false;       // Lock sound channel until verified quiet
        stateStartTime = millis();
        currentState = STATE_COOLDOWN;
      }
      break;
    }

    // -------------------------------------------------------------------------
    // STEP 4: COOLDOWN MODE (3s) - Buzzer OFF, ignore all triggers
    // -------------------------------------------------------------------------
    case STATE_COOLDOWN: {
      if (currentMillis - stateStartTime >= COOLDOWN_DURATION_MS) {
        Serial.println(F(">>> 3s Cooldown Complete -> Returning to STATE_STANDBY (Green LED)."));
        setRGB(false, true, false);

        // Sync PIR states and start 2s power settling window to prevent self-triggering loops
        lastPir1State = digitalRead(pirPin1);
        lastPir2State = digitalRead(pirPin2);
        pirSettleStartTime = millis();
        quietStartTime     = millis();

        currentState = STATE_STANDBY;
      } else {
        delay(50);
      }
      break;
    }
  }
}



