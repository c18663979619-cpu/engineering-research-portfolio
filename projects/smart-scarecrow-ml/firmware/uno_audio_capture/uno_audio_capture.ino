// Kona328 / 16 MHz UNO. Continuous A1 ADC, 8 kHz nominal, SCM1 binary.
// Standalone acquisition sketch: Timer1 is reserved; do not combine with Servo.
#include <Arduino.h>
#include <util/atomic.h>

static_assert(F_CPU == 16000000UL, "SCM1 timer configuration requires 16 MHz");
volatile uint16_t ring[512];  // 1024 bytes; one slot always unused.
volatile uint16_t head = 0, tail = 0, dropped = 0;
volatile bool discardFirst = true;
uint32_t sequence = 0;

ISR(ADC_vect) {
  uint16_t value = ADC;
  TIFR1 = _BV(OCF1B);  // Re-arm the compare-B trigger edge.
  if (discardFirst) { discardFirst = false; return; }
  uint16_t next = (head + 1) & 511;
  if (next == tail) {
    if (dropped != 65535) ++dropped;
  } else {
    ring[head] = value;
    head = next;
  }
}

uint16_t crc = 0xffff;
void emitByte(uint8_t value) {
  crc ^= (uint16_t)value << 8;
  for (uint8_t i = 0; i < 8; ++i)
    crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  Serial.write(value);
}
void emit16(uint16_t value) { emitByte(value & 255); emitByte(value >> 8); }
void emit32(uint32_t value) { emit16(value & 65535); emit16(value >> 16); }

void setup() {
  // Actual scarecrow wiring: A0 is PIR2; D13 is ultrasonic ECHO2.
  // No Servo library in this mode; pins D9/D10 remain inputs (no servo pulses).
  pinMode(2, OUTPUT); digitalWrite(2, LOW);
  pinMode(12, OUTPUT); digitalWrite(12, LOW);
  pinMode(11, OUTPUT); digitalWrite(11, LOW);  // Buzzer off.
  pinMode(6, OUTPUT); digitalWrite(6, LOW);
  pinMode(7, OUTPUT); digitalWrite(7, HIGH);
  pinMode(8, OUTPUT); digitalWrite(8, LOW);
  Serial.begin(250000);  // Exact divisor at 16 MHz; 25,000 payload bytes/s at 8N1.
  cli();
  ADMUX = _BV(REFS0) | 1;  // AVcc reference, ADC1/A1 (Waveshare AOUT).
  DIDR0 |= _BV(ADC1D);  // Keep A0 digital input working for PIR2.
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  OCR1A = 249;  // 16 MHz / 8 / 250 = 8000 Hz.
  OCR1B = 249;
  ADCSRB = _BV(ADTS2) | _BV(ADTS0);  // Timer1 compare B auto trigger.
  // Warm up ADC synchronously: first conversion takes longer than steady state.
  ADCSRA = _BV(ADEN) | _BV(ADPS2) | _BV(ADPS1) | _BV(ADPS0);
  ADCSRA |= _BV(ADSC);
  while (ADCSRA & _BV(ADSC)) {}
  ADCSRA |= _BV(ADIF);  // Clear pending flag before enabling interrupt.
  ADCSRA |= _BV(ADATE) | _BV(ADIE) | _BV(ADSC);
  TIFR1 = _BV(OCF1B);
  TCCR1B = _BV(WGM12) | _BV(CS11);  // CTC / prescaler 8.
  sei();
}

void loop() {
  uint16_t available, lost;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    available = (head - tail) & 511;
    lost = dropped;
  }
  if (available < 256) return;
  crc = 0xffff;
  emitByte('S'); emitByte('C'); emitByte('M'); emitByte('1');
  emit32(sequence++); emit16(8000); emit16(256); emit16(lost);
  for (uint16_t i = 0; i < 256; ++i) {
    uint16_t value;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
      value = ring[tail];
      tail = (tail + 1) & 511;
    }
    emit16(value);
  }
  uint16_t checksum = crc;
  Serial.write(checksum & 255); Serial.write(checksum >> 8);
}
