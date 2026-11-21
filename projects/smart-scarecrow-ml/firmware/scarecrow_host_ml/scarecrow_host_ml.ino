// Complete Kona328 integration using the user's actual 5-sensor pin map.
// Host microphone -> Python ML -> serial TRIGGER; A1/D5 remain sensor telemetry.
// This is NOT concurrent Waveshare PCM streaming. Servo owns Timer1.
// Starts DISARMED: servos detached, buzzer off. ARM requires a recent heartbeat.
#include <Arduino.h>
#include <Servo.h>
#include <string.h>

const uint8_t TRIG1=2, ECHO1=3, PIR1=4, SOUND_DOUT=5;
const uint8_t RED=6, GREEN=7, BLUE=8, RIGHT_ARM=9, LEFT_ARM=10;
const uint8_t BUZZER=11, TRIG2=12, ECHO2=13, PIR2=A0, SOUND_AOUT=A1;
const unsigned long ALARM_MS=20000, COOLDOWN_MS=3000, HEARTBEAT_MS=1500;
Servo leftArm, rightArm;
enum State { STANDBY, ALARM, COOLDOWN };
State state=STANDBY;
bool armed=false, heartbeatSeen=false, hostBird=false, discardLine=false;
char command[24]; uint8_t used=0;
unsigned long heartbeatAt=0, stateAt=0, settleAt=0, servoAt=0, ultraAt=0, logAt=0;
int leftPosition=90, rightPosition=90;
float distance1=999, distance2=999;
bool nextUltra2=false;

struct PirState { uint8_t pin; bool raw; bool stable; unsigned long changedAt; };
PirState p1={PIR1,false,false,0}, p2={PIR2,false,false,0};

void rgb(bool r, bool g, bool b) {
  digitalWrite(RED,r); digitalWrite(GREEN,g); digitalWrite(BLUE,b);
}
void syncPirs(unsigned long now) {
  p1.raw=p1.stable=digitalRead(p1.pin); p1.changedAt=now;
  p2.raw=p2.stable=digitalRead(p2.pin); p2.changedAt=now;
  settleAt=now;
}
bool pirEdge(PirState &p, unsigned long now) {
  bool value=digitalRead(p.pin);
  if (value!=p.raw) { p.raw=value; p.changedAt=now; }
  if (p.stable!=p.raw && now-p.changedAt>=150) {
    p.stable=p.raw;
    return p.stable && now-settleAt>=2000;
  }
  return false;
}
void disarm() {
  armed=false; hostBird=false; state=STANDBY;
  digitalWrite(BUZZER,LOW);
  leftArm.detach(); rightArm.detach();
  rgb(false,false,true);
}
bool heartbeatFresh(unsigned long now) {
  return heartbeatSeen && now-heartbeatAt<=HEARTBEAT_MS;
}
void processCommand() {
  unsigned long now=millis();
  if (!strcmp(command,"HEARTBEAT")) { heartbeatSeen=true; heartbeatAt=now; }
  else if (!strcmp(command,"STOP") || !strcmp(command,"DISARM")) {
    disarm(); Serial.println(F("ACK_DISARMED"));
  } else if (!strcmp(command,"ARM")) {
    if (!armed && heartbeatFresh(now)) {
      leftPosition=rightPosition=90;
      leftArm.write(90); rightArm.write(90);
      leftArm.attach(LEFT_ARM); rightArm.attach(RIGHT_ARM);
      armed=true; state=STANDBY; stateAt=now; syncPirs(now);
      rgb(false,true,false); Serial.println(F("ACK_ARMED"));
    }
  } else if (!strcmp(command,"TRIGGER")) {
    if (armed && heartbeatFresh(now) && state==STANDBY) hostBird=true;
    else Serial.println(F("IGNORED_TRIGGER_NOT_ARMED_OR_BUSY"));
  }
}
void pollSerial() {
  while (Serial.available()) {
    char c=Serial.read();
    if (c=='\n') {
      if (!discardLine) { command[used]=0; processCommand(); }
      used=0; discardLine=false;
    } else if (c!='\r' && !discardLine) {
      if (used<sizeof(command)-1) command[used++]=c;
      else { discardLine=true; used=0; disarm(); }
    }
  }
}
float distanceCm(uint8_t trig, uint8_t echo) {
  digitalWrite(trig,LOW); delayMicroseconds(2);
  digitalWrite(trig,HIGH); delayMicroseconds(10); digitalWrite(trig,LOW);
  unsigned long duration=pulseIn(echo,HIGH,15000);
  return duration ? duration*0.01715f : 999.0f;
}
bool nearObject(float d) { return d>=2 && d<=50; }
void stepArms(int targetLeft,int targetRight,unsigned long now) {
  if (!armed || now-servoAt<20) return;
  servoAt=now;
  if (leftPosition!=targetLeft) leftPosition+=(targetLeft>leftPosition?1:-1);
  if (rightPosition!=targetRight) rightPosition+=(targetRight>rightPosition?1:-1);
  leftArm.write(leftPosition); rightArm.write(rightPosition);
}

