#include <Servo.h>
#include <Adafruit_NeoPixel.h>

// ------------------------
// CONFIGURAÇÃO DA FITA LED
// ------------------------
#define LED_PIN 3
#define LED_PIN2 13
#define NUM_LEDS 30

#include <Adafruit_NeoPixel.h> 

Adafruit_NeoPixel strip1(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2(NUM_LEDS, LED_PIN2, NEO_GRB + NEO_KHZ800);

// ------------------------
// CONFIGURAÇÃO DOS BOTÕES
// ------------------------
const int vermelho = 2;
const int amarelo  = 4;
const int azul     = 6;
const int verde    = 8;

int led  = 1;
int led2 = 12;
int led3 = 7;
int led4 = 5;


// ------------------------
// CONFIGURAÇÃO DOS SERVOS
// ------------------------
Servo servo1;
Servo servo2;
Servo servo3;

String comando = "";

// ------------------------
// FUNÇÃO DO EFEITO COBRINHA COM RASTRO
// ------------------------
void efeitoCobraverde() {
  for (int i = 0; i < NUM_LEDS; i++) {
    strip1.clear(); 
    strip2.clear(); 
    for (int j = 0; j < 5; j++) {
      int idx = i - j;
      if (idx >= 0) {
        strip1.setPixelColor(idx, strip1.Color(0, 255, 0));
        strip2.setPixelColor(idx, strip2.Color(0, 255, 0));
      }
    }
    strip1.show();
    strip2.show();
    delay(50);
  }
}

void efeitoCobravermelho(){
  for (int i = 0; i < NUM_LEDS; i++) {
    strip1.clear();
    strip2.clear();  
    for (int j = 0; j < 5; j++) {
      int idx = i - j;
      if (idx >= 0) {
        strip1.setPixelColor(idx, strip1.Color(255, 0, 0));
        strip2.setPixelColor(idx, strip2.Color(255, 0, 0));
      }
    }
    strip1.show();
    strip2.show();
    delay(50);
  }
}

void setup() {
  // Botões
  pinMode(vermelho, INPUT_PULLUP);
  pinMode(amarelo, INPUT_PULLUP);
  pinMode(azul, INPUT_PULLUP);
  pinMode(verde, INPUT_PULLUP);

  // LEDs
  pinMode(led, OUTPUT);
  pinMode(led2, OUTPUT);
  pinMode(led3, OUTPUT);
  pinMode(led4, OUTPUT);
  

  // Servos
  servo1.attach(9);
  servo2.attach(10);
  servo3.attach(11);

  servo1.write(90);
  servo2.write(90);
  servo3.write(90);

  strip1.begin();
  strip1.show();
  strip2.begin();
  strip2.show(); // inicia apagado

  Serial.begin(9600);
  randomSeed(analogRead(A0));
}

void loop() {
  // Mantém todos os LEDs ligados
  digitalWrite(led, HIGH);
  digitalWrite(led2, HIGH);
  digitalWrite(led3, HIGH);
  digitalWrite(led4, HIGH);
  

  // Leitura dos botões
  if (digitalRead(vermelho) == LOW) {
    Serial.println("BTN1");
    delay(300);
  }
  else if (digitalRead(amarelo) == LOW) {
    Serial.println("BTN2");
    delay(300);
  }
  else if (digitalRead(azul) == LOW) {
    Serial.println("BTN3");
    delay(300);
  }
  else if (digitalRead(verde) == LOW) {
    Serial.println("BTN4");
    delay(300);
  }

  // Recebe comandos via Serial
  if (Serial.available()) {
    comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "ACERTOU") {
      Serial.println("ACERTOU");
      servo1.write(0);
      servo2.write(180);
      efeitoCobraverde();
      delay(500);
      servo1.write(90);
      servo2.write(90);
    }
    if (comando == "ERROU"){
      Serial.println("ERROU");
      efeitoCobravermelho();
    }
    if (comando == "BONUS") {
      servo3.write(0);
      delay(2000);
      servo3.write(90);
    }
  }
}
