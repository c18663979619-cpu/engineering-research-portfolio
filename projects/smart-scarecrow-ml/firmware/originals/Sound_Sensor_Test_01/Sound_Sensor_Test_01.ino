
const int soundPin = A1;

void setup() {
  Serial.begin(115200);

  pinMode(soundPin, INPUT);

  Serial.println("Sound Sensor Test Started");
}

void loop() {

  int minValue = 1023;
  int maxValue = 0;

  unsigned long startTime = millis();

  // Collect samples for 100 milliseconds
  while (millis() - startTime < 100) {

    int value = analogRead(soundPin);

    if (value < minValue) {
      minValue = value;
    }

    if (value > maxValue) {
      maxValue = value;
    }
  }

  int range = maxValue - minValue;

  Serial.print("Min: ");
  Serial.print(minValue);

  Serial.print(" | Max: ");
  Serial.print(maxValue);

  Serial.print(" | Range: ");
  Serial.println(range);

  delay(150);
}
