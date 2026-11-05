"""和夜一起住 · 第 1 期重做的视频版：照 ../ep01/video.py 的 v4 做法（只有音乐、字幕在上方、手札体），换成重做版的镜头和字幕。

  ../../../ucl-video/.venv/bin/python video.py      # 出 和夜一起住01_重做.mp4

镜头图在 vid/（第 1 期 art_C 的原图 + 新画的 n2、n3，都是链接；5a 换成了不下雨的 var/5a_dry）。
分层动效用 motion.py（在 ../ep01/layers.py 上加了冰箱摆东西、换姿势、热气）；音乐、眨眼变体图用 ../ep01 的缓存。
H3 片段：n2、n3、7 是 h3.py 新出的，1、4、8、9 沿用第 1 期，7b 换成第 1 期的第 2 条（第 1 条变身时多冒出一只爪子）。
不放配音，所以不调 TTS：每句字幕按字数定时长。
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ep01"))
import video as V  # noqa: E402
import motion  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

V.ART = os.path.join(HERE, "vid")
V.layers.Layered = motion.Shot
OLD_H3 = os.path.join(HERE, "..", "ep01", "h3")
CLIPS = {"1": f"{OLD_H3}/1.mp4", "4": f"{OLD_H3}/4.mp4", "7b": f"{OLD_H3}/7b_s2.mp4", "8": f"{OLD_H3}/8.mp4", "9": f"{OLD_H3}/9.mp4",
         "n2": os.path.join(HERE, "h3", os.environ.get("N2", "n2_s42") + ".mp4"),
         "n3": os.path.join(HERE, "h3", os.environ.get("N3", "n3_s42") + ".mp4"),
         "7": os.path.join(HERE, "h3", os.environ.get("C7", "7_s42") + ".mp4")}
V.H3_SHOTS = list(CLIPS)
_load = V.Shot.load


def load(self):
    """n2 台灯关掉那一下整屏本来就该变暗：不对首帧校色、不剪暗掉的帧（同第 1 期的 7b）。"""
    if self.key != "n2" or self.frames is not None or not os.path.exists(self.clip):
        return _load(self)
    r = V.imageio_ffmpeg.read_frames(self.clip)
    meta = next(r)
    w, h = meta["size"]
    self.fps = meta["fps"]
    self.frames = [Image.fromarray(np.frombuffer(b, np.uint8).reshape(h, w, 3)) for b in r]
    return self.frames


V.Shot.load = load
V.SHOTS = [
    ("1", []),
    ("n2", [("我", "我叫姜晴，灯光设计师。")]),
    ("n3", [("我", "每次搬家，我都会往盒子里放一颗灯泡，留作纪念。")]),
    ("2", [("我", "房租又涨了，我想找个室友。"), ("我", "来看房的，只有它。"), ("夜", "我上夜班，白天不吵你。")]),
    ("3", [("我", "冰箱一人一半，不动对方的东西，不问对方的工作。")]),
    ("4", [("我", "它说“早”，我说“晚安”。")]),
    ("5a", [("我", "我加班到最晚的那天，楼下坏了半年的路灯修好了，"), ("我", "灯光比之前更温暖。")]),
    ("5b", [("我", "我哭过的那晚，冰箱里多了热牛奶。"), ("我", "贴着纸条，"), ("夜", "买多了。")]),
    ("6", [("我", "有一天，它早上没回来。"), ("我", "我在阳台找到它时，它缩成了巴掌大。"), ("夜", "上班……用力过头了。")]),
    ("7", [("我", "我请了一天假，陪它晒太阳。")]),
    ("7b", [("我", "傍晚，它变得像沙发那么大。")]),
    ("8", [("夜", "这次……算我欠你的。"), ("我", "室友嘛。")]),
    ("9", [("我", "后来我们还是很少碰面。"), ("我", "但我好像，不太想搬走了。")]),
]
MIN_DUR = {"1": 5.5, "7b": 7.0, "n2": 7.0, "n3": 7.0, "7": 7.0, "3": 6.5, "6": 7.5}  # 封面留给标题；H3 片段 6 秒要放完；冰箱、换姿势要时间


def secs(text):
    return max(1.6, 0.45 + 0.2 * len(text))  # 字幕阅读速度约 5 字/秒


def plan():
    shots, clips = [], []
    for key, lines in V.SHOTS:
        t, subs = V.LEAD, []
        for who, text in lines:
            d = secs(text)
            subs.append((who, text, t, t + d))
            clips.append(np.zeros(int(d * V.SR)))
            t += d + V.GAP
        dur = t - V.GAP + V.TAIL + (V.END_HOLD if key == V.SHOTS[-1][0] else 0)
        shots.append((key, max(dur, MIN_DUR.get(key, 4.0)), subs))
    return shots, clips


def end_layer():
    im = Image.new("RGBA", (V.W, V.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, t in enumerate(["想知道夜的更多秘密吗？", "评论区告诉我。"]):
        d.text((V.W / 2, V.SUB_Y + 44 + i * 66), t, font=V.hand(52), fill=V.AMBER, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((V.W / 2, V.SUB_Y + 186), "和夜一起住 · 01", font=V.hand(34), fill=(190, 185, 175), anchor="mm")
    return im


if __name__ == "__main__":
    V.TITLE, V.END = V.title_layer(), end_layer()
    shots, clips = plan()
    objs = [V.Shot(k, d, s, i) for i, (k, d, s) in enumerate(shots)]
    for o in objs:
        o.clip = CLIPS.get(o.key, "")
    starts = np.cumsum([0] + [o.dur - V.FADE for o in objs[:-1]])
    total = starts[-1] + objs[-1].dur
    print(f"总长 {total:.1f}s，{len(objs)} 个镜头", flush=True)
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    wav = os.path.join(HERE, "build", "audio.f32")
    V.mix(shots, clips, total).astype(np.float32).tofile(wav)
    out = os.path.join(HERE, os.environ.get("OUT", "和夜一起住01_重做.mp4"))
    proc = subprocess.Popen([V.imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{V.W}x{V.H}", "-r", str(V.FPS), "-i", "-", "-f", "f32le", "-ar", str(V.SR), "-ac", "1", "-i", wav,
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * V.FPS)):
        t = fi / V.FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        if i >= 2:
            objs[i - 2].release()
        if fi % (V.FPS * 10) == 0:
            print(f"{t:.0f}s", flush=True)
        im = objs[i].frame(t - starts[i])
        if i > 0 and t - starts[i] < V.FADE:
            im = Image.blend(objs[i - 1].frame(t - starts[i - 1]), im, (t - starts[i]) / V.FADE)
        proc.stdin.write(im.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print(out)
