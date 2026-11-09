// BO-BOT hardware configuration. Everything you may need to change for your own wiring is in this file.
#pragma once
#include "controller.h"

// ---------------------------------------------------------------------------------------------------------
// Pins (ESP32 DevKit). Keep wiring/README.md in step with this table.
// ---------------------------------------------------------------------------------------------------------
// I2C bus shared by the MPU-6050 and the OLED. SDA/SCL are the ESP32 default pins (21 / 22).
constexpr int PIN_ML_IN1 = 25;   // DRV8833, left motor
constexpr int PIN_ML_IN2 = 26;
constexpr int PIN_MR_IN1 = 27;   // DRV8833, right motor
constexpr int PIN_MR_IN2 = 4;
constexpr int PIN_ENC_L_A = 32;  // left encoder  (power the encoders from 3V3, not 5 V)
constexpr int PIN_ENC_L_B = 33;
constexpr int PIN_ENC_R_A = 34;  // right encoder (34 and 35 are input-only pins, fine for encoders)
constexpr int PIN_ENC_R_B = 35;
constexpr int PIN_VBAT = 36;     // battery voltage through a resistor divider (ADC1)

// ---------------------------------------------------------------------------------------------------------
// Direction fixes. Check them with the wheels OFF the ground (see firmware/README.md, bring-up steps).
// ---------------------------------------------------------------------------------------------------------
constexpr bool MOTOR_L_INVERT = false;  // flip if a positive command spins the left wheel backwards
constexpr bool MOTOR_R_INVERT = false;
constexpr bool ENC_L_INVERT = false;    // flip if rolling the left wheel forward counts down
constexpr bool ENC_R_INVERT = false;

// MPU-6050 mounting. Robot frame: X forward, Y left, Z up. With the breakout mounted flat, X toward the front
// and Z up, the defaults below are right. For another mounting, remap the chip axes here (and flip signs).
// Check: the printed angle must be POSITIVE when you lean the robot forward.
struct ImuRaw { int16_t ax, ay, az, gx, gy, gz; };
inline ImuRaw mapImu(const ImuRaw& r) {
  ImuRaw o;
  o.ax = r.ax;  o.ay = r.ay;  o.az = r.az;
  o.gx = r.gx;  o.gy = r.gy;  o.gz = r.gz;
  return o;
}

// ---------------------------------------------------------------------------------------------------------
// Robot constants (same numbers as the simulator)
// ---------------------------------------------------------------------------------------------------------
constexpr float CONTROL_HZ = 200.0f;
constexpr float WHEEL_RADIUS_M = 0.017f;        // 34 mm wheel
constexpr float WHEEL_TRACK_M = 0.078f;         // simulator value; CAD shows 70 mm centre to centre. Measure yours.
constexpr float ENC_PPR = 7.0f;                 // N20 encoder pulses per motor revolution, per channel
constexpr float GEAR_RATIO = 50.0f;             // GA12-N20 300 rpm
constexpr float COUNTS_PER_WHEEL_REV = ENC_PPR * 4.0f * GEAR_RATIO;   // x4 quadrature decoding

// Motor back-EMF constant, from the datasheet numbers used in the simulator (6 V, 300 rpm, 0.04 A no-load, 0.55 A stall).
constexpr float MOTOR_V_RATED = 6.0f, MOTOR_RPM_NOLOAD = 300.0f, MOTOR_I_NOLOAD = 0.04f, MOTOR_I_STALL = 0.55f;
constexpr float MOTOR_R = MOTOR_V_RATED / MOTOR_I_STALL;
constexpr float MOTOR_KE = (MOTOR_V_RATED - MOTOR_I_NOLOAD * MOTOR_R) / (MOTOR_RPM_NOLOAD * GEAR_RATIO * 6.2831853f / 60.0f);
constexpr float EMF_V_PER_MPS = MOTOR_KE * GEAR_RATIO / WHEEL_RADIUS_M;

// Battery divider (top resistor to battery +, bottom resistor to GND), ohms
constexpr float VBAT_R_TOP = 10000.0f, VBAT_R_BOTTOM = 4700.0f;
constexpr float VBAT_CUTOFF = 6.6f;             // 2S LiPo: stop below this

constexpr int PWM_FREQ_HZ = 20000;              // above hearing
constexpr int PWM_BITS = 8;                     // duty 0..255, the same scale as the controller output

inline bb::Params makeParams() {
  bb::Params p;
  p.dt = 1.0f / CONTROL_HZ;
  p.wheel_radius_m = WHEEL_RADIUS_M;
  p.track_m = WHEEL_TRACK_M;
  p.counts_per_wheel_rev = COUNTS_PER_WHEEL_REV;
  p.emf_v_per_mps = EMF_V_PER_MPS;
  p.v_cutoff = VBAT_CUTOFF;
  return p;
}
