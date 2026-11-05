"""第 1 期重做视频在 ../ep01/layers.py 之上加的动效（不用视频模型）：

  items  冰箱：从空冰箱（var/3_empty）开始，东西一样一样出现，最后拿走几样
  poses  换姿势：几张只改了猫姿势的变体图轮流换进来（巴掌大的夜）
  away   走远：从空街（var/5a_empty）上把她的身影抠出来，渐显、慢慢往远处走、缩小、渐隐（回家）
  steam  热气：几缕半透明的白气从杯口、瓶口往上飘

  ../../../ucl-video/.venv/bin/python motion.py check     每个镜头抽几帧拼成 build/motion_check.jpg
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ep01"))
import layers as L  # noqa: E402

VAR = os.path.join(HERE, "var")
L.ART = os.path.join(HERE, "vid")
L.SPEC["5a"].pop("rain", None)  # 不下雨了
L.SPEC["6"].pop("blink", None)  # 巴掌大的夜改成换姿势
L.SPEC["5b"]["ripple"] = [(440, 170, 590, 380, 4.0)]
L.SPEC.update({
    "n2": dict(glow=[((130, 60, 580, 520), "pulse")]),
    "n3": dict(glow=[((90, 180, 340, 340), "pulse")]),
})

# 换姿势：(变体图, 区域)、换的时间表 [(起, 第几张)]；第 0 张是原图
POSES = {
    "6": dict(var=["6_up", "6_curl"], box=(220, 380, 620, 730), at=[(0.0, 0), (2.4, 1), (5.0, 2)], fade=0.45),
}
# 身影所在区域；她停在的几个位置（脚下那点挪多少、缩到多大），一处淡出、下一处淡入定住
AWAY = {"5a": dict(box=(440, 150, 860, 1024), stops=[(0, 0, 1.0), (22, -95, 0.78), (40, -170, 0.6)], fade=0.6, gap=0.3, tail=0.9)}
STEAM = {"5b": [(515, 385, 170, 34)]}  # (x, 底边 y, 往上飘多高, 摆幅)


def shift_to(key, v, box, r=16):
    """变体图可能整体挪了几个像素：在区域里找结构最贴合的平移，挪回来。"""
    x0, y0, x1, y1 = box
    K = ndimage.gaussian_gradient_magnitude(key[y0:y1, x0:x1].mean(2), 1.0)
    best = None
    for dy in range(-r, r + 1, 2):
        for dx in range(-r, r + 1, 2):
            V = ndimage.gaussian_gradient_magnitude(v[y0 + dy:y1 + dy, x0 + dx:x1 + dx].mean(2), 1.0)
            if V.shape == K.shape:
                e = np.abs(K - V).mean()
                if best is None or e < best[0]:
                    best = (e, dx, dy)
    return ndimage.shift(v, (-best[2], -best[1], 0), order=1, mode="nearest")


def load_var(name, key, box):
    v = np.asarray(Image.open(os.path.join(VAR, f"{name}.png")).convert("RGB").resize((key.shape[1], key.shape[0]), Image.LANCZOS), np.float32)
    return shift_to(key, v, box)


def diff_mask(key, v, box, thr=24, grow=8):
    x0, y0, x1, y1 = box
    d = ndimage.gaussian_filter(np.abs(key - v).mean(2), 2)
    m = np.zeros(d.shape, bool)
    m[y0:y1, x0:x1] = d[y0:y1, x0:x1] > thr
    m = ndimage.binary_dilation(ndimage.binary_fill_holes(ndimage.binary_dilation(m, iterations=grow)), iterations=grow)
    return m


def soft(m, r=5):
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)[..., None] / 255


class Shot(L.Layered):
    def __init__(self, key, dur, on=None, seed=0):
        super().__init__(key, dur, on=on, seed=seed)
        self.items, self.poses = [], None
        if key == "3":
            self._items()
        if key in POSES:
            p = POSES[key]
            self.poses = [(v, soft(diff_mask(self.a, v, p["box"]))) for v in (load_var(n, self.a, p["box"]) for n in p["var"])]
        self.steam = STEAM.get(key, [])
        self.away = None
        if key in AWAY:
            self._away()
            # 路灯的光晕比“金色像素”大得多（暖色的雾一直铺到地上）：灯灭时把整片偏暖的地方和灯泡一起压暗
            r, b = self.a[..., 0], self.a[..., 2]
            warm = np.clip((r - b - 6) / 25, 0, 1)
            zone = np.zeros_like(warm)
            zone[40:, 380:1200] = 1
            yy, xx = np.mgrid[:self.H, :self.W]
            bulb = (((xx - 868) / 80) ** 2 + ((yy - 160) / 55) ** 2 < 1) & (self.a.mean(2) > 170)
            off = ndimage.gaussian_filter(np.maximum(warm * ndimage.gaussian_filter(zone, 30), bulb), 6)
            self.glows = [((off[..., None], mode) if mode == "on" else (m, mode)) for m, mode in self.glows]

    def _items(self):
        """空冰箱对齐到满的那张；两张差别大的地方按连通块分成一样一样的东西。"""
        box = (120, 120, 910, 1240)
        self.empty = load_var("3_empty", self.a, box)
        m = diff_mask(self.a, self.empty, box, thr=30, grow=3)
        lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=6))
        objs = []
        for i, sl in enumerate(ndimage.find_objects(lab)):
            part = (lab == i + 1) & m
            if part.sum() > 1500:
                cy, cx = ndimage.center_of_mass(part)
                objs.append((cx, cy, soft(ndimage.binary_dilation(part, iterations=3), 3)))
        # 她那半边和它那半边轮流放，从上往下
        left = sorted([o for o in objs if o[0] < 512], key=lambda o: o[1])
        right = sorted([o for o in objs if o[0] >= 512], key=lambda o: o[1])
        order = [o for pair in zip(left, right) for o in pair] + left[len(right):] + right[len(left):]
        k = len(order)
        span = (0.7, max(1.4, self.dur * 0.62))
        gone = {1, k - 2} if k >= 4 else set()  # 最后拿走两样
        for j, (_cx, _cy, mm) in enumerate(order):
            t_in = span[0] + (span[1] - span[0]) * j / max(1, k - 1)
            t_out = self.dur * (0.74 + 0.06 * (j == k - 2)) if j in gone else None
            self.items.append((mm, t_in, t_out))
        print(f"冰箱：{k} 样东西", flush=True)

    def _away(self):
        """空街对齐到原图；两张差别大的那一大块就是她。底图换成空街，她单独贴上去。"""
        p = AWAY[self.key]
        empty = load_var("5a_empty", self.a, p["box"])
        m = diff_mask(self.a, empty, p["box"], thr=28, grow=3)
        lab, n = ndimage.label(m)
        if n:
            m = lab == (np.argmax(ndimage.sum(m, lab, range(1, n + 1))) + 1)
        m = ndimage.binary_fill_holes(m)
        ys, xs = np.nonzero(m)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        rgba = np.dstack([self.a, soft(m, 2)[..., 0] * 255])[y0:y1, x0:x1].clip(0, 255).astype(np.uint8)
        self.away = (Image.fromarray(rgba, "RGBA"), (x0 + x1) / 2, y1)  # 身影、脚下那点
        self.a = empty

    def _stop(self, t):
        """此刻停在第几处、透明度多少：第一处一开场就在，之后每处 淡入 → 定住 → 淡出，中间空一下。"""
        p = AWAY[self.key]
        n, f, g = len(p["stops"]), p["fade"], p["gap"]
        hold = (self.dur - p["tail"] - (2 * n - 1) * f - (n - 1) * g) / n
        t0 = 0.0
        for i in range(n):
            t_in = t0 if i else -f  # 第一处不淡入
            t_out = t_in + f + hold
            if t < t_out + f + g / 2 or i == n - 1:
                return i, L.ease((t - t_in) / f) * (1 - L.ease((t - t_out) / f))
            t0 = t_out + f + g
        return n - 1, 0.0

    def _apply_away(self, im, t):
        fig, fx, fy = self.away
        i, al = self._stop(t)
        if al <= 0:
            return im
        dx, dy, s = AWAY[self.key]["stops"][i]
        w, h = max(1, int(fig.width * s)), max(1, int(fig.height * s))
        f = fig.resize((w, h), Image.LANCZOS)
        if al < 1:
            f.putalpha(f.getchannel("A").point(lambda v: int(v * al)))
        im = im.convert("RGBA")
        im.alpha_composite(f, (int(fx + dx - w / 2), int(fy + dy - h)))
        return im.convert("RGB")

    def _glow(self, a, t):
        """同 layers 的 _glow，只是路灯没亮时整片暖光退成夜色（遮罩见 __init__）。"""
        for m, mode in self.glows:
            if mode == "on":
                f = 0.0 if self.on is None or t < self.on else L.ease((t - self.on) / 0.6)
                if self.on is not None and self.on + 0.15 < t < self.on + 0.28:
                    f *= 0.55
                dark = a.mean(2, keepdims=True) * 0.22
                a = a * (1 - m * (1 - f)) + dark * m * (1 - f)
            else:
                a = a + a * 0.10 * math.sin(2 * math.pi * t / 4.2) * m
        return a

    def _apply_items(self, a, t):
        show = np.zeros(a.shape[:2] + (1,), np.float32)
        for mm, t_in, t_out in self.items:
            w = L.ease((t - t_in) / 0.22)
            if t_out is not None:
                w *= 1 - L.ease((t - t_out) / 0.22)
            show = np.maximum(show, mm * w)
        hide = np.clip(sum(mm for mm, _a, _b in self.items), 0, 1) if self.items else 0
        base = a * (1 - hide) + self.empty * hide  # 先把所有东西都换成空冰箱，再按时间放回去
        return base * (1 - show) + a * show

    def _apply_poses(self, a, t):
        p = POSES[self.key]
        if "step" in p:  # 走路：迈一步、并步、迈另一步、并步
            seq = [1, 0, 2, 0]
            i = int(t / p["step"])
            cur, prev = seq[i % 4], seq[(i - 1) % 4]
            u = L.ease((t - i * p["step"]) / p["fade"])
        else:
            at = p["at"]
            i = max(j for j, (s, _n) in enumerate(at) if s <= t)
            cur, prev = at[i][1], at[i - 1][1] if i else at[i][1]
            u = L.ease((t - at[i][0]) / p["fade"])

        def img(n):
            return a if n == 0 else a * (1 - self.poses[n - 1][1]) + self.poses[n - 1][0] * self.poses[n - 1][1]
        return img(prev) * (1 - u) + img(cur) * u if prev != cur else img(cur)

    def _steam(self, im, t):
        if not self.steam:
            return im
        lay = Image.new("RGBA", im.size)
        d = ImageDraw.Draw(lay)
        for x, y, h, amp in self.steam:
            for s in range(3):
                ph = s * 2.1
                pts = []
                for q in range(40):
                    u = q / 39  # 0 在杯口，1 在最高处
                    yy = y - h * u
                    xx = x + (s - 1) * 10 + amp * u * math.sin(2 * math.pi * (u * 1.3 - t / 2.6) + ph)
                    pts.append((xx, yy))
                rise = (t / 2.6 + s / 3) % 1  # 每缕气一段一段往上走
                for q in range(39):
                    u = q / 39
                    al = int(110 * math.sin(math.pi * u) * (0.55 + 0.45 * math.sin(2 * math.pi * (u - rise))))
                    if al > 4:
                        d.line([pts[q], pts[q + 1]], fill=(255, 250, 240, al), width=int(9 - 4 * u))
        lay = lay.filter(ImageFilter.GaussianBlur(4))
        im = im.convert("RGBA")
        im.alpha_composite(lay)
        return im.convert("RGB")

    def frame(self, t):
        a = self.a.copy()
        if self.items:
            a = self._apply_items(a, t)
        if self.poses:
            a = self._apply_poses(a, t)
        a = self._blink(a, t)
        a = self._warp(a, t)
        a = self._glow(a, t)
        im = self._steam(self._overlay(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), t), t)
        return self._apply_away(im, t) if self.away else im


def check():
    rows = []
    for k, ts in {"3": [0.3, 1.5, 2.6, 3.8, 5.6], "5a": [0.3, 1.5, 3.0, 4.5, 6.2], "5b": [0, 0.7, 1.4, 2.1, 2.8],
                  "6": [1.0, 2.5, 3.5, 5.3, 6.5]}.items():
        sh = Shot(k, 7.0, on=2.0)
        ims = [sh.frame(t).resize((300, int(300 * sh.H / sh.W))) for t in ts]
        row = Image.new("RGB", (1500, 450), "black")
        for i, im in enumerate(ims):
            row.paste(im, (i * 300, 0))
        rows.append(row)
    out = Image.new("RGB", (1500, 450 * len(rows)))
    for i, r in enumerate(rows):
        out.paste(r, (0, i * 450))
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    out.save(os.path.join(HERE, "build", "motion_check.jpg"), quality=85)


if __name__ == "__main__":
    {"check": check}[sys.argv[1]]()
