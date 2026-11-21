
const int soundPin = A1;

// Number of audio samples
const int SAMPLE_COUNT = 256;

// Sampling interval: 104 microseconds
// Approximately 9600 samples per second
const unsigned long SAMPLE_INTERVAL = 104;

// Buffer for storing audio data
int samples[SAMPLE_COUNT];

void setup() {

  Serial.begin(115200);

  pinMode(soundPin, INPUT);

  // Faster ADC sampling for ATmega328P
  ADCSRA = (ADCSRA & 0xF8) | 0x05;

  analogRead(soundPin);
}

void loop() {

  // Record starting time
  unsigned long startTime = micros();

  // Step 1: Collect 256 samples
  for (int i = 0; i < SAMPLE_COUNT; i++) {

    while (micros() - startTime <
           (unsigned long)i * SAMPLE_INTERVAL) {
      // Wait until next sampling time
    }

    samples[i] = analogRead(soundPin);
  }

  // Step 2: Send samples to computer
  for (int i = 0; i < SAMPLE_COUNT; i++) {

    Serial.print("Audio:");
    Serial.println(samples[i]);
  }

  // Pause before the next collection
  delay(500);
}
