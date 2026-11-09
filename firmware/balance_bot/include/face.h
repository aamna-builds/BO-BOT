// OLED face for BO-BOT (128 x 64 monochrome).
//
// Portable C++ port of the face in the web simulator (class Face). It draws into an 8-bit image,
// so the same file runs on the ESP32 and in the host tests under firmware/test/.
// pack() converts the image to the SSD1306 / SH1106 page format used by the U8g2 display buffer.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
#include <initializer_list>

namespace bb {

enum class Mood : uint8_t { Idle, Happy, Careful, Worried, Surprised, Dizzy, Sleepy };

struct FaceInfo {
  float angle = 0;      // pitch, degrees
  float rate = 0;       // pitch rate, deg/s
  float v_cmd = 0;      // requested speed, m/s
  float yaw_cmd = 0;    // requested yaw rate, deg/s
  bool fallen = false, low_batt = false, pushed = false;
};

class Face {
 public:
  static const int W = 128, H = 64;
  uint8_t img[W * H];
  float look = 0, lookv = 0;   // eye offset from steering (x) and from tilt (y)
  Mood current = Mood::Idle;

  explicit Face(uint32_t seed = 4) : rng_(seed ? seed : 1) {
    std::memset(img, 0, sizeof(img));
    nextBlink_ = 2.0f;
  }

  Mood update(float dt, const FaceInfo& info) {
    t_ += dt;
    const Mood mood = choose(info, dt);
    const float tgt = info.yaw_cmd > 10 ? -1.0f : (info.yaw_cmd < -10 ? 1.0f : 0.0f);
    const float k = fminf(1.0f, dt * 8.0f);
    look += (tgt - look) * k;
    lookv += (clampf(info.angle / 15.0f, -1.0f, 1.0f) - lookv) * k;
    if (t_ > nextBlink_ && (mood == Mood::Idle || mood == Mood::Happy || mood == Mood::Careful || mood == Mood::Worried)) {
      blinkT_ = 0; nextBlink_ = t_ + 2.0f + 3.0f * rand01();
    }
    float blink = 1.0f;
    if (blinkT_ >= 0) {
      blinkT_ += dt;
      const float ph = blinkT_ / 0.16f;
      blink = ph < 1.0f ? std::fabs(1.0f - 2.0f * ph) : 1.0f;
      if (ph >= 1.0f) blinkT_ = -1.0f;
    }
    draw(mood, blink);
    current = mood;
    return mood;
  }

  // Convert the image to U8g2 / SSD1306 page layout: 8 pages of 128 bytes, bit b = row (page * 8 + b).
  void pack(uint8_t* buf) const {
    for (int p = 0; p < H / 8; p++)
      for (int x = 0; x < W; x++) {
        uint8_t b = 0;
        for (int bit = 0; bit < 8; bit++) b |= (uint8_t)((img[(p * 8 + bit) * W + x] ? 1 : 0) << bit);
        buf[p * W + x] = b;
      }
  }

  void draw(Mood mood, float blink = 1.0f) {
    std::memset(img, 0, sizeof(img));
    const float lx = 36, rx = 92, ey = 26, ox = look * 10.0f, oy = lookv * 5.0f;
    if (mood == Mood::Dizzy) {
      for (float cx : {lx, rx}) { tline(cx - 11, ey - 11, cx + 11, ey + 11, 5); tline(cx - 11, ey + 11, cx + 11, ey - 11, 5); }
      for (int i = 0; i < 5; i++) { float x0 = 46 + i * 8; tline(x0, 52 + (i % 2) * 4, x0 + 8, 52 + ((i + 1) % 2) * 4, 3); }
      return;
    }
    if (mood == Mood::Sleepy) {
      for (float cx : {lx, rx}) rbox(cx - 14, ey + 2, cx + 14, ey + 8, 3);
      tline(56, 52, 72, 52, 3);
      rbox(104, 46, 122, 58, 2); rbox(106, 48, 120, 56, 1, 0); rbox(107, 49, 109, 55, 0); rbox(122, 49, 124, 55, 0);
      return;
    }
    if (mood == Mood::Surprised) {
      for (float cx : {lx, rx}) { ellipse(cx, ey, 15, 17); ellipse(cx, ey, 9, 11, 0); ellipse(cx, ey, 5, 6); }
      ellipse(64, 53, 6, 7); ellipse(64, 53, 3, 4, 0);
      return;
    }
    if (mood == Mood::Happy) {
      for (float cx : {lx, rx}) arc(cx + ox, ey + 8 + oy, 13, 200, 340, 6);
      arc(64, 40, 14, 25, 155, 4);
      return;
    }
    const float h = (mood == Mood::Careful ? 22.0f : 30.0f) * blink;
    const float cxs[2] = {lx, rx};
    for (int i = 0; i < 2; i++) {
      const float cx = cxs[i];
      const float x0 = cx - 13 + ox, x1 = cx + 13 + ox, y0 = ey - h / 2 + oy, y1 = ey + h / 2 + oy;
      if (h < 3) { tline(x0, ey + oy, x1, ey + oy, 3); continue; }
      rbox(x0, y0, x1, y1, 7);
      if (mood == Mood::Worried) {
        const float s = i == 0 ? 1.0f : -1.0f, xi = i == 0 ? x1 : x0;
        for (int k = 0; k < 14; k++) tline(xi - s * 26, y0 - 4 - k, xi, y0 + 10 - k, 2, 0);
      }
    }
    if (mood == Mood::Worried) { for (int i = 0; i < 4; i++) tline(50 + i * 7, 54 + (i % 2) * 3, 57 + i * 7, 54 + ((i + 1) % 2) * 3, 3); }
    else if (mood == Mood::Careful) tline(58, 54, 70, 54, 3);
    else arc(64, 44, 9, 30, 150, 3);
  }

