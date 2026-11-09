#pragma once
#include "Arduino.h"
#define U8X8_PIN_NONE 255
#define U8G2_R0 0
#define u8g2_font_6x12_tr 0
class U8G2_SH1106_128X64_NONAME_F_HW_I2C {
 public:
  U8G2_SH1106_128X64_NONAME_F_HW_I2C(int, int) {}
  bool begin() { return true; }
  void setBusClock(uint32_t) {}
  uint8_t* getBufferPtr() { return buf; }
  void updateDisplayArea(int, int, int, int) {}
  void clearBuffer() {}
  void setFont(int) {}
  void drawStr(int, int, const char*) {}
  void sendBuffer() {}
 private:
  uint8_t buf[1024];
};
