"""和夜一起住 · 第 1 期视频的“分层动效”镜头：原图不动，只让画里已有的东西小幅动起来（不用视频模型）。

  ../../../ucl-video/.venv/bin/python layers.py gen      生成眨眼变体图并对齐（variants/，有缓存）
  ../../../ucl-video/.venv/bin/python layers.py check    每个镜头抽几帧拼成 build/layers_check.jpg

每个镜头能用的动作（坐标是插画像素，竖图 1024×1536、横图 1536×1024）：
  blink   gpt-image 改出“只闭上眼”的整图，配准回原图后只取眼睛那一小块，按时间淡入淡出（猫是慢眨眼）
  breathe 一块椭圆区域以底边为轴轻轻伸缩，像呼吸
  ripple  一块区域里横向的细波纹往上走：画好的热气、树叶轻轻飘
  glow    区域里金色的像素一起变亮变暗；mode="on" 时先暗着，到 on 秒亮起来（路灯）
  twinkle 区域里本来就有的小金星，一颗颗轮流闪一下
  rain    整屏往下落的细雨丝
"""
import math
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "clip10"))
import assets as base  # noqa: E402

ART = os.path.join(HERE, "art_C")
VAR = os.path.join(HERE, "variants")
KEEP = "其他所有东西一点都不要改：构图、线条、画风、黑白和金色、人物和猫的位置大小完全一样。画面里不要任何文字。"
CAT_EYES = "同一张图，只把黑猫的眼睛闭上（安详地闭眼，眼睛变成两道弯弯的细线）。"
GIRL_EYES = "同一张图，只把女孩的眼睛闭上（自然地眨眼，眼睛变成两道弯弯的线），表情其余部分不变。"

SPEC = {
    "1": dict(blink=[("cat", CAT_EYES, (300, 560, 640, 840))],
              breathe=[(230, 900, 260, 300)], glow=[((660, 400, 900, 660), "pulse")], twinkle=[(0, 500, 460, 1200)]),
    "2": dict(blink=[("cat", CAT_EYES, (180, 380, 420, 600)), ("girl", GIRL_EYES, (600, 280, 860, 480))],
              breathe=[(230, 700, 160, 230)], ripple=[(480, 580, 600, 705, 2.5), (0, 100, 130, 420, 1.5)], twinkle=[(40, 830, 300, 960)]),
    "3": dict(glow=[((440, 180, 820, 1020), "pulse")], twinkle=[(580, 600, 780, 830)]),
    "4": dict(blink=[("cat", CAT_EYES, (330, 900, 620, 1130)), ("girl", GIRL_EYES, (470, 60, 730, 270))],
              breathe=[(470, 1180, 170, 260)]),
    "5a": dict(glow=[((700, 80, 1120, 1000), "on")], rain=True, ripple=[(0, 0, 680, 320, 1.2)]),
    "5b": dict(ripple=[(440, 170, 590, 380, 2.5)], glow=[((0, 0, 430, 1024), "pulse")]),
    "6": dict(blink=[("cat", "同一张图，只把女孩手心里小黑猫的眼睛闭上（安详地闭眼）。", (290, 440, 540, 660))],
              breathe=[(400, 560, 120, 85)], ripple=[(0, 0, 210, 620, 1.2)]),
    "7": dict(blink=[("cat", "同一张图，只把女孩衬衫口袋里小黑猫的眼睛睁开（金色的圆眼睛，好奇地往外看一眼）。", (590, 570, 830, 770))],
              ripple=[(270, 410, 450, 615, 2.5), (0, 0, 400, 230, 1.2)], glow=[((0, 0, 520, 520), "pulse")]),
    "8": dict(blink=[("cat", CAT_EYES, (380, 340, 640, 570))],
              breathe=[(420, 880, 480, 600)], ripple=[(380, 670, 510, 810, 2.5)],
              glow=[((740, 480, 1024, 640), "pulse"), ((140, 160, 280, 340), "pulse")], twinkle=[(740, 1130, 1024, 1360)]),
    "9": dict(blink=[("cat", CAT_EYES, (325, 650, 480, 785))],
              breathe=[(330, 920, 170, 270)], glow=[((340, 350, 570, 570), "pulse")], twinkle=[(170, 1040, 460, 1260)]),
}


def ease(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


# ------------------------------------------------------------------ 变体图
def gen():
    os.makedirs(VAR, exist_ok=True)
    jobs = []
    for k, s in SPEC.items():
        src = os.path.join(ART, f"{k}.png")
        w, h = Image.open(src).size
        for who, prompt, _box in s.get("blink", []):
            out = os.path.join(VAR, f"{k}_{who}_raw.png")
            if not os.path.exists(out):
                jobs.append((prompt + KEEP, [src], out, f"{w}x{h}"))
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda a: base.edit(*a), jobs))
    for k, s in SPEC.items():
        for who, _p, box in s.get("blink", []):
            align(k, who, box)


def _grad(a):
    return ndimage.gaussian_gradient_magnitude(a, 1.0)


