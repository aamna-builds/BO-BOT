// Balance controller for BO-BOT.
//
// Portable C++ (no Arduino code), so the same file runs on the ESP32 and in the host tests under firmware/test/.
// It is a direct port of the controller in the web simulator (simulation/web/index.html, class Controller),
// and uses the same gains and units, so the values tuned in the simulator carry over.
//
//   angle   complementary filter of accelerometer + gyro                       (degrees, + = leaning forward)
//   speed   from wheel encoders, corrected for body pitch rate                 (m/s)
//   outer   speed error -> lean target (PI)
//   inner   angle error -> PWM: kp*e + kd*pitch_rate + ki*integral, plus a back-EMF feed-forward
//   yaw     yaw-rate error -> PWM difference between the wheels
#pragma once
#include <cmath>
#include <cstdint>

namespace bb {

struct Gains {
  float kp = 55.0f;          // PWM counts per degree of tilt
  float kd = 0.35f;          // PWM per deg/s of pitch rate
  float ki = 0.0f;           // PWM per degree-second
  float kp_v = 20.0f;        // degrees of lean per m/s of speed error
  float ki_v = 0.9f;         // degrees of lean per metre of drift
  float kp_t = 0.3f;         // PWM per deg/s of yaw-rate error
  float ki_t = 1.0f;         // PWM per degree of heading error
  float alpha = 0.98f;       // complementary filter: weight of the gyro
  float max_lean = 10.0f;    // limit on the lean target, degrees
  float deadband = 0.0f;     // PWM counts added to overcome motor stiction
  float pwm_cap = 204.0f;    // 80 % of 255, keeps a 7.4 V pack from over-driving 6 V motors
  float fall_angle = 40.0f;  // give up beyond this tilt, degrees
  float trim = 0.0f;         // balance-point offset, degrees
  float kff = 1.0f;          // speed feed-forward (1 = back-EMF exact)
  float max_auto_trim = 6.0f;
  float v_ramp = 0.6f;       // m/s per second
  float yaw_ramp = 400.0f;   // deg/s per second
};

struct Params {
  float dt = 0.005f;                    // control period, s (200 Hz)
  float wheel_radius_m = 0.017f;
  float track_m = 0.078f;
  float counts_per_wheel_rev = 1400.0f; // 7 PPR x 4 (quadrature) x 50 (gearbox)
  float emf_v_per_mps = 10.418f;        // motor back-EMF per m/s of wheel speed
  float v_cutoff = 6.6f;                // low-battery cut-off, volts
  float gyro_lsb_per_dps = 65.5f;       // MPU-6050 at +/-500 deg/s
};

struct Output {
  int pwmL, pwmR;                       // -255 .. 255
  bool enabled;
  Output(int l = 0, int r = 0, bool e = false) : pwmL(l), pwmR(r), enabled(e) {}
};

inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
inline float jsround(float x) { return std::floor(x + 0.5f); }  // same rounding as the simulator (JavaScript)
inline float signf(float x) { return x > 0 ? 1.0f : (x < 0 ? -1.0f : 0.0f); }

class Controller {
 public:
  static const int kMaxWin = 16;

  Gains g;
  Params p;

  // state (public so the main program and the tests can read it)
  float angle = 0, v = 0, x = 0, target = 0, yaw_rate = 0, vbat = 8.0f, gyro = 0, u = 0;
  float v_cmd = 0, yaw_cmd = 0;
  bool fallen = false, low_batt = false, enabled = true;
  int pwmL = 0, pwmR = 0;

  explicit Controller(const Params& params = Params(), const Gains& gains = Gains()) : g(gains), p(params) {
    n_ = (int)jsround(0.025f / p.dt);
    if (n_ < 1) n_ = 1;
    if (n_ > kMaxWin) n_ = kMaxWin;
    reset();
  }

  // Forget the filter and integrator state (the gyro offsets are kept).
  void reset() {
    angle = 0; init_ = false; haveLast_ = false; v = 0; x = 0; pos_i_ = ang_i_ = head_i_ = 0;
    v_cmd = yaw_cmd = 0; enabled = true; fallen = false; low_batt = false; low_t_ = 0; vbat = 8.0f;
    target = 0; yaw_rate = 0; pwmL = pwmR = 0; u = 0; gyro = 0;
    for (int i = 0; i < kMaxWin; i++) win_[i] = 0;
    wi_ = 0; wn_ = 0;
  }

  // Average the gyro readings taken while the robot is held still (raw order: ax ay az gx gy gz).
  void setGyroOffsets(float gx, float gy, float gz) { goff_[0] = gx; goff_[1] = gy; goff_[2] = gz; }

