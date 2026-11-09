// Minimal stand-ins for the Arduino-ESP32 headers, only so that `g++ -fsyntax-only` can catch typos in
// firmware/balance_bot/src/main.cpp on a PC. They do not behave like the real thing.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#ifndef ESP_ARDUINO_VERSION_MAJOR
#define ESP_ARDUINO_VERSION_MAJOR 2
#endif
#define IRAM_ATTR
#define DRAM_ATTR
#define INPUT 0
#define CHANGE 3
#define ADC_11db 3
#define configTICK_RATE_HZ 1000
typedef uint32_t TickType_t;
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
inline TickType_t xTaskGetTickCount() { return 0; }
inline void vTaskDelayUntil(TickType_t*, TickType_t) {}
inline void vTaskDelay(TickType_t) {}
typedef void (*TaskFunction_t)(void*);
inline int xTaskCreatePinnedToCore(TaskFunction_t, const char*, uint32_t, void*, int, void*, int) { return 1; }
inline void delay(uint32_t) {}
inline uint32_t millis() { return 0; }
inline void pinMode(int, int) {}
inline int digitalRead(int) { return 0; }
inline void attachInterruptArg(int, void (*)(void*), void*, int) {}
inline uint32_t analogReadMilliVolts(int) { return 0; }
inline void analogSetPinAttenuation(int, int) {}
#if ESP_ARDUINO_VERSION_MAJOR >= 3
inline bool ledcAttach(int, int, int) { return true; }
inline bool ledcWrite(int, uint32_t) { return true; }
#else
inline double ledcSetup(int, double, int) { return 0; }
inline void ledcAttachPin(int, int) {}
inline void ledcWrite(int, uint32_t) {}
#endif
class String : public std::string {
 public:
  String() {}
  String(const char* s) : std::string(s) {}
  String(const std::string& s) : std::string(s) {}
  int length() const { return (int)size(); }
  void trim() {}
  bool startsWith(const char* p) const { return rfind(p, 0) == 0; }
  int indexOf(char c, int from = 0) const { size_t i = find(c, from); return i == npos ? -1 : (int)i; }
  String substring(int a, int b = -1) const { return String(b < 0 ? substr(a) : substr(a, b - a)); }
  float toFloat() const { return 0; }
  String& operator+=(char c) { push_back(c); return *this; }
};
class HardwareSerial {
 public:
  void begin(long) {}
  void println(const char*) {}
  void println(const String&) {}
  int printf(const char*, ...) __attribute__((format(printf, 2, 3))) { return 0; }
  int available() { return 0; }
  int read() { return 0; }
  int availableForWrite() { return 0; }
};
static HardwareSerial Serial;