def align(k, who, box):
    """变体图可能整体挪了几个像素：在眼睛那块附近找最贴合的平移，再只取两图差别大的地方当遮罩。"""
    out = os.path.join(VAR, f"{k}_{who}.png")
    if os.path.exists(out):
        return
    key = np.asarray(Image.open(os.path.join(ART, f"{k}.png")).convert("RGB"), np.float32)
    var = Image.open(os.path.join(VAR, f"{k}_{who}_raw.png")).convert("RGB").resize((key.shape[1], key.shape[0]), Image.LANCZOS)
    v = np.asarray(var, np.float32)
    x0, y0, x1, y1 = box
    pad = 40
    K = _grad(key[y0:y1, x0:x1].mean(2))
    best = None
    for dy in range(-12, 13, 2):
        for dx in range(-12, 13, 2):
            V = _grad(v[y0 + dy:y1 + dy, x0 + dx:x1 + dx].mean(2))
            if V.shape != K.shape:
                continue
            # 用整块的结构比（眼睛本身变了，但头的轮廓、胡须没变）
            e = np.abs(K - V).mean()
            if best is None or e < best[0]:
                best = (e, dx, dy)
    _, dx, dy = best
    v = ndimage.shift(v, (-dy, -dx, 0), order=1, mode="nearest")
    diff = ndimage.gaussian_filter(np.abs(key - v).mean(2), 2)
    m = np.zeros(diff.shape, bool)
    m[y0:y1, x0:x1] = diff[y0:y1, x0:x1] > 22
    if who == "cat":  # 黑猫的眼睛是金色的：只认金色有变化的地方，免得把毛的细微差别也换进来
        m &= ndimage.binary_dilation((gold(key) > 0.3) | (gold(v) > 0.3), iterations=3)
        m = ndimage.binary_dilation(m, iterations=6)
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=6))
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = [i + 1 for i in np.argsort(sizes)[::-1][:2] if sizes[i] > 30]
        m = np.isin(lab, keep)
    m = ndimage.binary_dilation(ndimage.binary_fill_holes(m), iterations=6)
    a = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)))
    rgba = np.dstack([v.clip(0, 255).astype(np.uint8), a])
    Image.fromarray(rgba, "RGBA").save(out)
    print(k, who, "shift", dx, dy, "mask px", int(m.sum()), flush=True)


# ------------------------------------------------------------------ 镜头
def gold(a):
    """每个像素有多“金”：红明显高过蓝。"""
    return np.clip((a[..., 0] - a[..., 2] - 35) / 70, 0, 1) * np.clip((a[..., 0] - 90) / 80, 0, 1)


