

const int pinTrigger = 10;
const int pinStartButton = 3;

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
int startButtonState = 0;

void setup() {

  pinMode(pinTrigger, OUTPUT);
  pinMode(pinStartButton, INPUT); 

  Serial.begin(9600);
}

void loop() {

  // read the state of the START pushbutton value:
  startButtonState = digitalRead(pinStartButton);

  // check if the pushbutton is pressed ie the buttonState is HIGH:
  if (startButtonState == HIGH) {
    
    delay(5000); // 5 seconds delay
    
    for (int trial = 0; trial < intTrials; trial++) {
      
      // trigger sent to openbci and board buzzer
      digitalWrite(pinTrigger, HIGH);
      delay(6);

      // intervalle inter-stimulus jitté (évite l'anticipation)
      digitalWrite(pinTrigger, LOW);
      int isi = random(isiMin, isiMax);
      delay(isi);

      //Serial.println(digitalRead(pinTrigger));
  
    }
  }
}
