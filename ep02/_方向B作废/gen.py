"""和夜一起住 · 第 2 期《报价 800，我室友站了起来》（剧本见 剧本.md）。画风 C 黑白点金，版式同第 1 期。

  ../../../ucl-video/.venv/bin/python gen.py          # 补齐缺的插画，再排全部页 + 总览
  ../../../ucl-video/.venv/bin/python gen.py 1 4 8    # 只做这几页（样张）
  ../../../ucl-video/.venv/bin/python gen.py page 5   # 只重新排版
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "clip10"))
import assets as base  # noqa: E402

V = "C"
REF = os.path.join(HERE, "..", "style", {"B": "v3_B深蓝扁平.png", "C": "v3_C黑白点金.png"}[V])
ART = os.path.join(HERE, "art")
EP = "02"
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
CAT = ("黑猫夜：就是参考图里的黑猫，毛色深黑泛一点蓝紫光泽，琥珀金色的眼睛微微发光，额头一道银色月牙纹，"
       "尾巴尖有几点星星似的微光，不戴项圈")
LAYOUT = "竖版构图：人物和主要内容在画面上方 72%，画面下方 28% 是较暗、简单的地面或前景（之后要压文字），不要把重要内容放在下方。"
COVER_LAYOUT = "竖版构图：画面上方 30% 是简单干净、偏暗的背景（之后压大标题，这里不能有人脸），人物在画面中部，下方 15% 简单干净。"
NO_TEXT = "画面里不要任何文字、字母、数字、logo、门牌上的字。每个人一共只有两只手。"

# 页：(插画场景，两格的页给两个场景, 独白行, 夜的台词)；夜的台词默认排在独白后面，"夜先说" 的页把台词写成 ("先", 台词)
MAN = "维修师傅：原创的普通中年男人，圆脸、短寸头、工装背带裤、腰上挂着工具包，表情市侩但不凶，是喜剧角色"
PAGES = {
    1: (f"白天，合租房的门厅。{GIRL}，抱着胳膊站在画面前方，自信地看向镜头、嘴角带一点得意的笑；她身后，{CAT}变得巨大，"
        "几乎占满整个门厅、耳朵快顶到天花板，安静地坐着，半眯着发光的金色眼睛居高临下地往镜头这边看，尾巴在她脚边绕了半圈。"
        "两张脸都在画面中部偏下、清楚完整。", None, None),
    2: ([f"早上，狭小的浴室。{GIRL}，头发湿漉漉、肩上搭着毛巾，皱眉看着墙上那台老式电热水器，热水器上的故障小灯亮着琥珀金色，"
         "花洒在滴冷水。画面里没有猫。",
         f"白天，合租房客厅的布艺沙发角落。{CAT}，正常家猫大小，团成一个圆圆的黑毛球睡得很沉，尾巴盖着鼻子，"
         "窗帘拉着，只透进一条光。画面里没有人。"],
        ["热水器坏了，我约了维修师傅。", "夜白天要睡觉，团成一团，叫不醒。"], None),
    3: (f"白天，浴室门口。{MAN}，站在热水器前只瞟了一眼，转过头竖起一根手指报价，一副“这个很贵”的表情；"
        f"{GIRL}，站在旁边、手里攥着手机，眉头微皱、有点犹豫。她身后的白墙上，投着她自己的一道淡淡的影子，影子的头顶有两只尖尖的猫耳朵。",
        ["师傅看了一眼：“主板烧了，换一个，800。”", "我还在犹豫……"], None),
    4: (f"白天，浴室门口的走廊，同一个场景。{GIRL}，站在画面中间偏左，还是那个犹豫的姿势；她身后，{CAT}无声地变得巨大，"
        "从她背后慢慢站起来，头快顶到天花板，整个身体像一团黑影把走廊填满，半眯着发光的金色眼睛居高临下地看着师傅，表情平静；"
        f"画面右侧的{MAN}，抬头看着大猫，整个人僵住，手里的扳手掉了一半，额头冒出一滴汗。",
        ["身后的影子，慢慢变大了。"], None),
    5: ([f"浴室里，热水器前。{MAN}的中近景，满头大汗，拿着螺丝刀飞快地拧热水器下面的一颗螺丝，眼睛紧张地往旁边偷瞄；"
         "画面边缘露出一只巨大的黑色猫爪，安静地搭在门框上。",
         f"门口。{MAN}，弯着腰、双手恭恭敬敬地递出一张小小的收据，满脸讨好的笑；{GIRL}伸手去接，表情忍着笑。"
         "收据上不要写任何文字。"],
        ["师傅擦了擦汗：“……其实拧紧个螺丝就行。”", "“80。”"], None),
    6: ([f"合租房客厅。一位原创的中年房东阿姨，戴眼镜、拿着一张单子，正要开口；{GIRL}坐在她对面；"
         f"{GIRL}身后的沙发上，{CAT}巨大地趴着，下巴搁在沙发背上，金色眼睛半睁着看着房东。房东的表情僵住。",
         f"合租房门口，门开着。一位原创的年轻快递员，举着一个纸箱，表情僵住；门后探出{CAT}巨大的脑袋，"
         "占满半扇门，金色眼睛平静地看着他。"],
        ["后来，房东想扣押金，快递想收上楼费。", "结局都一样。"], None),
    7: (f"晚上，客厅只开着一盏暖光落地灯。{CAT}恢复正常家猫大小，团在沙发上闭着眼、一脸“我在睡觉”的表情，一只耳朵却竖着；"
        f"{GIRL}，蹲在沙发前，伸出一根手指戳它的肚子，笑着歪头看它。",
        ["我问它：“你一句话都没说，他们怕什么？”"], "我在睡觉。"),
    8: (f"白天，合租房门口的地上放着一个圆圆的软垫。{CAT}，正常家猫大小，被端端正正地摆坐在软垫上、正对着门，"
        f"一脸不情愿、耳朵往后撇；{GIRL}，蹲在它身后，双手刚放开它，憋着笑。",
        ["从那以后，有人上门，", "我都先把室友抱到门口坐着。"], "……这算加班。"),
    9: (f"深夜，纯黑的背景，合租房的门开着一条缝，门外是黑暗的楼道。{CAT}，正常家猫大小，嘴里叼着一盏小小的发着琥珀金色光的灯笼，"
        "正要出门，回头看了一眼镜头，金色眼睛和额头的月牙纹发光。门以外的地方全是黑色。", None, None),
}


def art(n):
    """n：页码，或 "5a" / "5b"（两格页的上下格，横图）。"""
    out = os.path.join(ART, f"{n}.png")
    if not os.path.exists(out):
        if isinstance(n, str):
            scene = PAGES[int(n[0])][0]["ab".index(n[1])]
            layout, size = "横版构图：人物和主要内容在画面中间，四周留一点余地。", "1536x1024"
        else:
            scene = PAGES[n][0]
            layout = COVER_LAYOUT if n == 1 else "竖版构图：人物和主要内容在画面中间偏上，脸部完整清楚。"
            size = "1024x1536"
        base.edit(f"{STYLE}。场景：{scene}{layout}{NO_TEXT}", [REF], out, size=size)
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
    d.text(P(540, 1404), f"和夜一起住 · {EP}", font=f(SONG, 24, 6), fill=(150, 140, 130), anchor="mm")


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
    d.text(P(540, 120), "师傅报价 800", font=f(SONG, 96, 0), fill=(255, 255, 255), anchor="mm")
    d.text(P(540, 250), "我室友站了起来", font=f(SONG, 96, 0), fill=AMBER, anchor="mm")
    d.text(P(540, 340), f"和夜一起住 · {EP}", font=f(SONG, 30, 6), fill=(200, 195, 185), anchor="mm")
    finish(im, 1)


def closing():
    """第 9 页：黑底，夜叼着小灯笼出门；回一下上期悬念，下期预告。"""
    im = load(9, keep=0.15)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for y in range(int(860 * S), H):
        ld.line([(0, y), (W, y)], fill=(0, 0, 0, int(255 * min(1, (y / S - 860) / 160))))
    im.alpha_composite(layer)
    d = ImageDraw.Draw(im)
    for i, s in enumerate(["至于它的夜班到底是什么——", "它还是不让问。"]):
        d.text(P(540, 1060 + i * 64), s, font=f(SONG, 40, 6), fill=(245, 240, 230), anchor="mm")
    d.text(P(540, 1250), "下期：跟着夜去上班", font=f(SONG, 40, 1), fill=AMBER, anchor="mm")
    d.text(P(540, 1404), f"和夜一起住 · {EP}", font=f(SONG, 24, 6), fill=(120, 115, 108), anchor="mm")
    finish(im, 9)


def page(n):
    if n == 1:
        return cover()
    if n == 9:
        return closing()
    scene, lines, say = PAGES[n]
    im = framed2(n) if isinstance(scene, list) else framed(n)
    d = ImageDraw.Draw(im)
    size, lh = 38, 62
    first = isinstance(say, tuple)
    say = say[1] if first else say
    block = len(lines) * lh + (150 if say else 0)
    y = PANEL[3] + (1380 - PANEL[3] - block) / 2
    if say and first:
        bubble(im, y + 40, say)
        y += 150
    for i, s in enumerate(lines):
        d.text(P(540, y + i * lh + lh / 2), s, font=f(SONG, size, 6), fill=INK, anchor="mm")
    if say and not first:
        bubble(im, y + len(lines) * lh + 50, say)
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
