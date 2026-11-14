#!/usr/bin/env python3
"""ai-happy-01 entry: a golden morning sunshine scene.

Pure Python 3.13 standard library only. No external images, no network,
no randomness -- every run produces the exact same PNG bytes.

Scene: a big smiling sun in a warm golden sky, a joyful puppy and a
kitten playing together among colourful flowers, butterflies, a rainbow
and fluffy clouds. Drawn entirely in code, pixel by pixel.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024


def rgb(r, g, b):
    return (r, g, b)


# ---- palette -----------------------------------------------------------
SKY_TOP = rgb(112, 190, 246)
SKY_MID = rgb(178, 224, 250)
SKY_LOW = rgb(255, 228, 158)
SUN_GLOW = rgb(255, 238, 150)
SUN_CORE = rgb(255, 214, 64)
SUN_RAY = rgb(255, 196, 0)
CLOUD = rgb(255, 255, 255)
CLOUD_SHADE = rgb(214, 235, 250)
HILL_BACK = rgb(96, 176, 84)
HILL_FRONT = rgb(124, 205, 92)
GRASS_DARK = rgb(74, 154, 66)
RAINBOW = [
    rgb(255, 89, 89),    # red
    rgb(255, 159, 67),   # orange
    rgb(255, 214, 64),   # yellow
    rgb(96, 205, 110),   # green
    rgb(84, 160, 255),   # blue
    rgb(178, 120, 235),  # purple
]
PUPPY = rgb(233, 169, 94)
PUPPY_DARK = rgb(138, 90, 43)
PUPPY_CREAM = rgb(255, 242, 217)
KITTEN = rgb(255, 158, 74)
KITTEN_DARK = rgb(214, 110, 30)
INK = rgb(58, 42, 30)
PINK = rgb(255, 122, 158)
BLUSH = rgb(255, 158, 158)
STEM = rgb(56, 142, 60)
LEAF = rgb(76, 175, 80)


class Canvas:
    """A plain RGB pixel buffer with small filled-shape primitives."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _clip_x(self, x0, x1):
        return max(0, x0), min(self.w, x1)

    def hspan(self, y, x0, x1, c):
        """Fill one horizontal run (clipped)."""
        if y < 0 or y >= self.h:
            return
        x0, x1 = self._clip_x(x0, x1)
        if x1 <= x0:
            return
        base = (y * self.w + x0) * 3
        row = bytes(c) * (x1 - x0)
        self.buf[base:base + len(row)] = row

    def fill_rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1)):
            self.hspan(y, x0, x1, c)

    def disc(self, cx, cy, r, c):
        """Filled circle, row by row."""
        r = int(r)
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hspan(y, cx - dx, cx + dx + 1, c)

    def ellipse(self, cx, cy, rx, ry, c):
        """Filled ellipse, row by row."""
        rx = int(rx)
        ry = int(ry)
        for y in range(cy - ry, cy + ry + 1):
            dy = y - cy
            if ry == 0:
                continue
            t = 1.0 - (dy * dy) / float(ry * ry)
            if t < 0:
                continue
            dx = int(rx * math.sqrt(t))
            self.hspan(y, cx - dx, cx + dx + 1, c)

    def thick_line(self, x0, y0, x1, y1, width, c):
        """A line drawn as a chain of small discs (round caps)."""
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 2
        rad = max(1, width // 2)
        for i in range(steps + 1):
            t = i / float(steps)
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            self.disc(x, y, rad, c)

    def arc_discs(self, cx, cy, radius, a0_deg, a1_deg, dot_r, c):
        """Thick arc made of discs along the angle range."""
        steps = int(abs(a1_deg - a0_deg) * 2) + 2
        for i in range(steps + 1):
            a = math.radians(a0_deg + (a1_deg - a0_deg) * i / float(steps))
            x = int(round(cx + radius * math.cos(a)))
            y = int(round(cy + radius * math.sin(a)))
            self.disc(x, y, dot_r, c)

    def polygon(self, points, c):
        """Filled polygon via a scanline fill."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / float(y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.hspan(y, int(math.ceil(xs[j])), int(math.floor(xs[j + 1])) + 1, c)

    def arc_band(self, cx, cy, r_outer, r_inner, c):
        """One band of a rainbow: the upper half of an annulus."""
        for y in range(cy - r_outer, cy + 1):
            dy = cy - y
            if dy < 0:
                continue
            oo = r_outer * r_outer - dy * dy
            ii = r_inner * r_inner - dy * dy
            if oo < 0:
                continue
            dx_o = int(math.sqrt(oo))
            dx_i = int(math.sqrt(ii)) if ii > 0 else 0
            self.hspan(y, cx - dx_o, cx - dx_i + 1, c)
            self.hspan(y, cx + dx_i, cx + dx_o + 1, c)

    def heart(self, cx, cy, s, c):
        self.disc(cx - s // 2, cy - s // 4, s // 2, c)
        self.disc(cx + s // 2, cy - s // 4, s // 2, c)
        self.polygon([(cx - s, cy - s // 6), (cx + s, cy - s // 6),
                      (cx, cy + s)], c)

    def sparkle(self, cx, cy, s, c):
        self.polygon([(cx, cy - s), (cx + s // 3, cy - s // 3),
                      (cx + s, cy), (cx + s // 3, cy + s // 3),
                      (cx, cy + s), (cx - s // 3, cy + s // 3),
                      (cx - s, cy), (cx - s // 3, cy - s // 3)], c)

    def eye(self, cx, cy, r, pupil=rgb(30, 30, 30)):
        self.disc(cx, cy, r, pupil)
        self.disc(cx - r // 3, cy - r // 3, max(2, r // 3), rgb(255, 255, 255))


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def draw_sky(cv):
    """Warm vertical gradient: blue morning sky melting into gold."""
    cv.fill_rect(0, 0, W, H, SKY_LOW)  # base so no pixel stays black
    for y in range(0, 760):
        if y < 380:
            c = lerp(SKY_TOP, SKY_MID, y / 380.0)
        else:
            c = lerp(SKY_MID, SKY_LOW, (y - 380) / 380.0)
        cv.hspan(y, 0, W, c)


def draw_rainbow(cv):
    cx, cy = 512, 780
    outer = 400
    band = 28
    for i, col in enumerate(RAINBOW):
        r_out = outer - i * band
        r_in = r_out - band
        cv.arc_band(cx, cy, r_out, r_in, col)


def draw_sun(cv):
    cx, cy = 215, 195
    # rays: twelve triangles fanning out
    for k in range(12):
        a = math.radians(k * 30.0)
        tip_r = 185 if k % 2 == 0 else 165
        base_r = 118
        ax, ay = cx + base_r * math.cos(a - 0.10), cy + base_r * math.sin(a - 0.10)
        bx, by = cx + base_r * math.cos(a + 0.10), cy + base_r * math.sin(a + 0.10)
        tx, ty = cx + tip_r * math.cos(a), cy + tip_r * math.sin(a)
        cv.polygon([(int(ax), int(ay)), (int(bx), int(by)),
                    (int(tx), int(ty))], SUN_RAY)
    cv.disc(cx, cy, 138, SUN_GLOW)
    cv.disc(cx, cy, 112, SUN_CORE)
    # happy face
    cv.eye(cx - 38, cy - 18, 11)
    cv.eye(cx + 38, cy - 18, 11)
    cv.arc_discs(cx, cy + 8, 46, 25, 155, 7, INK)  # big smile
    cv.disc(cx - 66, cy + 26, 15, BLUSH)
    cv.disc(cx + 66, cy + 26, 15, BLUSH)


def draw_cloud(cv, cx, cy, s):
    """One fluffy cloud: a row of overlapping discs, flat bottom."""
    cv.ellipse(cx, cy + 8, int(2.6 * s), int(0.9 * s), CLOUD_SHADE)
    for dx, r in ((-2 * s, s), (-s, int(1.4 * s)), (0, int(1.6 * s)),
                  (s, int(1.35 * s)), (2 * s, int(0.95 * s))):
        cv.disc(cx + dx, cy, r, CLOUD)
    cv.fill_rect(cx - int(2.6 * s), cy, cx + int(2.6 * s), cy + int(0.9 * s), CLOUD)


def draw_hills(cv):
    cv.ellipse(180, 1060, 720, 330, HILL_BACK)
    cv.ellipse(880, 1090, 680, 320, HILL_BACK)
    cv.ellipse(512, 1150, 780, 330, HILL_FRONT)
    # grass tufts
    for x, y, h in ((90, 950, 22), (170, 990, 18), (930, 940, 20),
                    (860, 1000, 18), (60, 1010, 16), (980, 990, 16)):
        cv.thick_line(x, y, x - 6, y - h, 4, GRASS_DARK)
        cv.thick_line(x, y, x + 6, y - h, 4, GRASS_DARK)


FLOWER_SPOTS = [
    (70, 880, rgb(255, 89, 89), 1.0), (150, 940, rgb(255, 255, 255), 0.9),
    (240, 870, rgb(255, 159, 67), 1.0), (300, 960, rgb(178, 120, 235), 0.9),
    (480, 950, rgb(255, 89, 150), 1.0), (560, 880, rgb(255, 255, 255), 0.9),
    (760, 950, rgb(255, 89, 89), 1.0), (830, 890, rgb(255, 159, 67), 0.95),
    (920, 960, rgb(255, 89, 150), 1.0), (980, 880, rgb(178, 120, 235), 0.9),
    (110, 800, rgb(255, 214, 64), 0.8), (900, 810, rgb(255, 89, 150), 0.8),
    (610, 980, rgb(255, 214, 64), 0.9), (40, 960, rgb(255, 159, 67), 0.85),
]


def draw_flower(cv, x, y, petal, s):
    stem_h = int(58 * s)
    cv.thick_line(x, y, x, y - stem_h, 5, STEM)
    cv.ellipse(x - 12, y - int(26 * s), 14, 6, LEAF)
    cx, cy = x, y - stem_h - 12
    for k in range(6):
        a = math.radians(k * 60.0)
        px = cx + int(20 * s * math.cos(a))
        py = cy + int(20 * s * math.sin(a))
        cv.disc(px, py, int(13 * s), petal)
    cv.disc(cx, cy, int(12 * s), rgb(255, 196, 0))
    cv.disc(cx - 3, cy - 3, 4, rgb(255, 236, 170))


def draw_puppy(cv):
    # tail wagging up behind the body
    cv.arc_discs(478, 830, 52, 250, 350, 9, PUPPY_DARK)
    # body, chest and paws
    cv.ellipse(390, 862, 96, 72, PUPPY)
    cv.ellipse(390, 838, 42, 34, rgb(158, 104, 52))  # patch
    cv.ellipse(390, 872, 58, 48, PUPPY_CREAM)
    cv.ellipse(348, 922, 30, 17, PUPPY_CREAM)
    cv.ellipse(432, 922, 30, 17, PUPPY_CREAM)
    # floppy ears behind the head
    cv.ellipse(332, 758, 24, 52, PUPPY_DARK)
    cv.ellipse(448, 758, 24, 52, PUPPY_DARK)
    # head, muzzle, nose, tongue
    cv.disc(390, 748, 64, PUPPY)
    cv.ellipse(390, 772, 40, 28, PUPPY_CREAM)
    cv.ellipse(390, 756, 17, 12, INK)
    cv.ellipse(390, 800, 15, 19, PINK)
    cv.thick_line(390, 784, 390, 800, 3, rgb(200, 60, 90))
    cv.eye(364, 734, 10)
    cv.eye(416, 734, 10)
    cv.disc(364, 718, 5, PUPPY_DARK)
    cv.disc(416, 718, 5, PUPPY_DARK)


def draw_kitten(cv):
    # tail curling up on the left
    cv.arc_discs(586, 838, 48, 90, 260, 9, KITTEN_DARK)
    # body and paws
    cv.ellipse(652, 868, 72, 54, KITTEN)
    cv.ellipse(652, 878, 44, 34, rgb(255, 214, 160))
    cv.ellipse(622, 916, 24, 14, rgb(255, 214, 160))
    cv.ellipse(682, 916, 24, 14, rgb(255, 214, 160))
    # stripes on the body
    for dx in (-34, 0, 34):
        cv.thick_line(652 + dx, 828, 652 + dx, 856, 6, KITTEN_DARK)
    # ears (triangles with pink inner ears)
    cv.polygon([(614, 756), (628, 706), (652, 748)], KITTEN)
    cv.polygon([(690, 756), (676, 706), (652, 748)], KITTEN)
    cv.polygon([(624, 748), (630, 722), (644, 742)], PINK)
    cv.polygon([(680, 748), (674, 722), (660, 742)], PINK)
    # head
    cv.disc(652, 782, 50, KITTEN)
    cv.thick_line(632, 742, 632, 760, 5, KITTEN_DARK)
    cv.thick_line(652, 738, 652, 756, 5, KITTEN_DARK)
    cv.thick_line(672, 742, 672, 760, 5, KITTEN_DARK)
    # green eyes, pink nose, whiskers, smile
    cv.eye(632, 776, 9, rgb(34, 139, 34))
    cv.eye(672, 776, 9, rgb(34, 139, 34))
    cv.polygon([(646, 794), (658, 794), (652, 802)], PINK)
    cv.arc_discs(652, 792, 14, 30, 150, 4, INK)
    for sx in (-1, 1):
        for dy in (-4, 2, 8):
            cv.thick_line(652 + sx * 34, 796 + dy, 652 + sx * 62, 792 + dy, 2,
                          rgb(255, 255, 255))


def draw_butterfly(cv, cx, cy, s, wing, wing2):
    cv.ellipse(cx - int(20 * s), cy - int(10 * s), int(20 * s), int(14 * s), wing)
    cv.ellipse(cx + int(20 * s), cy - int(10 * s), int(20 * s), int(14 * s), wing)
    cv.ellipse(cx - int(14 * s), cy + int(12 * s), int(13 * s), int(10 * s), wing2)
    cv.ellipse(cx + int(14 * s), cy + int(12 * s), int(13 * s), int(10 * s), wing2)
    cv.disc(cx - int(20 * s), cy - int(10 * s), int(6 * s), rgb(255, 255, 255))
    cv.disc(cx + int(20 * s), cy - int(10 * s), int(6 * s), rgb(255, 255, 255))
    cv.thick_line(cx, cy - 16, cx, cy + 18, 5, INK)
    cv.thick_line(cx - 2, cy - 16, cx - 12, cy - 30, 3, INK)
    cv.thick_line(cx + 2, cy - 16, cx + 12, cy - 30, 3, INK)


def draw_bird(cv, cx, cy, s):
    cv.arc_discs(cx - int(12 * s), cy, int(12 * s), 200, 340, 4, INK)
    cv.arc_discs(cx + int(12 * s), cy, int(12 * s), 200, 340, 4, INK)


def render():
    cv = Canvas(W, H)
    draw_sky(cv)
    draw_rainbow(cv)
    draw_sun(cv)
    draw_cloud(cv, 660, 150, 26)
    draw_cloud(cv, 880, 260, 20)
    draw_cloud(cv, 470, 300, 17)
    draw_hills(cv)
    for x, y, petal, s in FLOWER_SPOTS:
        draw_flower(cv, x, y, petal, s)
    draw_puppy(cv)
    draw_kitten(cv)
    draw_butterfly(cv, 830, 330, 1.0, rgb(255, 122, 158), rgb(255, 190, 210))
    draw_butterfly(cv, 170, 470, 0.85, rgb(84, 160, 255), rgb(150, 200, 255))
    draw_butterfly(cv, 560, 180, 0.8, rgb(255, 214, 64), rgb(255, 236, 170))
    draw_bird(cv, 480, 130, 1.0)
    draw_bird(cv, 560, 100, 0.8)
    draw_bird(cv, 760, 90, 0.7)
    cv.heart(520, 640, 22, PINK)
    cv.heart(300, 610, 16, rgb(255, 150, 180))
    cv.sparkle(340, 330, 14, rgb(255, 255, 255))
    cv.sparkle(720, 420, 12, rgb(255, 255, 255))
    cv.sparkle(90, 300, 11, rgb(255, 236, 170))
    return cv.buf


def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(rgb_bytes, w, h):
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter: none
        raw += rgb_bytes[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    png = encode_png(render(), W, H)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print(f"wrote {path} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
