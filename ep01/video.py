"""和夜一起住 · 第 1 期视频版：用图文的插画（art_C），黑底竖屏 9:16，钢琴背景乐 + 字幕（不放配音，VO=1 才混进去）。
字幕放在画面上方（小红书底部的标题、按钮会挡住下面），用手札体。

  ../../../ucl-video/.venv/bin/python video.py      # 出 和夜一起住01.mp4（配音、音乐有缓存）

每个镜头的画面默认是分层动效（layers.py：眨眼、呼吸、热气、金星、路灯、雨，再加 3% 的慢推）；
H3=1,8 这样列出的镜头改放 h3/<插画>.mp4（h3.py 在 4090 上图生视频），镜头不动，片段放在镜头中间，前后停在首帧、尾帧。
LOOK=still 退回原图慢推（第一版）。
音乐先用 music.generate 生成到 music/夜.mp3（见 build 记录）。不加音效。
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import layers  # noqa: E402
import music  # noqa: E402
import voice  # noqa: E402
import imageio_ffmpeg  # noqa: E402

SR, FPS = voice.SR, 30
W, H = 1080, 1920
ART = os.path.join(HERE, "art_C")
SONG = "/System/Library/Fonts/Supplemental/Songti.ttc"
HAND = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/00bfc46ccb002b730e29def5116e0a571fb617d8.asset/AssetData/Hannotate.ttc"
VO = os.environ.get("VO", "0") == "1"  # 配音只用来定每句字幕的时长
AMBER = (226, 164, 60)
VOICES = {"我": dict(voice="female-yujie", speed=0.95, emotion="calm"),
          "夜": dict(voice="Chinese (Mandarin)_Unrestrained_Young_Man", speed=0.92, pitch=-2, emotion="calm")}
FADE = 0.45  # 镜头之间交叉淡化
SUB_Y = 150  # 字幕条（150 高）的上沿：躲开小红书顶部的返回、搜索按钮
LOOK = os.environ.get("LOOK", "layer")
H3_SHOTS = [k for k in os.environ.get("H3", "").split(",") if k]

# 镜头：(插画, [(谁, 台词, 情绪?)])；插画是 art_C 里的原图编号
SHOTS = [
    ("1", []),  # 封面：标题已经写着这句
    ("2", [("我", "房租涨了，我决定找个合租室友。"), ("我", "来看房的，只有一个。"), ("夜", "我上夜班，白天不吵你。")]),
    ("3", [("我", "我们约法三章："), ("我", "冰箱一人一半，不动对方的东西，不问对方的工作。")]),
    ("4", [("我", "我们几乎碰不到面。我出门，它回来。"), ("夜", "早。"), ("我", "晚安。")]),
    ("5a", [("我", "我加班到最晚的那天，楼下坏了半年的路灯，亮了。")]),
    ("5b", [("我", "我偷偷哭过的那晚，冰箱里多了一瓶热牛奶。"), ("我", "纸条上写着："), ("夜", "买多了。")]),
    ("6", [("我", "有一天，它早上没回来。"), ("我", "我在阳台找到它，缩成了巴掌大。"), ("夜", "上班……用力过头了。", "sad")]),
    ("7", [("我", "我请了一天假。没问它的工作，这是我们的约定。"), ("我", "只是把它揣进口袋，带它晒了一整天太阳。")]),
    ("7b", [("我", "傍晚，它在我腿边伸了个懒腰。"), ("我", "然后一点一点，变大了。"), ("我", "我第一次知道，它原本有这么大。")]),
    ("8", [("夜", "这次……算我欠你的。"), ("我", "室友嘛。", "happy"), ("我", "独立的人也可以互相照顾。不用问太多，在就好。")]),
    ("9", [("我", "后来，我们还是很少碰面。"), ("我", "但窗边那盏灯，一直有人留着。")]),
]
LEAD, GAP, TAIL = 0.6, 0.35, 0.9
END_HOLD = 3.5  # 最后一个镜头多停，留给下期预告


def f(size, index=6):
    return ImageFont.truetype(SONG, size, index=index)


def hand(size):
    return ImageFont.truetype(HAND, size, index=2)  # 手札体 SC 粗


def plan():
    """配音 + 每句的起止时间。返回 [(镜头, 时长, [(谁, 台词, 起, 止)])] 和每句的音频。"""
    shots, clips = [], []
    for key, lines in SHOTS:
        t, subs = LEAD, []
        for who, text, *emo in lines:
            y = voice.tts(os.path.join(HERE, "voice"), VOICES[who], text, *emo)
            subs.append((who, text, t, t + len(y) / SR))
            clips.append(y)
            t += len(y) / SR + GAP
        dur = t - GAP + TAIL + (END_HOLD if key == SHOTS[-1][0] else 0)
        dur = max(dur, 5.5)  # 封面多留一会儿给标题
        shots.append((key, dur, subs))
    return shots, clips


def wrap(text, n=17):
    """长句在最靠近中间的逗号处折成两行。"""
    if len(text) <= n:
        return [text]
    cuts = [i + 1 for i, c in enumerate(text[:-1]) if c in "，、：；。？"]
    if not cuts:
        return [text]
    k = min(cuts, key=lambda i: abs(i - len(text) / 2))
    return [text[:k], text[k:]]


def subtitle(who, text):
    """一句字幕的 RGBA 图（最多两行）：她是白字，夜是金字 + 左边一枚“夜”字章。"""
    ft = hand(52)
    rows = wrap(text)
    im = Image.new("RGBA", (W, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tw = max(ft.getlength(r) for r in rows)
    x = W / 2 + (30 if who == "夜" else 0)
    for j, r in enumerate(rows):
        y = 75 + (j - (len(rows) - 1) / 2) * 66
        d.text((x, y), r, font=ft, fill=AMBER if who == "夜" else (245, 240, 230), anchor="mm",
               stroke_width=4, stroke_fill=(0, 0, 0))
    if who == "夜":
        cx = x - tw / 2 - 42
        d.ellipse((cx - 26, 49, cx + 26, 101), fill=AMBER)
        d.text((cx, 76), "夜", font=hand(32), fill=(255, 255, 255), anchor="mm")
    return im


def title_layer():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 330), "我的新室友", font=f(96, 0), fill=(255, 255, 255), anchor="mm")
    d.text((W / 2, 460), "是一只上夜班的猫", font=f(96, 0), fill=AMBER, anchor="mm")
    d.text((W / 2, 560), "和夜一起住 · 01", font=f(32), fill=(200, 195, 185), anchor="mm")
    return im


def end_layer():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((W / 2, SUB_Y + 60), "下期：夜的夜班，到底是什么？", font=hand(52), fill=AMBER, anchor="mm",
           stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((W / 2, SUB_Y + 128), "和夜一起住 · 01", font=hand(34), fill=(190, 185, 175), anchor="mm")
    return im


class Shot:
    def __init__(self, key, dur, subs, i):
        self.src = Image.open(os.path.join(ART, f"{key}.png")).convert("RGB")
        self.dur, self.subs = dur, [(s, a, b) for (who, text, a, b) in subs for s in [subtitle(who, text)]]
        land = self.src.width > self.src.height
        # 字幕在最上面；竖图铺满宽度接在字幕下面（底边出画 10 像素），横图（两格页的上下格）也接在字幕下面
        self.box = (0, 420, W, 1140) if land else (0, 310, W, 1930)
        self.sub_y = SUB_Y
        self.zin = i % 2 == 0  # 推近 / 拉远交替
        self.key = key
        self.clip = os.path.join(HERE, "h3", f"{key}.mp4") if key in H3_SHOTS else ""
        self.frames = None
        on = subs[0][3] - 0.75 if key == "5a" else None  # “……路灯，亮了。”说到“亮了”时灯亮
        self.lay = layers.Layered(key, dur, on=on, seed=i) if LOOK == "layer" else None

    def load(self):
        if self.frames is None and os.path.exists(self.clip):
            r = imageio_ffmpeg.read_frames(self.clip)
            meta = next(r)
            w, h = meta["size"]
            self.fps = meta["fps"]
            fr = [np.frombuffer(b, np.uint8).reshape(h, w, 3) for b in r]
            # H3 越往后越发灰或变暗：每帧按通道把直方图对回首帧；亮度掉到一半以下（转黑）的尾巴直接剪掉
            if self.key == "7b":  # 变身镜头画面本来就从亮变暗（小猫长成大黑猫），不校色不剪
                self.frames = [Image.fromarray(f) for f in fr]
                return self.frames
            ref = fr[0]
            lum = [f.mean() / ref.mean() for f in fr]
            n = next((i for i, v in enumerate(lum) if v < 0.85), len(fr))
            q = np.linspace(0, 100, 257)
            pr = [np.percentile(ref[..., c], q) for c in range(3)]
            out = []
            for f in fr[:n]:
                g = np.stack([np.interp(f[..., c], np.percentile(f[..., c], q), pr[c]) for c in range(3)], -1)
                out.append(Image.fromarray(g.clip(0, 255).astype(np.uint8)))
            self.frames = out
        return self.frames

    def release(self):
        self.frames = None

    def picture(self, t):
        """动态镜头：片段放在镜头中间，前后停在首帧、尾帧。没有片段就用原图慢推。"""
        x0, y0, x1, y1 = self.box
        bw, bh = x1 - x0, y1 - y0
        fr = self.load()
        if fr:
            off = max(0.0, (self.dur - len(fr) / self.fps) / 2)
            return fr[int(min(len(fr) - 1, max(0, (t - off) * self.fps)))].resize((bw, bh), Image.LANCZOS)
        src = self.lay.frame(t) if self.lay else self.src
        sw, sh = src.size
        p = layers.ease(t / self.dur) if self.lay else min(1, t / self.dur)
        s = 1.0 + (0.03 if self.lay else 0.05) * (p if self.zin else 1 - p)
        cw = min(sw, sh * bw / bh) / s
        ch = cw * bh / bw
        cx, cy = sw / 2, min(max(sh * 0.45, ch / 2), sh - ch / 2)
        return src.resize((bw, bh), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))

    def frame(self, t):
        x0, y0 = self.box[:2]
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        im.paste(self.picture(t), (x0, y0))
        if self.key == "1":
            # 标题区：图的上缘渐隐到黑
            g = Image.linear_gradient("L").resize((W, 420)).transpose(Image.FLIP_TOP_BOTTOM)
            im.paste((0, 0, 0), (0, y0, W, y0 + 420), g.point(lambda v: int(v * 0.85)))
            im.alpha_composite(TITLE)
        ending = self.key == SHOTS[-1][0] and t > self.subs[-1][2] + 0.3
        if ending:
            a = min(1, (t - self.subs[-1][2] - 0.3) / 0.8)
            im.alpha_composite(Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 0)), END, a))
        for sub, a, b in self.subs:
            if a - 0.1 <= t <= b + 0.25 and not ending:
                im.alpha_composite(sub, (0, self.sub_y))
        return im


def mix(shots, clips, total):
    vo = np.zeros(int(total * SR) + SR)
    t0, k = 0.0, 0
    for _key, dur, subs in shots:
        for _who, _text, a, _b in subs:
            y = clips[k]
            k += 1
            i = int((t0 + a) * SR)
            vo[i:i + len(y)] += y
        t0 += dur - FADE
    bgm = music.load(os.path.join(HERE, "music", "夜.mp3"))
    bgm = np.tile(bgm, int(np.ceil(len(vo) / len(bgm))))[:len(vo)]
    n = len(vo)
    fade = np.minimum(1, np.minimum(np.arange(n) / (1.5 * SR), (n - np.arange(n)) / (2.5 * SR)))
    if not VO:  # 只有音乐：峰值拉到 0.8，整段不压
        return np.clip(bgm / (np.abs(bgm).max() + 1e-9) * 0.8 * fade, -1, 1)
    # 说话时音乐压低：按语音包络平滑
    env = np.convolve((np.abs(vo) > 0.01).astype(float), np.ones(int(0.4 * SR)) / int(0.4 * SR), "same")
    gain = 0.32 - 0.2 * np.clip(env * 3, 0, 1)
    out = vo * 0.95 + bgm * gain * fade
    return np.clip(out, -1, 1)


if __name__ == "__main__":
    TITLE, END = title_layer(), end_layer()
    shots, clips = plan()
    objs = [Shot(k, d, s, i) for i, (k, d, s) in enumerate(shots)]
    starts = np.cumsum([0] + [o.dur - FADE for o in objs[:-1]])
    total = starts[-1] + objs[-1].dur
    print(f"总长 {total:.1f}s，{len(objs)} 个镜头", flush=True)
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    wav = os.path.join(HERE, "build", "audio.f32")
    mix(shots, clips, total).astype(np.float32).tofile(wav)
    out = os.path.join(HERE, os.environ.get("OUT", "和夜一起住01.mp4"))
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", wav,
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        t = fi / FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        if i >= 2:
            objs[i - 2].release()
        if fi % (FPS * 10) == 0:
            print(f"{t:.0f}s", flush=True)
        im = objs[i].frame(t - starts[i])
        if i > 0 and t - starts[i] < FADE:
            prev = objs[i - 1].frame(t - starts[i - 1])
            im = Image.blend(prev, im, (t - starts[i]) / FADE)
        proc.stdin.write(im.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print(out)
