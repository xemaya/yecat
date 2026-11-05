"""和夜一起住 · 第 1 期重做（剧本见 ../ep01/剧本_重做.md）。画风 C 黑白点金；沿用的插画从 ../ep01/art_C 拷进 art/。

  ../../../ucl-video/.venv/bin/python gen.py          # 补齐缺的插画，再排全部页 + 总览
  ../../../ucl-video/.venv/bin/python gen.py 2 3      # 只做这几页（样张）
  ../../../ucl-video/.venv/bin/python gen.py page 5   # 只重新排版
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "clip10"))
import assets as base  # noqa: E402

# 画风对比阶段：第一个参数选 B（深蓝扁平）或 C（黑白点金），图出到 art_B / art_C
V = "C"
REF = os.path.join(HERE, "..", "style", {"B": "v3_B深蓝扁平.png", "C": "v3_C黑白点金.png"}[V])
ART = os.path.join(HERE, "art")
GIRL_REF = os.path.join(HERE, "..", "ep01", "art_C", "2.png")  # 第 1 期面试页，女孩的长相照它
FA = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8"
KAITI = f"{FA}/88d6cc32a907955efa1d014207889413890573be.asset/AssetData/Kaiti.ttc"
YUANTI = f"{FA}/4a418d1fa4860652a3241e8ee457806c8557fc64.asset/AssetData/Yuanti.ttc"
SONG = "/System/Library/Fonts/Supplemental/Songti.ttc"  # 0 Black、1 Bold、6 Regular
S = 2
W, H = 1080 * S, 1440 * S
CREAM = (255, 244, 226)
AMBER = (226, 164, 60)
INK = (16, 16, 16)
PAPER = (250, 248, 243)

STYLE = {
    "B": ("画风：极简的扁平插画，和参考图的画风、人物、黑猫完全一致：深夜蓝和暖橘两种主色，几何化的干净色块，没有线稿、没有纹理，"
          "光和猫眼是画面的亮点，像高级绘本和杂志插画"),
    "C": ("画风：黑白漫画线稿风，和参考图的画风、人物、黑猫完全一致：干净的黑色线条和大块纯黑、纯白，整张画只有一个颜色点缀——"
          "猫的金色眼睛、月牙纹、星光，以及故事里温暖的光（灯、热牛奶、阳光）是琥珀金色，其余全部黑白，克制高级"),
}[V] + "。画面干净、道具少，背景简化"
GIRL = ("女孩：就是参考图里的女孩，二十五六岁，身材高挑修长、头身比约 1:7.5、腿长、肩颈舒展，鹅蛋脸偏瘦，"
        "利落的齐肩黑色短发（发尾整齐、一侧别在耳后），合身的燕麦色衬衫袖子挽到手肘、合身的深灰色直筒长裤，"
        "手腕上一块旧手表，独立干练、眼神温柔")
CAT = ("黑猫夜：就是参考图里的黑猫，毛色深黑泛一点蓝紫光泽，琥珀金色的眼睛微微发光，额头一道琥珀金色月牙纹，"
       "尾巴尖有几点星星似的微光，不戴项圈")
LAYOUT = "竖版构图：人物和主要内容在画面上方 72%，画面下方 28% 是较暗、简单的地面或前景（之后要压文字），不要把重要内容放在下方。"
COVER_LAYOUT = "竖版构图：画面上方 30% 是简单干净、偏暗的背景（之后压大标题，这里不能有人脸），人物在画面中部，下方 15% 简单干净。"
NO_TEXT = "画面里不要任何文字、字母、数字、logo、门牌上的字。每个人一共只有两只手。"

# 页：(插画场景，两格的页给两个场景, 文字)。文字按顺序排：字符串是旁白一行，("夜", 台词) 是夜的对话框。
# 场景写成 None 的页，插画是从 ../ep01/art_C 拷来的（见 ../ep01/剧本_重做.md 的素材列）。
OLD = os.path.join(HERE, "..", "ep01", "art_C")
REMAKE = {"5a": os.path.join(OLD, "3.png"), "5b": os.path.join(OLD, "4.png")}  # 第 1 期的竖图，照着改成横图
PAGES = {
    1: (None, []),
    2: (f"夜里，一家还没开业的小店，店里所有的灯都关着，几乎全黑。{GIRL}，腰上系着装满工具的帆布腰包，额头戴着关掉的头灯，"
        "坐在一架木头人字梯的中段，双手捧着一盏小小的台灯；台灯亮着温暖的琥珀金色光，是画面里唯一的光，照亮她安静专注的脸，"
        "她微微仰头，在看光落在哪里。画面里没有猫。",
        ["我叫姜晴，灯光设计师。"]),
    3: (f"白天，一间空荡荡的老出租屋卧室，只有天花板中间一盏冷白色的吸顶灯，墙角堆着两只搬家纸箱。{GIRL}，踮着脚，"
        "双手把一只打开盖子的旧鞋盒举到衣柜顶上；鞋盒里整齐躺着几颗旧灯泡，每颗灯泡上贴着一小截白色胶布，灯泡透出一点琥珀金色的微光。"
        "她低头看着那些灯泡，神情平静。画面里没有猫。",
        ["每次搬家，", "我都会往盒子里放一颗灯泡，留作纪念。"]),
    4: (None, ["房租又涨了，我想找个室友。", "来看房的，只有它。", ("夜", "我上夜班，白天不吵你。")]),
    5: (["夜里，一台打开的双开门冰箱正面，冰箱里透出暖光。冰箱正中间竖着贴了一条黑白条纹的分界胶带：左半边是女孩的东西"
         "（几盒外卖、半颗卷心菜、一排酸奶）；右半边是黑猫的东西（几瓶玻璃瓶牛奶、一小罐会发出琥珀金色微光的小星星、一条小鱼干）。"
         "画面里只有冰箱：没有任何人，也没有猫。",
         f"清晨天刚亮，合租房的门口，门开着一半。{GIRL}，背着包正要出门、回头看了一眼；{CAT}，正常家猫大小，"
         "刚从门外走进来，毛上带着一点夜露、尾巴尖的星光快熄了，抬头看她。一人一猫在门口擦肩而过，门外是淡淡的晨光。"],
        ["冰箱一人一半，不动对方的东西，不问对方的工作。", "它说“早”，我说“晚安”。"]),
    6: ([None, None],
        ["我加班到最晚的那天，楼下坏了半年的路灯修好了，", "灯光比之前更温暖。",
         "我哭过的那晚，冰箱里多了热牛奶。", "贴着纸条，“买多了。”"]),
    7: (None, ["有一天，它早上没回来。", "我在阳台找到它时，它缩成了巴掌大。", ("夜", "上班……用力过头了。")]),
    8: (None, ["我请了一天假，陪它晒太阳。", "傍晚，它变得像沙发那么大。", ("夜", "这次……算我欠你的。"), "我说：“室友嘛。”"]),
    9: (None, []),
}


def art(n):
    """n：页码，或 "5a" / "5b"（两格页的上下格，横图）。"""
    out = os.path.join(ART, f"{n}.png")
    if not os.path.exists(out):
        if isinstance(n, str):
            scene = PAGES[int(n[0])][0]["ab".index(n[1])]
            layout, size = "横版构图：人物和主要内容在画面中间，四周留一点余地。", "1536x1024"
            if n in REMAKE:  # 照第 1 期那张竖图的内容和人物重画成横图
                layout = "照第二张参考图的内容、人物和道具重画成" + layout
        else:
            scene = PAGES[n][0]
            layout = COVER_LAYOUT if n == 1 else "竖版构图：人物和主要内容在画面中间偏上，脸部完整清楚。"
            size = "1024x1536"
        base.edit(f"{STYLE}。场景：{scene}{layout}{NO_TEXT}", [REMAKE[n]] if n in REMAKE else [REF, GIRL_REF], out, size=size)
    return out


def f(path, size, index=0):
    return ImageFont.truetype(path, int(size * S), index=index)


def P(*v):
    return tuple(int(x * S) for x in v)


def load(n, keep=0.3):
    src = Image.open(art(n)).convert("RGB")
    w, h = src.size  # 2:3 → 3:4
    ch = int(w * 4 / 3)
    y0 = int((h - ch) * keep)
    return src.crop((0, y0, w, y0 + ch)).resize((W, H), Image.LANCZOS).convert("RGBA")


PANEL = (44, 44, 1036, 1084)  # 画格：纸面上的黑框，下方留给旁白


def framed(n, keep=0.12):
    """纸白底，插画裁进黑框画格。"""
    x0, y0, x1, y1 = PANEL
    src = Image.open(art(n)).convert("RGB")
    w, h = src.size
    ch = int(w * (y1 - y0) / (x1 - x0))
    top = int((h - ch) * keep)
    pic = src.crop((0, top, w, top + ch)).resize(((x1 - x0) * S, (y1 - y0) * S), Image.LANCZOS)
    im = Image.new("RGBA", (W, H), PAPER + (255,))
    im.paste(pic, P(x0, y0))
    ImageDraw.Draw(im).rectangle(P(x0, y0, x1, y1), outline=INK, width=5 * S)
    return im


def framed2(n, gap=22):
    """两格页：上下两个黑框画格。"""
    x0, y0, x1, y1 = PANEL
    im = Image.new("RGBA", (W, H), PAPER + (255,))
    hh = (y1 - y0 - gap) / 2
    for i, k in enumerate("ab"):
        src = Image.open(art(f"{n}{k}")).convert("RGB")
        w, h = src.size
        ch = int(w * hh / (x1 - x0))
        top = (h - ch) // 2
        pic = src.crop((0, top, w, top + ch)).resize(((x1 - x0) * S, int(hh * S)), Image.LANCZOS)
        yy = y0 + i * (hh + gap)
        im.paste(pic, P(x0, yy))
        ImageDraw.Draw(im).rectangle(P(x0, yy, x1, yy + hh), outline=INK, width=5 * S)
    return im


def bubble(im, y, s, size=40):
    """夜的对话框：白底黑边、尾巴朝上指向画格，左边挂一枚金色“夜”字章。"""
    d = ImageDraw.Draw(im)
    ft = f(SONG, size, 1)
    w = ft.getlength(s) / S + 96
    h = size + 52
    x = 540 - w / 2
    d.polygon([P(x + w * 0.7, y + 4), P(x + w * 0.78, y - 34), P(x + w * 0.82, y + 4)], fill=(255, 255, 255), outline=INK)
    d.rounded_rectangle(P(x, y, x + w, y + h), radius=h / 2 * S, fill=(255, 255, 255), outline=INK, width=4 * S)
    d.polygon([P(x + w * 0.7 + 3, y + 6), P(x + w * 0.78, y - 28), P(x + w * 0.82 - 3, y + 6)], fill=(255, 255, 255))
    d.text(P(540, y + h / 2), s, font=ft, fill=INK, anchor="mm")
    r = 28
    d.ellipse(P(x - 22, y + h / 2 - r, x - 22 + 2 * r, y + h / 2 + r), fill=AMBER)
    d.text(P(x - 22 + r, y + h / 2), "夜", font=f(SONG, 30, 0), fill=(255, 255, 255), anchor="mm")


def foot(d):
    d.text(P(540, 1404), "和夜一起住 · 01", font=f(SONG, 24, 6), fill=(150, 140, 130), anchor="mm")


def finish(im, n):
    im.convert("RGB").resize((1080, 1440), Image.LANCZOS).save(os.path.join(ART, f"p{n}.png"))


def cover():
    """封面：整张出血，上方黑底压标题；只有“上夜班的猫”是金色。"""
    im = load(1, keep=0.0)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for y in range(int(430 * S)):
        ld.line([(0, y), (W, y)], fill=(0, 0, 0, int(235 * min(1, (1 - y / (430 * S)) * 1.6))))
    im.alpha_composite(layer)
    d = ImageDraw.Draw(im)
    d.text(P(540, 120), "我的新室友", font=f(SONG, 96, 0), fill=(255, 255, 255), anchor="mm")
    d.text(P(540, 250), "是一只上夜班的猫", font=f(SONG, 96, 0), fill=AMBER, anchor="mm")
    d.text(P(540, 340), "和夜一起住 · 01", font=f(SONG, 30, 6), fill=(200, 195, 185), anchor="mm")
    finish(im, 1)


def closing():
    """第 9 页：黑底，夜坐在窗台上；结尾两句和评论区钩子。"""
    im = load(9, keep=0.15)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for y in range(int(860 * S), H):
        ld.line([(0, y), (W, y)], fill=(0, 0, 0, int(255 * min(1, (y / S - 860) / 160))))
    im.alpha_composite(layer)
    d = ImageDraw.Draw(im)
    for i, t in enumerate(["后来我们还是很少碰面。", "但我好像，不太想搬走了。"]):
        d.text(P(540, 1060 + i * 66), t, font=f(SONG, 40, 6), fill=(245, 240, 230), anchor="mm")
    d.text(P(540, 1290), "想知道夜的更多秘密吗？评论区告诉我。", font=f(SONG, 32, 6), fill=AMBER, anchor="mm")
    d.text(P(540, 1404), "和夜一起住 · 01", font=f(SONG, 24, 6), fill=(120, 115, 108), anchor="mm")
    finish(im, 9)


def page(n):
    if n == 1:
        return cover()
    if n == 9:
        return closing()
    scene, items = PAGES[n]
    im = framed2(n) if isinstance(scene, list) else framed(n)
    d = ImageDraw.Draw(im)
    size, lh, bh = 38, 56, 130
    block = sum(bh if isinstance(t, tuple) else lh for t in items)
    k = min(1, 262 / block)  # 字多的页把行距压紧，上下各留一点白
    lh, bh = lh * k, bh * k
    y = PANEL[3] + (1384 - PANEL[3] - block * k) / 2
    for t in items:
        if isinstance(t, tuple):
            bubble(im, y + 26, t[1])
            y += bh
        else:
            d.text(P(540, y + lh / 2), t, font=f(SONG, size, 6), fill=INK, anchor="mm")
            y += lh
    foot(ImageDraw.Draw(im))
    finish(im, n)


def sheet():
    w, h = 360, 480
    out = Image.new("RGB", (w * 5 + 60, h * 2 + 30), (200, 200, 200))
    for i, n in enumerate(sorted(PAGES)):
        out.paste(Image.open(os.path.join(ART, f"p{n}.png")).resize((w, h), Image.LANCZOS), (10 + (i % 5) * (w + 10), 10 + (i // 5) * (h + 10)))
    out.save(os.path.join(HERE, "总览.jpg"), quality=90)


if __name__ == "__main__":
    os.makedirs(ART, exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "page":
        for n in args[1:]:
            page(int(n))
    else:
        ns = [int(a) for a in args] or sorted(PAGES)
        jobs = [k for n in ns for k in ([f"{n}a", f"{n}b"] if isinstance(PAGES[n][0], list) else [n])]
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(art, jobs))
        for n in ns:
            page(n)
        if not args:
            sheet()
