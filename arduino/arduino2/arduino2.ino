#include <Adafruit_NeoPixel.h>
#include <Metro.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

#define PIXELS_PER_STRIP 30
#define STRIP_COUNT 2

Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(PIXELS_PER_STRIP, 7, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2 = Adafruit_NeoPixel(PIXELS_PER_STRIP, 6, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strips[] = {strip1, strip2};

byte buffer[PIXELS_PER_STRIP * STRIP_COUNT];
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
    if (bufferIndex == PIXELS_PER_STRIP * STRIP_COUNT) {
      for (byte s = 0; s < STRIP_COUNT; s++) {
        updateStrip(&strips[s], buffer + s * PIXELS_PER_STRIP);  
      }
      
      //Serial.write(buffer, 30);
      
      bufferIndex = 0;
      Serial.println(""); // Newline is the ACK required by the python end
    }
  }
}


void updateStrip(Adafruit_NeoPixel* strip, byte* data) {
  byte color;
  byte alpha;
  for (byte i = 0; i <= PIXELS_PER_STRIP; i++) {
    color = data[i] >> 6;
    alpha = (data[i] & B00111111) << 2;
    if (color == 0) {
      strip->setPixelColor(i, strip->Color(alpha/4, 0, 0));
    } else if (color == 1) {
      strip->setPixelColor(i, strip->Color(0, alpha/4, 0));
    } else if (color == 2) {
      strip->setPixelColor(i, strip->Color(alpha/8, alpha/8, alpha/8));
    }
  }
  strip->show();
}
