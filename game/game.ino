#include <Adafruit_NeoPixel.h>
#include <Metro.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

#define STRIP_COUNT 2
#define MAX_PIXELS_PER_STRIP 240

Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(MAX_PIXELS_PER_STRIP, 5, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2 = Adafruit_NeoPixel(MAX_PIXELS_PER_STRIP, 6, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strips[] = {strip1, strip2};

byte stripIndex = 0;
byte buffer[MAX_PIXELS_PER_STRIP];
byte bufferIndex = 0;
bool stripsReady = false;

void setup() {
  for (byte s = 0; s < STRIP_COUNT; s++) {
    strips[s].begin();
    strips[s].show();
  }

  Serial.begin(0);

  for (byte s = 0; s < STRIP_COUNT; s++) {
    for (byte i = 0; i <= strips[s].numPixels(); i++) {
      strips[s].setPixelColor(i, strips[s].Color(0, 0, 0));
    }
    strips[s].show();
  }
}

void loop() {
  byte rc;
  while (Serial.available() > 0) {
    rc = Serial.read();
    if (!stripsReady) {
      strips[stripIndex].updateLength(rc);
      stripIndex++;
      if (stripIndex == STRIP_COUNT) {
        stripsReady = true;
        stripIndex = 0;
      }
      Serial.println(stripIndex); //ack
    }
    else {
      buffer[bufferIndex] = rc;
      bufferIndex++;
      if (bufferIndex == strips[stripIndex].numPixels()) {
        updateStrip(&strips[stripIndex], buffer);    
        bufferIndex = 0;
        stripIndex++;
        if (stripIndex == STRIP_COUNT) {
          stripIndex = 0;
        }
        Serial.println(stripIndex); //ack
      }
    }
  }
}


void updateStrip(Adafruit_NeoPixel* strip, byte* data) {
  byte color;
  byte alpha;
  for (byte i = 0; i < strip->numPixels(); i++) {
    color = data[i] >> 5;
    alpha = (data[i] & B00011111) << 3;
    if (color == 0) {
      strip->setPixelColor(i, strip->Color(0, 0, 0));
    } else if (color == 1) {
      strip->setPixelColor(i, strip->Color(alpha/4, 0, alpha*0.5/4));
    } else if (color == 2) {
      strip->setPixelColor(i, strip->Color(alpha/4, alpha*0.3/4, 0));
    } else if (color == 3) {
      strip->setPixelColor(i, strip->Color(0, alpha/4, alpha/4));
    } else if (color == 4) {
      strip->setPixelColor(i, strip->Color(alpha*0.5/4, alpha/4, 0));
    } else if (color == 5) {
      strip->setPixelColor(i, strip->Color(alpha/8, alpha/8, alpha/8));
    } else if (color == 6) {
      strip->setPixelColor(i, strip->Color(0, 0, alpha/4));
    }
  }
  strip->show();
}

