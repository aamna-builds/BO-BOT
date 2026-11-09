// BO-BOT: self-balancing robot firmware for the ESP32 (Arduino framework).
//
// Hardware: ESP32 DevKit, MPU-6050 (I2C), 1.3" SH1106 OLED (I2C), DRV8833 + 2 x GA12-N20 motors with encoders.
// The balance controller and the face are ports of the web simulator (see include/controller.h, include/face.h).
//
// Tasks:  control (core 1, 200 Hz): read IMU + encoders -> controller -> motors, and sends the OLED
//         display (core 0, ~12 Hz): draws the face into a frame buffer (no I2C here)
//         loop():                    serial commands for tuning
//
// NOT yet tested on hardware. Follow the bring-up steps in firmware/README.md before letting it balance.
#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>
#include <driver/gpio.h>

#include "config.h"
#include "controller.h"
#include "face.h"

static_assert(configTICK_RATE_HZ >= 1000, "FreeRTOS tick must be 1 kHz for the 5 ms control loop");

// ---------------------------------------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------------------------------------
static bb::Controller ctrl(makeParams());
static bb::Face face;
static U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

static const uint8_t MPU_ADDR = 0x68;
static volatile float cmd_v = 0.0f;       // requested speed, m/s
static volatile float cmd_yaw = 0.0f;     // requested yaw rate, deg/s (+ = turn left)
static volatile bool telemetry = false;
static volatile int run_state = 0;        // 0 waiting upright, 1 balancing, 2 low battery
static volatile uint32_t imu_errors = 0;
static bool oled_ok = false;

// shared with the display task
static volatile float fi_angle = 0, fi_rate = 0, fi_v = 0, fi_yaw = 0;
static volatile bool fi_fallen = true, fi_low = false;
static uint8_t frame[1024];
static volatile bool frame_ready = false;

// ---------------------------------------------------------------------------------------------------------
// Encoders: x4 quadrature decoding in interrupts
// ---------------------------------------------------------------------------------------------------------
struct Encoder {
  volatile int32_t count = 0;
  volatile uint8_t last = 0;
  int pinA, pinB;
};
static Encoder encL, encR;
static const int8_t DRAM_ATTR QDEC[16] = {0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0};

static void IRAM_ATTR encoderIsr(void* arg) {
  Encoder* e = static_cast<Encoder*>(arg);
  const uint8_t now = (uint8_t)((gpio_get_level((gpio_num_t)e->pinA) << 1) | gpio_get_level((gpio_num_t)e->pinB));
  e->count += QDEC[(e->last << 2) | now];
  e->last = now;
}

static void encoderBegin(Encoder& e, int a, int b) {
  e.pinA = a; e.pinB = b;
  pinMode(a, INPUT);
  pinMode(b, INPUT);
  e.last = (uint8_t)((digitalRead(a) << 1) | digitalRead(b));
  attachInterruptArg(a, encoderIsr, &e, CHANGE);
  attachInterruptArg(b, encoderIsr, &e, CHANGE);
}

// ---------------------------------------------------------------------------------------------------------
// Motors (DRV8833: PWM on IN1 to go one way, PWM on IN2 to go the other)
// ---------------------------------------------------------------------------------------------------------
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void pwmBegin(int pin, int /*channel*/) { ledcAttach(pin, PWM_FREQ_HZ, PWM_BITS); ledcWrite(pin, 0); }
static void pwmWrite(int pin, int /*channel*/, int duty) { ledcWrite(pin, duty); }
#else
static void pwmBegin(int pin, int channel) { ledcSetup(channel, PWM_FREQ_HZ, PWM_BITS); ledcAttachPin(pin, channel); ledcWrite(channel, 0); }
static void pwmWrite(int /*pin*/, int channel, int duty) { ledcWrite(channel, duty); }
#endif

static void motorWrite(int pin1, int ch1, int pin2, int ch2, int pwm, bool invert) {
  if (invert) pwm = -pwm;
  if (pwm > 255) pwm = 255;
  if (pwm < -255) pwm = -255;
  if (pwm > 0) { pwmWrite(pin1, ch1, pwm); pwmWrite(pin2, ch2, 0); }
  else if (pwm < 0) { pwmWrite(pin1, ch1, 0); pwmWrite(pin2, ch2, -pwm); }
  else { pwmWrite(pin1, ch1, 0); pwmWrite(pin2, ch2, 0); }
}
static void motorsWrite(int left, int right) {
  motorWrite(PIN_ML_IN1, 0, PIN_ML_IN2, 1, left, MOTOR_L_INVERT);
  motorWrite(PIN_MR_IN1, 2, PIN_MR_IN2, 3, right, MOTOR_R_INVERT);
}