void setup() {
  pinMode(TRIG1,OUTPUT); digitalWrite(TRIG1,LOW); pinMode(ECHO1,INPUT);
  pinMode(TRIG2,OUTPUT); digitalWrite(TRIG2,LOW); pinMode(ECHO2,INPUT);
  pinMode(PIR1,INPUT); pinMode(PIR2,INPUT);
  pinMode(SOUND_DOUT,INPUT); pinMode(SOUND_AOUT,INPUT);
  pinMode(RED,OUTPUT); pinMode(GREEN,OUTPUT); pinMode(BLUE,OUTPUT);
  pinMode(BUZZER,OUTPUT); disarm(); syncPirs(millis());
  Serial.begin(115200);
  Serial.println(F("KONA_HOST_ML_V1 DISARMED | AOUT=A1 PIR2=A0 ECHO2=D13"));
}

void loop() {
  pollSerial();
  unsigned long now=millis();
  if (armed && !heartbeatFresh(now)) { disarm(); Serial.println(F("HEARTBEAT_LOST_DISARMED")); }
  bool edge1=pirEdge(p1,now), edge2=pirEdge(p2,now);
  if (state==STANDBY && now-ultraAt>=60) {
    ultraAt=now;
    if (nextUltra2) distance2=distanceCm(TRIG2,ECHO2);
    else distance1=distanceCm(TRIG1,ECHO1);
    nextUltra2=!nextUltra2;
  }
  now=millis();  // pulseIn may have waited; do not use stale timestamps.
  if (state==STANDBY) {
    bool u1=nearObject(distance1), u2=nearObject(distance2);
    if (armed && (u1 || u2 || edge1 || edge2 || hostBird)) {
      Serial.print(F("ALARM_SOURCE "));
      if (u1) Serial.print(F("ULTRA1 "));
      if (u2) Serial.print(F("ULTRA2 "));
      if (edge1) Serial.print(F("PIR1 "));
      if (edge2) Serial.print(F("PIR2 "));
      if (hostBird) Serial.print(F("HOST_ML "));
      Serial.println(); state=ALARM; stateAt=now;
    }
    hostBird=false;
  }
  if (state==ALARM) {
    if (now-stateAt>=ALARM_MS) {
      digitalWrite(BUZZER,LOW); state=COOLDOWN; stateAt=now; rgb(true,true,false);
    } else {
      bool outward=((now-stateAt)/400)%2==0;
      stepArms(outward?65:90,outward?115:90,now);
      digitalWrite(BUZZER,outward?HIGH:LOW); rgb(outward,false,!outward);
    }
  }
  if (state==COOLDOWN) {
    stepArms(90,90,now);
    if (now-stateAt>=COOLDOWN_MS) {
      state=STANDBY; syncPirs(now); distance1=distance2=999;
      hostBird=false; rgb(false,true,false);
    }
  }
  if (now-logAt>=500) {
    logAt=now;
    Serial.print(F("STATE=")); Serial.print((int)state);
    Serial.print(F(" ARMED=")); Serial.print(armed);
    Serial.print(F(" U1=")); Serial.print(distance1,0);
    Serial.print(F(" U2=")); Serial.print(distance2,0);
    Serial.print(F(" PIR=")); Serial.print(p1.stable); Serial.print(p2.stable);
    Serial.print(F(" A1=")); Serial.print(analogRead(SOUND_AOUT));
    Serial.print(F(" D5=")); Serial.println(digitalRead(SOUND_DOUT));
  }
}
