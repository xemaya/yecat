"""第 2 期的分层动效，在 ../ep01/layers.py 上加：

  glow 的 ("on", 起, 用时)：区域里的金光先暗着，到“起”秒用“用时”慢慢亮起来，亮了以后轻轻呼吸
    （P6：先亮掌心的星，再亮弯臂上那双眼睛）
  ("on", 起, 用时, "lum")：不只金色，区域里所有亮的线（白色的月牙、耳朵轮廓）都先全黑
  ("on", 起, 用时, "flicker") / "flicker"：星的光忽明忽暗，不是匀速呼吸（用户 11-05 要求）
  PUSH：某个时刻起很慢地往一个点推近（P6 眼睛亮了以后推向弯臂，眼睛在手机上太小）

第 1 期重做的 ../ep01r/motion.py 按第 1 期的镜头编号写死了冰箱、换姿势、走远，这里不继承它，用到时再借它的函数。

  ../../../ucl-video/.venv/bin/python motion.py check     每个镜头抽几帧拼成 build/motion_check.jpg
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ep01"))
import layers as L  # noqa: E402

L.ART = os.path.join(HERE, "art")
L.SPEC.clear()
L.SPEC.update({
    "1": dict(glow=[((380, 330, 660, 600), "flicker")]),  # 灯罩里的星光
    "5a": dict(glow=[((400, 220, 1210, 730), "flicker")]),  # 星把灯罩里照亮，一起忽明忽暗
    "6": dict(glow=[((440, 380, 700, 640), ("on", 0.5, 1.8, "flicker")), ((470, 90, 830, 228), ("on", 3.4, 2.2, "lum"))]),
    "7": dict(glow=[((464, 600, 694, 820), "flicker")], twinkle=[(664, 420, 904, 720)]),  # 掌心的星；尾尖闪（图已左右翻转，灯杆在右）
})

PUSH = {"6": dict(at=3.4, secs=8.0, zoom=1.08, center=(600, 200))}  # 起、用时、推到多大、朝哪一点


def flicker(t, seed=0):
    """星的亮度倍数，大约 0.5–1.35：几条不成整数比的正弦叠起来，偶尔往下暗一下，像快没电的星。"""
    u = t + seed * 1.7
    v = 0.55 * math.sin(2 * math.pi * u / 1.9) + 0.3 * math.sin(2 * math.pi * u / 0.73 + 1.1) + 0.15 * math.sin(2 * math.pi * u / 0.31 + 2.3)
    dip = max(0.0, math.sin(2 * math.pi * u / 3.7 + 0.4)) ** 12  # 每三四秒一次明显变暗
    return 0.95 + 0.4 * v - 0.4 * dip


def dim(a, m, f, dark_k=0.22):
    """把遮罩里的光调到 f 倍：小于 1 往夜色里退，大于 1 更亮。"""
    if f < 1:
        dark = a.mean(2, keepdims=True) * dark_k
        return a * (1 - m * (1 - f)) + dark * m * (1 - f)
    return a + a * (f - 1) * m


class Shot(L.Layered):
    def __init__(self, key, dur, on=None, seed=0):
        super().__init__(key, dur, on=on, seed=seed)
        for i, ((x0, y0, x1, y1), mode) in enumerate(self.spec.get("glow", [])):
            if isinstance(mode, tuple) and mode[-1] == "lum":
                m = np.zeros(self.a.shape[:2], np.float32)
                m[y0:y1, x0:x1] = np.clip((self.a[y0:y1, x0:x1].mean(2) - 25) / 60, 0, 1)
                self.glows[i] = (ndimage.gaussian_filter(ndimage.maximum_filter(m, 7), 1.5)[..., None], mode)  # 细线先加粗再羽化，不然压不黑

    def _glow(self, a, t):
        for m, mode in self.glows:
            if isinstance(mode, tuple):
                t0, ramp = mode[1], mode[2]
                after = max(0.0, t - t0 - ramp)
                k = flicker(after) if mode[-1] == "flicker" else 1 + 0.08 * math.sin(2 * math.pi * after / 4.2)
                a = dim(a, m, L.ease((t - t0) / ramp) * (k if t > t0 + ramp else min(1.0, k)), 0.03 if mode[-1] == "lum" else 0.22)
            elif mode == "flicker":
                a = dim(a, m, flicker(t, len(self.key)))
            elif mode == "pulse":
                a = a + a * 0.10 * math.sin(2 * math.pi * t / 4.2) * m
        return a

    def frame(self, t):
        im = super().frame(t)
        p = PUSH.get(self.key)
        if not p or t <= p["at"]:
            return im
        z = 1 + (p["zoom"] - 1) * L.ease((t - p["at"]) / p["secs"])
        cx, cy = p["center"]
        w, h = self.W / z, self.H / z
        x0 = min(max(cx - (cx / self.W) * w, 0), self.W - w)  # 推的时候那一点在画面里的位置不动
        y0 = min(max(cy - (cy / self.H) * h, 0), self.H - h)
        return im.crop((x0, y0, x0 + w, y0 + h)).resize((self.W, self.H), Image.LANCZOS)


def check():
    rows = []
    for k, ts in {"1": [0.3, 0.9, 1.5, 2.1, 2.7, 3.3], "5a": [0.3, 0.9, 1.5, 2.1, 2.7, 3.3],
                  "6": [0.2, 1.2, 2.6, 3.8, 5.0, 7.5], "7": [0.3, 0.9, 1.5, 2.1, 2.7, 3.3]}.items():
        sh = Shot(k, 9.0)
        rows.append([sh.frame(t).resize((300, int(300 * sh.H / sh.W))) for t in ts])
    w, hs = 300 * max(len(r) for r in rows), [r[0].height for r in rows]
    out = Image.new("RGB", (w, sum(hs)))
    for i, r in enumerate(rows):
        for j, im in enumerate(r):
            out.paste(im, (j * 300, sum(hs[:i])))
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    out.save(os.path.join(HERE, "build", "motion_check.jpg"), quality=85)


if __name__ == "__main__":
    {"check": check}[sys.argv[1]]()
