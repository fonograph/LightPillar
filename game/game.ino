#include <Adafruit_NeoPixel.h>
#include <Metro.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

#define PIXELS_PER_STRIP 60
#define STRIP_COUNT 4

Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(PIXELS_PER_STRIP, 5, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2 = Adafruit_NeoPixel(PIXELS_PER_STRIP, 6, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip3 = Adafruit_NeoPixel(PIXELS_PER_STRIP, 9, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip4 = Adafruit_NeoPixel(PIXELS_PER_STRIP, 10, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strips[] = {strip1, strip2, strip3, strip4};

byte stripIndex = 0;
byte buffer[PIXELS_PER_STRIP];
byte bufferIndex = 0;


void setup() {
  for (byte s = 0; s < STRIP_COUNT; s++) {
    strips[s].begin();
    strips[s].show();
  }

  Serial.begin(115200);

  for (byte s = 0; s < STRIP_COUNT; s++) {
    for (byte i = 0; i <= PIXELS_PER_STRIP; i++) {
      strips[s].setPixelColor(i, strips[s].Color(0, 0, 0));
    }
    strips[s].show();
  }
}

void loop() {
  byte rc;
  while (Serial.available() > 0) {
    rc = Serial.read();
    //Serial.println(rc);
    buffer[bufferIndex] = rc;
    bufferIndex++;
    //Serial.println(bufferIndex);
    if (bufferIndex == PIXELS_PER_STRIP) {
      updateStrip(&strips[stripIndex], buffer);    
      //Serial.write(buffer, 30);   
      Serial.println(stripIndex); // Newline is the ACK required by the python end
      bufferIndex = 0;
      stripIndex++;
      if (stripIndex == STRIP_COUNT) {
        stripIndex = 0;
      }
    }
  }
}


void updateStrip(Adafruit_NeoPixel* strip, byte* data) {
  byte color;
  byte alpha;
  for (byte i = 0; i <= PIXELS_PER_STRIP; i++) {
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