 private:
  uint32_t rng_;
  float t_ = 0, nextBlink_ = 2.0f, blinkT_ = -1.0f;
  float hold_ = 0;
  Mood mood_ = Mood::Idle;

  static float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
  float rand01() { rng_ ^= rng_ << 13; rng_ ^= rng_ >> 17; rng_ ^= rng_ << 5; return (rng_ & 0xFFFFFF) / 16777216.0f; }

  Mood choose(const FaceInfo& info, float dt) {
    hold_ = fmaxf(0.0f, hold_ - dt);
    if (info.fallen) return Mood::Dizzy;
    if (info.low_batt) return Mood::Sleepy;
    if (std::fabs(info.rate) > 90.0f || info.pushed) { hold_ = 1.2f; mood_ = Mood::Surprised; return Mood::Surprised; }
    if (hold_ > 0) return mood_;
    if (std::fabs(info.angle) > 12.0f) return Mood::Worried;
    if (info.v_cmd > 0.05f) return Mood::Happy;
    if (info.v_cmd < -0.05f) return Mood::Careful;
    return Mood::Idle;
  }

  // ---- drawing primitives (same shapes as the simulator) ----
  void rbox(float x0, float y0, float x1, float y1, float r, uint8_t val = 1) {
    r = fmaxf(0.0f, fminf(r, fminf((x1 - x0) / 2, (y1 - y0) / 2)));
    for (int y = (int)fmaxf(0, std::floor(y0)); y <= fminf(H - 1, y1); y++)
      for (int x = (int)fmaxf(0, std::floor(x0)); x <= fminf(W - 1, x1); x++) {
        if (x < x0 || y < y0) continue;
        const float cx = clampf((float)x, x0 + r, x1 - r), cy = clampf((float)y, y0 + r, y1 - r);
        if ((x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r + 0.5f) img[y * W + x] = val;
      }
  }
  void ellipse(float cx, float cy, float rx, float ry, uint8_t val = 1) {
    for (int y = (int)fmaxf(0, std::floor(cy - ry)); y <= fminf(H - 1, cy + ry); y++)
      for (int x = (int)fmaxf(0, std::floor(cx - rx)); x <= fminf(W - 1, cx + rx); x++) {
        const float a = (x - cx) / rx, b = (y - cy) / ry;
        if (a * a + b * b <= 1.0f) img[y * W + x] = val;
      }
  }
  void tline(float x0, float y0, float x1, float y1, float w, uint8_t val = 1) {
    const float dx = x1 - x0, dy = y1 - y0, hw = w / 2;
    float L2 = dx * dx + dy * dy; if (L2 == 0) L2 = 1e-9f;
    for (int y = (int)fmaxf(0, std::floor(fminf(y0, y1) - hw)); y <= fminf(H - 1, fmaxf(y0, y1) + hw); y++)
      for (int x = (int)fmaxf(0, std::floor(fminf(x0, x1) - hw)); x <= fminf(W - 1, fmaxf(x0, x1) + hw); x++) {
        const float t = clampf(((x - x0) * dx + (y - y0) * dy) / L2, 0.0f, 1.0f);
        const float px = x0 + t * dx, py = y0 + t * dy;
        if ((x - px) * (x - px) + (y - py) * (y - py) <= hw * hw) img[y * W + x] = val;
      }
  }
  void arc(float cx, float cy, float r, float a0, float a1, float w, uint8_t val = 1) {
    a0 = std::fmod(std::fmod(a0, 360.0f) + 360.0f, 360.0f);
    a1 = std::fmod(std::fmod(a1, 360.0f) + 360.0f, 360.0f);
    for (int y = (int)fmaxf(0, std::floor(cy - r - w)); y <= fminf(H - 1, cy + r + w); y++)
      for (int x = (int)fmaxf(0, std::floor(cx - r - w)); x <= fminf(W - 1, cx + r + w); x++) {
        const float dd = std::sqrt((x - cx) * (x - cx) + (y - cy) * (y - cy));
        if (std::fabs(dd - r) > w / 2) continue;
        const float a = std::fmod(std::fmod(std::atan2((float)y - cy, (float)x - cx) * 180.0f / 3.14159265f, 360.0f) + 360.0f, 360.0f);
        if (a0 <= a1 ? (a >= a0 && a <= a1) : (a >= a0 || a <= a1)) img[y * W + x] = val;
      }
  }
};

}  // namespace bb