// ---------------------------------------------------------------------------------------------------------
// MPU-6050
// ---------------------------------------------------------------------------------------------------------
static bool mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg); Wire.write(val);
  return Wire.endTransmission() == 0;
}

static bool mpuBegin() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x75);                               // WHO_AM_I
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU_ADDR, 1) != 1) return false;
  const uint8_t who = Wire.read();
  Serial.printf("MPU WHO_AM_I = 0x%02X\n", who);
  if (who != 0x68 && who != 0x70 && who != 0x71 && who != 0x72 && who != 0x98) return false;
  bool ok = mpuWrite(0x6B, 0x80);                 // reset
  delay(100);
  ok &= mpuWrite(0x6B, 0x01);                     // wake, clock from gyro X
  ok &= mpuWrite(0x19, 0x00);                     // sample rate divider: 1 kHz
  ok &= mpuWrite(0x1A, 0x03);                     // digital low-pass filter, 44 Hz (as in the simulator)
  ok &= mpuWrite(0x1B, 0x08);                     // gyro   +/- 500 deg/s (65.5 LSB per deg/s)
  ok &= mpuWrite(0x1C, 0x08);                     // accel  +/- 4 g
  return ok;
}

static bool mpuRead(ImuRaw& r) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU_ADDR, 14) != 14) return false;
  uint8_t b[14];
  for (int i = 0; i < 14; i++) b[i] = Wire.read();
  r.ax = (int16_t)((b[0] << 8) | b[1]);
  r.ay = (int16_t)((b[2] << 8) | b[3]);
  r.az = (int16_t)((b[4] << 8) | b[5]);
  r.gx = (int16_t)((b[8] << 8) | b[9]);           // b[6..7] is temperature
  r.gy = (int16_t)((b[10] << 8) | b[11]);
  r.gz = (int16_t)((b[12] << 8) | b[13]);
  return true;
}

// Average the gyro while the robot is held still; retry if it moved.
static bool calibrateGyro() {
  for (int attempt = 0; attempt < 5; attempt++) {
    double sx = 0, sy = 0, sz = 0, sxx = 0, syy = 0, szz = 0;
    const int N = 400;
    int got = 0;
    for (int i = 0; i < N; i++) {
      ImuRaw r;
      if (mpuRead(r)) { sx += r.gx; sy += r.gy; sz += r.gz; sxx += (double)r.gx * r.gx; syy += (double)r.gy * r.gy; szz += (double)r.gz * r.gz; got++; }
      delay(5);
    }
    if (got < N / 2) continue;
    const double mx = sx / got, my = sy / got, mz = sz / got;
    const double vx = sxx / got - mx * mx, vy = syy / got - my * my, vz = szz / got - mz * mz;
    const double sd = sqrt(fmax(vx, fmax(vy, vz)));
    Serial.printf("gyro offsets %.1f %.1f %.1f, noise %.1f counts\n", mx, my, mz, sd);
    if (sd < 30.0) { ctrl.setGyroOffsets((float)mx, (float)my, (float)mz); return true; }   // 30 counts = 0.5 deg/s
    Serial.println("robot moved during calibration, trying again");
  }
  return false;
}

// ---------------------------------------------------------------------------------------------------------
// Battery
// ---------------------------------------------------------------------------------------------------------
static float readBatteryVolts() {
  const float mv = (float)analogReadMilliVolts(PIN_VBAT);
  return mv / 1000.0f * (VBAT_R_TOP + VBAT_R_BOTTOM) / VBAT_R_BOTTOM;
}

