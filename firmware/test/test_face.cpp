// Host test: the firmware face drawing must match the images drawn by the simulator.
// Reads golden/face_frames.txt and compares every pixel of every mood / look / blink combination.
#include <cstdio>
#include <cstring>
#include <string>
#include "../balance_bot/include/face.h"

static bb::Mood moodFrom(const char* s) {
  if (!std::strcmp(s, "idle")) return bb::Mood::Idle;
  if (!std::strcmp(s, "happy")) return bb::Mood::Happy;
  if (!std::strcmp(s, "careful")) return bb::Mood::Careful;
  if (!std::strcmp(s, "worried")) return bb::Mood::Worried;
  if (!std::strcmp(s, "surprised")) return bb::Mood::Surprised;
  if (!std::strcmp(s, "dizzy")) return bb::Mood::Dizzy;
  return bb::Mood::Sleepy;
}

int main(int argc, char** argv) {
  const char* path = argc > 1 ? argv[1] : "golden/face_frames.txt";
  FILE* f = std::fopen(path, "r");
  if (!f) { std::printf("FAIL cannot open %s\n", path); return 1; }
  static char line[4096];
  int frames = 0, bad = 0; long diffPixels = 0, litPixels = 0;
  while (std::fgets(line, sizeof line, f)) {
    if (line[0] == '#') continue;
    char mood[16]; float look, lookv, blink; int off = 0;
    if (std::sscanf(line, "%15s %f %f %f %n", mood, &look, &lookv, &blink, &off) < 4) continue;
    const char* hex = line + off;
    bb::Face face; face.look = look; face.lookv = lookv;
    face.draw(moodFrom(mood), blink);
    long diff = 0;
    for (int i = 0; i < bb::Face::W * bb::Face::H; i++) {
      const char ch = hex[i / 4];
      const int nib = ch >= 'a' ? ch - 'a' + 10 : ch - '0';
      const int ref = (nib >> (3 - i % 4)) & 1;
      if (ref) litPixels++;
      if (ref != (face.img[i] ? 1 : 0)) diff++;
    }
    diffPixels += diff; frames++;
    if (diff > 12) { bad++; std::printf("  %s look=%.1f lookv=%.1f blink=%.1f: %ld pixels differ\n", mood, look, lookv, blink, diff); }
  }
  std::fclose(f);
  std::printf("%d frames, %ld lit reference pixels, %ld differing pixels in total\n", frames, litPixels, diffPixels);
  // float32 vs double can flip a pixel on a shape edge; anything beyond a handful per frame is a real difference
  const bool ok = frames == 28 && bad == 0;
  std::printf(ok ? "PASS face matches the simulator\n" : "FAIL face differs from the simulator\n");
  return ok ? 0 : 1;
}
