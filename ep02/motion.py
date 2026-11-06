"""第 2 期的分层动效，在 ../ep01/layers.py 上加：

  glow 的 ("on", 起, 用时)：区域里的金光先暗着，到“起”秒用“用时”慢慢亮起来，亮了以后轻轻呼吸
    （P6：先亮掌心的星，再亮弯臂上那双眼睛）
  ("on", 起, 用时, "lum")：不只金色，区域里所有亮的线（白色的月牙、耳朵轮廓）都先全黑

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
    "6": dict(glow=[((440, 380, 700, 640), ("on", 0.5, 1.8)), ((470, 90, 830, 228), ("on", 3.4, 2.2, "lum"))]),
    "7": dict(glow=[((330, 600, 560, 820), "pulse")], twinkle=[(120, 420, 360, 720)]),  # 掌心的星呼吸；尾尖闪
})


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
                f = L.ease((t - t0) / ramp) * (1 + 0.08 * math.sin(2 * math.pi * max(0.0, t - t0 - ramp) / 4.2))
                dark = a.mean(2, keepdims=True) * (0.03 if mode[-1] == "lum" else 0.22)
                a = a * (1 - m * (1 - f)) + dark * m * (1 - f) if f < 1 else a + a * (f - 1) * m
            elif mode == "pulse":
                a = a + a * 0.10 * math.sin(2 * math.pi * t / 4.2) * m
        return a


def check():
    rows = []
    for k, ts in {"6": [0.2, 1.2, 2.6, 3.8, 5.0, 7.5]}.items():
        sh = Shot(k, 9.0)
        rows.append([sh.frame(t).resize((300, int(300 * sh.H / sh.W))) for t in ts])
    w, h = 300 * max(len(r) for r in rows), max(r[0].height for r in rows)
    out = Image.new("RGB", (w, h * len(rows)))
    for i, r in enumerate(rows):
        for j, im in enumerate(r):
            out.paste(im, (j * 300, i * h))
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    out.save(os.path.join(HERE, "build", "motion_check.jpg"), quality=85)


if __name__ == "__main__":
    {"check": check}[sys.argv[1]]()
