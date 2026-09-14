

const int pinSpeaker = 9;
const int pinTrigger = 7;

// Define the number of trials
int intTrials = 120;

// Define the sound duration
int soundDuration = 250; // ms
int soundFreq = 4000; // Hz

// with clic
int dureeClic = 2; // ms

// Define the interval duration
int intDuration = 1000; // ms
int isiMin = 800;      // ms — ISI minimum
int isiMax = 1200;     // ms — ISI maximum

// variable will change
int triggerState = 0;

void setup() {

  pinMode(pinTrigger, INPUT); 

  randomSeed(analogRead(A0));  // graine aléatoire pour le jitter

  Serial.begin(9600);
}

void loop() {

  // read the state of the ttl input:
  triggerState = digitalRead(pinTrigger);

  Serial.println(digitalRead(pinTrigger));

  // check if the ttl input is HIGH:
  if (triggerState == HIGH) {
    
    // son pur déclenchement simultané du son et du trigger de synchronisation
    //digitalWrite(pinTrigger, HIGH);
    //tone(pinSpeaker, soundFreq);    
    //delay(soundDuration);
    
    // bruit blanc déclenchement simultané du son et du trigger
    unsigned long startTime = millis();
    while (millis() - startTime < soundDuration) {
      tone(pinSpeaker, random(100, soundFreq));
      delay(5);
    }

    // clic déclenchement simultané du son et du trigger
    //tone(pinSpeaker, soundFreq, dureeClic);
    //delay(5);

    // turn off speaker
    noTone(pinSpeaker);
  
  }
}