  // raw: MPU-6050 counts [ax ay az gx gy gz] in the robot frame; cL/cR: encoder counts (+ = forward);
  // vbat_sensed: battery volts; v_in / yaw_in: requested speed (m/s) and yaw rate (deg/s).
  Output update(const int16_t raw[6], int32_t cL, int32_t cR, float vbat_sensed, float v_in, float yaw_in) {
    const float dt = p.dt, PI_ = 3.14159265358979f;
    const float ax = raw[0], az = raw[2];
    const float gp = ((float)raw[4] - goff_[1]) / p.gyro_lsb_per_dps;   // pitch rate, deg/s
    const float gyw = ((float)raw[5] - goff_[2]) / p.gyro_lsb_per_dps;  // yaw rate, deg/s
    const float acc = std::atan2(-ax, az) * 180.0f / PI_;
    gyro = gp;
    if (!init_) { angle = acc; init_ = true; }
    angle = g.alpha * (angle + gp * dt) + (1.0f - g.alpha) * acc;

    if (!haveLast_) { lastL_ = cL; lastR_ = cR; haveLast_ = true; }
    const float dL = (float)(cL - lastL_), dR = (float)(cR - lastR_);
    lastL_ = cL; lastR_ = cR;
    win_[wi_] = dL + dR; wi_ = (wi_ + 1) % n_; if (wn_ < n_) wn_++;
    float sum = 0; for (int i = 0; i < wn_; i++) sum += win_[i];
    const float rel = sum * 0.5f / p.counts_per_wheel_rev * 2.0f * PI_ / ((float)wn_ * dt);
    const float vraw = p.wheel_radius_m * (rel + gp * PI_ / 180.0f);  // add the body's own pitch motion
    v += 0.3f * (vraw - v);
    x += p.wheel_radius_m * ((dL + dR) * 0.5f / p.counts_per_wheel_rev * 2.0f * PI_ + gp * PI_ / 180.0f * dt);
    yaw_rate = gyw;

    vbat += 0.02f * (vbat_sensed - vbat);
    if (vbat < p.v_cutoff) { low_t_ += dt; if (low_t_ > 2.0f) low_batt = true; } else low_t_ = 0;

    float st = g.v_ramp * dt;     v_cmd += clampf(v_in - v_cmd, -st, st);
    st = g.yaw_ramp * dt;         yaw_cmd += clampf(yaw_in - yaw_cmd, -st, st);

    if (std::fabs(angle) > g.fall_angle) fallen = true;
    if (fallen || low_batt) {
      enabled = false; pos_i_ = ang_i_ = head_i_ = 0; pwmL = pwmR = 0;
      return Output(0, 0, false);
    }

    const float ev = v_cmd - v;
    const float lim = g.max_auto_trim / (g.ki_v > 1e-6f ? g.ki_v : 1e-6f);
    pos_i_ = clampf(pos_i_ + ev * dt, -lim, lim);
    target = clampf(g.kp_v * ev + g.ki_v * pos_i_, -g.max_lean, g.max_lean);

    const float e = angle - g.trim - target;
    ang_i_ = clampf(ang_i_ + e * dt, -50.0f, 50.0f);
    const float vb = vbat > 5.0f ? vbat : 5.0f;
    float uu = g.kp * e + g.kd * gp + g.ki * ang_i_;
    uu += g.kff * v_cmd * p.emf_v_per_mps / vb * 255.0f;
    u = uu;

    const float ey = yaw_cmd - gyw;
    head_i_ = clampf(head_i_ + ey * dt, -90.0f, 90.0f);
    float diff = g.kp_t * ey + g.ki_t * head_i_;
    diff += g.kff * (yaw_cmd * PI_ / 180.0f) * p.track_m / 2.0f * p.emf_v_per_mps / vb * 255.0f;

    const float outs[2] = {uu - diff, uu + diff};
    int res[2];
    for (int i = 0; i < 2; i++) {
      float ui = outs[i];
      if (std::fabs(ui) > 0.5f) ui += signf(ui) * g.deadband;
      res[i] = (int)jsround(clampf(ui, -g.pwm_cap, g.pwm_cap));
    }
    pwmL = res[0]; pwmR = res[1]; enabled = true;
    return Output(res[0], res[1], true);
  }

 private:
  int n_ = 5;
  bool init_ = false, haveLast_ = false;
  int32_t lastL_ = 0, lastR_ = 0;
  float win_[kMaxWin];
  int wi_ = 0, wn_ = 0;
  float pos_i_ = 0, ang_i_ = 0, head_i_ = 0, low_t_ = 0;
  float goff_[3] = {0, 0, 0};
};

}  // namespace bb
