// Host test: the firmware controller must reproduce the simulator's controller on the same sensor data.
// Reads golden/controller_trace.txt (made by gen_golden.py from the simulator), runs bb::Controller over the
// same inputs, and compares PWM output, state flags, angle and speed.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "../balance_bot/include/controller.h"

int main(int argc, char** argv) {
  const char* path = argc > 1 ? argv[1] : "golden/controller_trace.txt";
  FILE* f = std::fopen(path, "r");
  if (!f) { std::printf("FAIL cannot open %s\n", path); return 1; }

  bb::Controller c;
  char line[512];
  int steps = 0, pwmBad = 0, flagBad = 0, maxPwmDiff = 0, enabledSteps = 0, fallenSteps = 0, lowBattSteps = 0;
  double maxAngle = 0, maxSpeed = 0;
  while (std::fgets(line, sizeof line, f)) {
    if (line[0] == '#') continue;
    if (!std::strncmp(line, "GOFF", 4)) {
      float a, b, d; std::sscanf(line + 4, "%f %f %f", &a, &b, &d); c.setGyroOffsets(a, b, d); continue;
    }
    int ax, ay, az, gx, gy, gz, wl, wr, en, fallen, low; long cL, cR;
    float vbat, vIn, yIn, angle, v, target;
    if (std::sscanf(line, "T %d %d %d %d %d %d %ld %ld %f %f %f %d %d %d %f %f %f %d %d", &ax, &ay, &az, &gx, &gy, &gz,
                    &cL, &cR, &vbat, &vIn, &yIn, &wl, &wr, &en, &angle, &v, &target, &fallen, &low) != 19) {
      std::printf("FAIL cannot parse line %d\n", steps + 1); return 1;
    }
    const int16_t raw[6] = {(int16_t)ax, (int16_t)ay, (int16_t)az, (int16_t)gx, (int16_t)gy, (int16_t)gz};
    bb::Output o = c.update(raw, (int32_t)cL, (int32_t)cR, vbat, vIn, yIn);
    steps++;
    enabledSteps += en; fallenSteps += fallen; lowBattSteps += low;

    const int dl = std::abs(o.pwmL - wl), dr = std::abs(o.pwmR - wr);
    const int d = dl > dr ? dl : dr;
    if (d > maxPwmDiff) maxPwmDiff = d;
    if (d > 2) pwmBad++;                                  // float32 vs double: allow a couple of counts
    if ((o.enabled ? 1 : 0) != en || (c.fallen ? 1 : 0) != fallen || (c.low_batt ? 1 : 0) != low) flagBad++;
    if (std::fabs(c.angle - angle) > maxAngle) maxAngle = std::fabs(c.angle - angle);
    if (std::fabs(c.v - v) > maxSpeed) maxSpeed = std::fabs(c.v - v);
  }
  std::fclose(f);

  std::printf("steps %d (enabled %d, fallen %d, low-battery %d)\n", steps, enabledSteps, fallenSteps, lowBattSteps);
  std::printf("max PWM difference %d counts, max angle difference %.4f deg, max speed difference %.5f m/s\n",
              maxPwmDiff, maxAngle, maxSpeed);
  bool ok = steps > 1000 && pwmBad == 0 && flagBad == 0 && maxAngle < 0.05 && maxSpeed < 0.01;
  // the scenario must exercise the interesting paths, otherwise the test proves little
  ok = ok && enabledSteps > 1000 && lowBattSteps > 0;
  std::printf(ok ? "PASS controller matches the simulator\n" : "FAIL controller differs from the simulator (pwm>2: %d, flags: %d)\n", pwmBad, flagBad);
  return ok ? 0 : 1;
}