// ---------------------------------------------------------------------------------------------------------
// Control task: 200 Hz
// ---------------------------------------------------------------------------------------------------------
static void controlStep(uint32_t tick) {
  ImuRaw raw;
  if (!mpuRead(raw)) {
    imu_errors++;
    motorsWrite(0, 0);
    return;
  }
  const ImuRaw m = mapImu(raw);
  const int16_t r6[6] = {m.ax, m.ay, m.az, m.gx, m.gy, m.gz};

  int32_t cL = encL.count, cR = encR.count;
  if (ENC_L_INVERT) cL = -cL;
  if (ENC_R_INVERT) cR = -cR;
  const float vbat = readBatteryVolts();

  const bb::Output out = ctrl.update(r6, cL, cR, vbat, cmd_v, cmd_yaw);
  if (out.enabled) motorsWrite(out.pwmL, out.pwmR); else motorsWrite(0, 0);

  // After a fall (or at power-up) wait until the robot is held upright for one second, then start again.
  static int upright = 0;
  if (ctrl.fallen || ctrl.low_batt) {
    upright = (fabsf(ctrl.angle) < 3.0f && fabsf(ctrl.gyro) < 20.0f) ? upright + 1 : 0;
    if (upright >= (int)CONTROL_HZ) {
      const bb::Gains keep = ctrl.g;
      ctrl.reset();
      ctrl.g = keep;
      ctrl.vbat = vbat;
      upright = 0;
    }
  } else upright = 0;
  run_state = ctrl.low_batt ? 2 : (ctrl.fallen ? 0 : 1);

  fi_angle = ctrl.angle; fi_rate = ctrl.gyro; fi_v = ctrl.v_cmd; fi_yaw = ctrl.yaw_cmd;
  fi_fallen = ctrl.fallen; fi_low = ctrl.low_batt;

  // OLED: one 128-byte page every second tick, so the I2C bus is never busy for long.
  if (oled_ok && (tick & 1)) {
    static uint8_t page = 0;
    bool send = true;
    if (page == 0) {                                // start of a new picture: take the frame the display task made
      if (frame_ready) { memcpy(u8g2.getBufferPtr(), frame, sizeof(frame)); frame_ready = false; }
      else send = false;
    }
    if (send) { u8g2.updateDisplayArea(0, page, 16, 1); page = (page + 1) & 7; }
  }

  if (telemetry && (tick % 10) == 0 && Serial.availableForWrite() > 120) {
    Serial.printf("%lu,%.2f,%.2f,%d,%d,%.3f,%.2f,%d\n", (unsigned long)millis(), ctrl.angle, ctrl.target,
                  ctrl.pwmL, ctrl.pwmR, ctrl.v, ctrl.vbat, (int)run_state);
  }
}

static void controlTask(void*) {
  TickType_t last = xTaskGetTickCount();
  uint32_t tick = 0;
  for (;;) {
    vTaskDelayUntil(&last, pdMS_TO_TICKS(5));
    controlStep(tick++);
  }
}

// ---------------------------------------------------------------------------------------------------------
// Display task: draws the face, about 12 frames per second (CPU only, no I2C)
// ---------------------------------------------------------------------------------------------------------
static void displayTask(void*) {
  const float dt = 0.08f;
  for (;;) {
    bb::FaceInfo info;
    info.angle = fi_angle; info.rate = fi_rate; info.v_cmd = fi_v; info.yaw_cmd = fi_yaw;
    info.fallen = fi_fallen; info.low_batt = fi_low;
    face.update(dt, info);
    if (!frame_ready) { face.pack(frame); frame_ready = true; }
    vTaskDelay(pdMS_TO_TICKS(80));
  }
}

// ---------------------------------------------------------------------------------------------------------
// Serial commands (for tuning from the Serial Monitor, 115200 baud)
// ---------------------------------------------------------------------------------------------------------
struct GainRef { const char* name; float* ptr; };
static GainRef gainTable[] = {
  {"kp", &ctrl.g.kp}, {"kd", &ctrl.g.kd}, {"ki", &ctrl.g.ki}, {"kp_v", &ctrl.g.kp_v}, {"ki_v", &ctrl.g.ki_v},
  {"kp_t", &ctrl.g.kp_t}, {"ki_t", &ctrl.g.ki_t}, {"alpha", &ctrl.g.alpha}, {"max_lean", &ctrl.g.max_lean},
  {"deadband", &ctrl.g.deadband}, {"pwm_cap", &ctrl.g.pwm_cap}, {"fall_angle", &ctrl.g.fall_angle},
  {"trim", &ctrl.g.trim}, {"kff", &ctrl.g.kff},
};

