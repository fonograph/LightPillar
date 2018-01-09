#include <Adafruit_NeoPixel.h>
#include <Metro.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

#define STRIP_TERMINAL_PIXELS 2


#define STRIP_STATE_FORWARD 1

Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(30, 6, NEO_GRB + NEO_KHZ800);

int strip1State = STRIP_STATE_FORWARD;
int strip1Speed = 2000;
int strip1Ticker = 0;

void setup() {
  strip1.begin();
  //strip1.setBrightness(20);
  strip1.show();

  for(uint16_t i=0; i<strip1.numPixels(); i++) {
    strip1.setPixelColor(i, strip1.Color(255, 0, 0));
  }
  strip1.show();

  Serial.begin(115200);
}

void loop() {
  byte rc;
  if (Serial.available() > 0) {
    rc = Serial.read();
    Serial.println(rc);
    if ( rc % 2 == 0 ) {
      for(uint16_t i=0; i<strip1.numPixels(); i++) {
      strip1.setPixelColor(i, strip1.Color(255, 0, 0));
      strip1.show();
      }
    }
    else {
      for(uint16_t i=0; i<strip1.numPixels(); i++) {
      strip1.setPixelColor(i, strip1.Color(0, 255, 0));
      strip1.show();
      }
    }
  }

  for(uint16_t i=STRIP_TERMINAL_PIXELS; i<strip1.numPixels()-STRIP_TERMINAL_PIXELS; i++) {
    bool on = (i + strip1Ticker) % (strip1.numPixels()/3) == 0;
    strip1.setPixelColor(i, on ? strip1.Color(255,255,255) : strip1.Color(0,0,0));
  }
  strip1.show();
  strip1Ticker++;
  delay(100);
  

  // STRIP STATE
//  if ( strip1Timer.check() == true ) {
//    strip1Ticker++;
//    if ( strip1State == STRIP_STATE_FORWARD ) {
//      stripForward(strip1, strip1Ticker);
//    }
//  }
}

void stripForward(Adafruit_NeoPixel strip, int ticker) {
  Serial.println("tick");
  Serial.println(ticker);
//  for(uint16_t i=STRIP_TERMINAL_PIXELS; i<strip.numPixels()-STRIP_TERMINAL_PIXELS; i++) {
//    bool on = (i + ticker) % (strip.numPixels()/2) == 0;
//    if ( on ) Serial.println(i);
//    strip.setPixelColor(i, on ? strip.Color(255,255,255) : strip.Color(0,255,0));
//  }
  strip.show();
}

