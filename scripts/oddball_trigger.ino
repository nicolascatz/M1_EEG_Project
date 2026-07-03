/*
  oddball_trigger.ino
  Reçoit un octet (code de trigger) depuis PsychoPy via USB série,
  et l'encode en binaire sur 3 broches numériques reliées au Cyton
  (D11, D12, D13) pour marquer les événements dans le flux EEG.

  Câblage :
    Arduino D2 -> Cyton D11
    Arduino D3 -> Cyton D12
    Arduino D4 -> Cyton D13
    Arduino GND -> Cyton GND
*/

const int PIN_BIT0 = 2;
const int PIN_BIT1 = 3;
const int PIN_BIT2 = 4;
const unsigned long PULSE_MS = 10;  // doit correspondre à TRIGGER_PULSE_MS côté Python

void setup() {
  pinMode(PIN_BIT0, OUTPUT);
  pinMode(PIN_BIT1, OUTPUT);
  pinMode(PIN_BIT2, OUTPUT);
  digitalWrite(PIN_BIT0, LOW);
  digitalWrite(PIN_BIT1, LOW);
  digitalWrite(PIN_BIT2, LOW);
  Serial.begin(115200);
}

void loop() {
  if (Serial.available() > 0) {
    byte code = Serial.read();  // valeur 0-7 (3 bits)

    digitalWrite(PIN_BIT0, code & 0x01);
    digitalWrite(PIN_BIT1, (code >> 1) & 0x01);
    digitalWrite(PIN_BIT2, (code >> 2) & 0x01);

    delay(PULSE_MS);

    digitalWrite(PIN_BIT0, LOW);
    digitalWrite(PIN_BIT1, LOW);
    digitalWrite(PIN_BIT2, LOW);
  }
}
