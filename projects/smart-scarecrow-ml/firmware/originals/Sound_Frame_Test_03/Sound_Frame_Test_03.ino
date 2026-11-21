
const int soundPin = A1;

const int SAMPLE_COUNT = 256;
const unsigned long SAMPLE_INTERVAL = 104;

int samples[SAMPLE_COUNT];

unsigned long frameID = 0;

void setup() {

  Serial.begin(115200);

  pinMode(soundPin, INPUT);

  // Configure faster ADC sampling
  ADCSRA = (ADCSRA & 0xF8) | 0x05;

  analogRead(soundPin);
}

void loop() {

  // Step 1: Collect 256 audio samples
  unsigned long nextSampleTime = micros();

  for (int i = 0; i < SAMPLE_COUNT; i++) {

    while ((long)(micros() - nextSampleTime) < 0) {
      // Wait until the next sample
    }

    samples[i] = analogRead(soundPin);

    nextSampleTime += SAMPLE_INTERVAL;
  }

  // Step 2: Mark the beginning of the frame
  Serial.print("FRAME_START,");
  Serial.print(frameID);
  Serial.print(",");
  Serial.println(SAMPLE_COUNT);

  // Step 3: Send all samples
  for (int i = 0; i < SAMPLE_COUNT; i++) {

    Serial.print("Audio:");
    Serial.println(samples[i]);
  }

  // Step 4: Mark the end of the frame
  Serial.print("FRAME_END,");
  Serial.println(frameID);

  // Step 5: Prepare next frame
  frameID++;

  delay(300);
}