class Layered:
    def __init__(self, key, dur, on=None, seed=0):
        self.key, self.dur = key, dur
        self.spec = SPEC.get(key, {})
        self.src = Image.open(os.path.join(ART, f"{key}.png")).convert("RGB")
        self.a = np.asarray(self.src, np.float32)
        self.H, self.W = self.a.shape[:2]
        rnd = random.Random(seed * 31 + len(key))
        self.blinks = []
        for who, _p, _b in self.spec.get("blink", []):
            path = os.path.join(VAR, f"{key}_{who}.png")
            if not os.path.exists(path):
                continue
            v = np.asarray(Image.open(path), np.float32)
            slow = who == "cat"  # 猫的慢眨眼：闭 0.35 秒、停 0.5 秒、睁 0.35 秒
            times, t = [], rnd.uniform(1.4, 2.4)
            while t < dur - 1.2:
                times.append(t)
                t += rnd.uniform(3.6, 5.0) if slow else rnd.uniform(2.6, 3.8)
            self.blinks.append((v[..., :3], v[..., 3:] / 255, times, slow))
        self.on = on
        self.glows = []
        g = gold(self.a)
        for (x0, y0, x1, y1), mode in self.spec.get("glow", []):
            m = np.zeros_like(g)
            m[y0:y1, x0:x1] = g[y0:y1, x0:x1]
            self.glows.append((ndimage.gaussian_filter(m, 3)[..., None], mode))
        self.stars = []
        for x0, y0, x1, y1 in self.spec.get("twinkle", []):
            sub = (g[y0:y1, x0:x1] > 0.5) & (self.a[y0:y1, x0:x1, 0] > 190)
            lab, n = ndimage.label(sub)
            for i, sl in enumerate(ndimage.find_objects(lab)):
                area = int((lab[sl] == i + 1).sum())
                if 4 <= area <= 900:
                    cy, cx = (sl[0].start + sl[0].stop) / 2 + y0, (sl[1].start + sl[1].stop) / 2 + x0
                    self.stars.append((cx, cy, 6 + 2.2 * math.sqrt(area), rnd.uniform(0, 3.0)))
        self.stars = sorted(self.stars, key=lambda s: -s[2])[:14]
        self.rain = [(rnd.uniform(-100, self.W), rnd.uniform(0, self.H), rnd.uniform(26, 58), rnd.uniform(0.8, 1.25), rnd.randint(50, 110))
                     for _ in range(260)] if self.spec.get("rain") else []

    # 小动作 --------------------------------------------------------------
    def _blink(self, a, t):
        for v, m, times, slow in self.blinks:
            w = 0.0
            for b in times:
                u = t - b
                if slow:
                    w = max(w, ease(u / 0.35) if u < 0.35 else 1.0 if u < 0.85 else 1 - ease((u - 0.85) / 0.35))
                else:
                    w = max(w, ease(u / 0.05) if u < 0.05 else 1.0 if u < 0.12 else 1 - ease((u - 0.12) / 0.06))
            if w > 0:
                a = a * (1 - m * w) + v * m * w
        return a

    def _warp(self, a, t):
        """呼吸 + 波纹：都是一小块区域里的位移场，只在那块里重采样。"""
        for i, (cx, cy, rx, ry) in enumerate(self.spec.get("breathe", [])):
            x0, x1 = int(max(0, cx - rx)), int(min(self.W, cx + rx))
            y0, y1 = int(max(0, cy - ry)), int(min(self.H, cy + ry))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            w = np.clip(1 - ((xx - cx) / rx) ** 2 - ((yy - cy) / ry) ** 2, 0, 1) ** 1.5
            s = 0.006 * math.sin(2 * math.pi * t / 3.6 + i)  # 3.6 秒一呼一吸，幅度 0.6%
            sy = yy - (yy - (cy + ry)) * s * w
            a[y0:y1, x0:x1] = np.stack([ndimage.map_coordinates(a[..., c], [sy, xx], order=1, mode="nearest") for c in range(3)], -1)
        for x0, y0, x1, y1, amp in self.spec.get("ripple", []):
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            ex = np.sin(np.clip((xx - x0) / (x1 - x0), 0, 1) * math.pi)
            ey = np.sin(np.clip((yy - y0) / (y1 - y0), 0, 1) * math.pi)
            lam = 46 if amp > 2 else 90
            dx = amp * np.sin(2 * math.pi * ((yy / lam) + t / (1.8 if amp > 2 else 3.2))) * ex * ey
            a[y0:y1, x0:x1] = np.stack([ndimage.map_coordinates(a[..., c], [yy, xx + dx], order=1, mode="nearest") for c in range(3)], -1)
        return a

    def _glow(self, a, t):
        for m, mode in self.glows:
            if mode == "on":  # 路灯：先暗着（金色退成灰黑），到 on 秒用 0.6 秒亮起来，亮的时候闪一下
                f = 0.0 if self.on is None or t < self.on else ease((t - self.on) / 0.6)
                if self.on is not None and self.on + 0.15 < t < self.on + 0.28:
                    f *= 0.55
                dark = a.mean(2, keepdims=True) * 0.28
                a = a * (1 - m * (1 - f)) + dark * m * (1 - f)
            else:
                k = 0.10 * math.sin(2 * math.pi * t / 4.2)
                a = a + (a * k) * m
        return a

    def _overlay(self, im, t):
        if not (self.stars or self.rain):
            return im
        L = Image.new("RGBA", im.size)
        d = ImageDraw.Draw(L)
        for x, y, r, ph in self.stars:
            u = (t + ph) % 3.0
            if u > 0.9:
                continue
            k = math.sin(u / 0.9 * math.pi)
            R = r * (0.4 + 0.6 * k)
            d.polygon([(x, y - R), (x + R * 0.18, y - R * 0.18), (x + R, y), (x + R * 0.18, y + R * 0.18), (x, y + R),
                       (x - R * 0.18, y + R * 0.18), (x - R, y), (x - R * 0.18, y - R * 0.18)], fill=(255, 232, 160, int(230 * k)))
        for x, y, ln, v, al in self.rain:
            yy = (y + t * 1500 * v) % (self.H + 80) - 40
            xx = x + (yy - y) * 0.06
            d.line((xx, yy, xx + ln * 0.06, yy + ln), fill=(235, 235, 240, al), width=2)
        im = im.convert("RGBA")
        im.alpha_composite(L)
        return im.convert("RGB")

    def frame(self, t):
        a = self.a.copy()
        a = self._blink(a, t)
        a = self._warp(a, t)
        a = self._glow(a, t)
        return self._overlay(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), t)


def check():
    rows = []
    for k in SPEC:
        sh = Layered(k, 8.0, on=3.0)
        ts = [0.0] + [b + 0.6 for _v, _m, times, _s in sh.blinks for b in times[:1]] + [2.6, 3.4, 4.5]
        ims = [sh.frame(t).resize((300, int(300 * sh.H / sh.W))) for t in ts[:5]]
        row = Image.new("RGB", (300 * 5, 450), "black")
        for i, im in enumerate(ims):
            row.paste(im, (i * 300, 0))
        rows.append(row)
    sheet = Image.new("RGB", (1500, 450 * len(rows)))
    for i, r in enumerate(rows):
        sheet.paste(r, (0, i * 450))
    sheet.save(os.path.join(HERE, "build", "layers_check.jpg"), quality=85)


if __name__ == "__main__":
    {"gen": gen, "check": check}[sys.argv[1]]()
