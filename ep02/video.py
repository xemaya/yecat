"""和夜一起住 · 第 2 期视频版：照 ../ep01r/video.py 的做法（只有音乐、字幕在上方、手札体），镜头和字幕直接从 剧本.md 读。

  ../../../ucl-video/.venv/bin/python video.py              # 出 和夜一起住02.mp4
  ONLY=6 ../../../ucl-video/.venv/bin/python video.py       # 只出这几个镜头（样张），出 样张_6.mp4

5b（取星）放 H3 片段，其余镜头是分层动效（motion.py）。

字幕四种样式（配方.md）：旁白白字；晴白字 + 黑白“晴”字章；夜琥珀色 + 金“夜”字章；配角灰字。
纸条按写纸条的人走晴或夜的样式。封面的标题叠在第一个镜头上。
"""
import os
import subprocess
import sys
from dataclasses import asdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ep01"))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import video as V  # noqa: E402
import motion  # noqa: E402
from check_script import parse  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

V.ART = os.path.join(HERE, "art")
V.layers.Layered = motion.Shot
# H3 片段（h3.py 出）：5b 取星。环境变量 C5B 换种子
CLIPS = {"5b": os.path.join(HERE, "h3", os.environ.get("C5B", "5b_s42") + ".mp4")}
V.H3_SHOTS = list(CLIPS)
_load = V.Shot.load


def load(self):
    """取星那一下灯罩本来就该变暗：不对首帧校色、不剪暗掉的帧（同第 1 期的 7b、重做版的 n2）。"""
    if self.key != "5b" or self.frames is not None or not os.path.exists(self.clip):
        return _load(self)
    r = V.imageio_ffmpeg.read_frames(self.clip)
    meta = next(r)
    w, h = meta["size"]
    self.fps = meta["fps"]
    self.frames = [Image.fromarray(np.frombuffer(b, np.uint8).reshape(h, w, 3)) for b in r]
    return self.frames


V.Shot.load = load
NO = 2
TITLE = ("灯罩里没有灯泡，", "只有一颗星星")
GREY = (170, 168, 162)


def subtitle(who, text):
    """一句字幕的 RGBA 图（最多两行）。"""
    ft = V.hand(52)
    rows = V.wrap(text)
    im = Image.new("RGBA", (V.W, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tw = max(ft.getlength(r) for r in rows)
    seal = who in ("夜", "晴")
    x = V.W / 2 + (30 if seal else 0)
    fill = {"夜": V.AMBER, "配角": GREY}.get(who, (245, 240, 230))
    for j, r in enumerate(rows):
        y = 75 + (j - (len(rows) - 1) / 2) * 66
        d.text((x, y), r, font=ft, fill=fill, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    if seal:
        cx = x - tw / 2 - 42
        if who == "夜":
            d.ellipse((cx - 26, 49, cx + 26, 101), fill=V.AMBER)
            d.text((cx, 76), "夜", font=V.hand(32), fill=(255, 255, 255), anchor="mm")
        else:  # 晴：白圈黑字，和夜的金章对称
            d.ellipse((cx - 26, 49, cx + 26, 101), fill=(245, 240, 230), outline=(0, 0, 0), width=3)
            d.text((cx, 76), "晴", font=V.hand(32), fill=(16, 16, 16), anchor="mm")
    return im


def title_layer():
    im = Image.new("RGBA", (V.W, V.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((V.W / 2, 330), TITLE[0], font=V.f(88, 0), fill=(255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((V.W / 2, 450), TITLE[1], font=V.f(88, 0), fill=V.AMBER, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((V.W / 2, 550), f"和夜一起住 · {NO:02d}", font=V.f(32), fill=(200, 195, 185), anchor="mm")
    return im


def end_layer():
    im = Image.new("RGBA", (V.W, V.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, t in enumerate(["想知道夜的更多秘密吗？", "评论区告诉我。"]):
        d.text((V.W / 2, V.SUB_Y + 44 + i * 66), t, font=V.hand(52), fill=V.AMBER, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((V.W / 2, V.SUB_Y + 186), f"和夜一起住 · {NO:02d}", font=V.hand(34), fill=(190, 185, 175), anchor="mm")
    return im


V.subtitle = subtitle


def shots_from_script():
    """[(镜头, [(谁, 字)], 建议秒数)]；两格页拆成 5a、5b 两个镜头。"""
    ep = asdict(parse(os.path.join(HERE, "剧本.md")))
    out = []
    for p in ep["pages"]:
        panels = sorted(p["scenes"]) if "a" in p["scenes"] else [""]
        for k in panels:
            lines = []
            for ln in p["lines"]:
                if ln["panel"] not in ("", k) or ln["kind"] == "标题":
                    continue
                who = {"旁白": "我", "画面字": ln["writer"] or "我"}.get(ln["kind"], ln["kind"])
                lines.append((who, ln["text"]))
            dur = p["dur"].get(k) or (p["dur"].get("") if k in ("", "b") else None)
            out.append((f"{p['no']}{k}", lines, dur))
    return out


def secs(text):
    return max(1.6, 0.45 + 0.2 * len(text))  # 字幕阅读速度约 5 字/秒


def plan(only=None):
    shots, clips = [], []
    table = shots_from_script()
    for key, lines, want in table:
        t, subs = V.LEAD, []
        for who, text in lines:
            d = secs(text)
            subs.append((who, text, t, t + d))
            clips.append(np.zeros(int(d * V.SR)))
            t += d + V.GAP
        dur = t - V.GAP + V.TAIL + (V.END_HOLD if key == table[-1][0] else 0)
        floor = 5.5 if key == "1" else 6.5 if key in CLIPS else 4.0  # 封面留给标题；H3 片段 6 秒要放完；镜头最短 4 秒
        shots.append((key, max(dur, want or 0, floor), subs))
    if only:
        shots = [s for s in shots if s[0] in only]
    return shots, clips


if __name__ == "__main__":
    only = [k for k in os.environ.get("ONLY", "").split(",") if k]
    V.TITLE = title_layer() if not only or "1" in only else Image.new("RGBA", (V.W, V.H))
    V.END = end_layer() if not only else Image.new("RGBA", (V.W, V.H))
    shots, clips = plan(only)
    objs = [V.Shot(k, d, s, i) for i, (k, d, s) in enumerate(shots)]
    for o in objs:
        o.clip = CLIPS.get(o.key, "")
    starts = np.cumsum([0] + [o.dur - V.FADE for o in objs[:-1]])
    total = starts[-1] + objs[-1].dur
    print(f"总长 {total:.1f}s，{len(objs)} 个镜头", flush=True)
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    wav = os.path.join(HERE, "build", "audio.f32")
    V.mix(shots, clips, total).astype(np.float32).tofile(wav)
    out = os.path.join(HERE, f"样张_{'_'.join(only)}.mp4" if only else f"和夜一起住{NO:02d}.mp4")
    proc = subprocess.Popen([V.imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{V.W}x{V.H}", "-r", str(V.FPS), "-i", "-", "-f", "f32le", "-ar", str(V.SR), "-ac", "1", "-i", wav,
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * V.FPS)):
        t = fi / V.FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        if i >= 2:
            objs[i - 2].release()
        im = objs[i].frame(t - starts[i])
        if i > 0 and t - starts[i] < V.FADE:
            im = Image.blend(objs[i - 1].frame(t - starts[i - 1]), im, (t - starts[i]) / V.FADE)
        proc.stdin.write(im.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print(out)