static void printHelp() {
  Serial.println("commands:");
  Serial.println("  show                  print gains and state");
  Serial.println("  set <gain> <value>    e.g. set kp 50   (gains: kp kd ki kp_v ki_v kp_t ki_t alpha max_lean deadband pwm_cap fall_angle trim kff)");
  Serial.println("  v <m/s>               drive speed, e.g. v 0.2");
  Serial.println("  yaw <deg/s>           turn rate, + = left");
  Serial.println("  stop                  v = 0, yaw = 0");
  Serial.println("  tele on|off           CSV: ms,angle,target,pwmL,pwmR,speed,vbat,state");
}

static void printStatus() {
  Serial.printf("state %d (0 waiting upright, 1 balancing, 2 low battery), angle %.2f deg, speed %.3f m/s, battery %.2f V, imu errors %lu\n",
                (int)run_state, ctrl.angle, ctrl.v, ctrl.vbat, (unsigned long)imu_errors);
  Serial.printf("encoders L %ld R %ld\n", (long)encL.count, (long)encR.count);
  for (const GainRef& g : gainTable) Serial.printf("  %s = %.3f\n", g.name, *g.ptr);
}

static void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;
  if (line == "help" || line == "?") { printHelp(); return; }
  if (line == "show") { printStatus(); return; }
  if (line == "stop") { cmd_v = 0; cmd_yaw = 0; Serial.println("ok"); return; }
  if (line == "tele on") { telemetry = true; return; }
  if (line == "tele off") { telemetry = false; return; }
  if (line.startsWith("v ")) { cmd_v = line.substring(2).toFloat(); Serial.printf("v = %.3f\n", (float)cmd_v); return; }
  if (line.startsWith("yaw ")) { cmd_yaw = line.substring(4).toFloat(); Serial.printf("yaw = %.1f\n", (float)cmd_yaw); return; }
  if (line.startsWith("set ")) {
    const int sp = line.indexOf(' ', 4);
    if (sp > 0) {
      const String name = line.substring(4, sp);
      const float val = line.substring(sp + 1).toFloat();
      for (const GainRef& g : gainTable)
        if (name == g.name) { *g.ptr = val; Serial.printf("%s = %.3f\n", g.name, val); return; }
    }
    Serial.println("unknown gain, type help");
    return;
  }
  Serial.println("unknown command, type help");
}

// ---------------------------------------------------------------------------------------------------------
// setup / loop
// ---------------------------------------------------------------------------------------------------------
static void oledMessage(const char* l1, const char* l2) {
  if (!oled_ok) return;
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x12_tr);
  u8g2.drawStr(4, 24, l1);
  u8g2.drawStr(4, 44, l2);
  u8g2.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\nBO-BOT balance firmware");

  // motors off first
  pwmBegin(PIN_ML_IN1, 0); pwmBegin(PIN_ML_IN2, 1); pwmBegin(PIN_MR_IN1, 2); pwmBegin(PIN_MR_IN2, 3);
  motorsWrite(0, 0);
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);

  Wire.begin();                 // default pins SDA 21, SCL 22
  Wire.setClock(400000);

  oled_ok = u8g2.begin();
  if (oled_ok) { u8g2.setBusClock(400000); oledMessage("BO-BOT", "starting..."); }
  else Serial.println("OLED not found (continuing without it)");

  if (!mpuBegin()) {
    Serial.println("MPU-6050 not found. Check SDA/SCL wiring and power.");
    oledMessage("MPU-6050", "not found");
    for (;;) delay(1000);       // never run motors without the IMU
  }

  oledMessage("hold still", "calibrating...");
  Serial.println("calibrating gyro, keep the robot still");
  if (!calibrateGyro()) {
    Serial.println("gyro calibration failed (robot kept moving?). Reset and try again.");
    oledMessage("calibration", "failed");
    for (;;) delay(1000);
  }

  encoderBegin(encL, PIN_ENC_L_A, PIN_ENC_L_B);
  encoderBegin(encR, PIN_ENC_R_A, PIN_ENC_R_B);

  ctrl.reset();
  ctrl.fallen = true;           // stay off until the robot is held upright for one second
  Serial.println("ready. Hold the robot upright to start. Type help for commands.");

  xTaskCreatePinnedToCore(displayTask, "face", 4096, nullptr, 1, nullptr, 0);
  xTaskCreatePinnedToCore(controlTask, "control", 6144, nullptr, 5, nullptr, 1);
}

void loop() {
  static String line;
  while (Serial.available()) {
    const char c = (char)Serial.read();
    if (c == '\n' || c == '\r') { handleCommand(line); line = ""; }
    else if (line.length() < 80) line += c;
  }
  delay(10);
}
