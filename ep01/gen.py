"""和夜一起住 · 第 1 期《我的新室友，是一只上夜班的猫》。画风定为暖光厚涂（../style/1暖光厚涂.png 也是角色参考图）。

  ../../../ucl-video/.venv/bin/python gen.py          # 补齐缺的插画，再排全部页 + 总览
  ../../../ucl-video/.venv/bin/python gen.py C 1 5 6  # 只做这几页（B / C 选画风）
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
V = sys.argv.pop(1) if len(sys.argv) > 1 and sys.argv[1] in ("B", "C") else "C"
REF = os.path.join(HERE, "..", "style", {"B": "v3_B深蓝扁平.png", "C": "v3_C黑白点金.png"}[V])
ART = os.path.join(HERE, f"art_{V}")
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
PAGES = {
    1: (f"夜里，老小区合租房的门口，门上一盏暖光小灯。中景：{GIRL}，背靠着门框站着、手里拎着一袋菜，侧过脸看向镜头；"
        f"{CAT}，比普通家猫大一圈，蹲坐在她肩膀高度的鞋柜上，和她并排、脸挨得很近，也看向镜头，金色眼睛在暗处发光，表情骄傲。"
        "两张脸都在画面中部、清楚完整。", None, None),
    2: (f"白天，空荡荡的出租屋客厅，只有一张木椅和一张小桌。{CAT}，正常家猫大小，端坐在木椅上，身边立着一只小小的旧皮箱，"
        f"前爪把一张纸（简历）推过桌面，一本正经地看着对面；{GIRL}，坐在桌子对面，手里捏着那张纸，表情愣住、哭笑不得。",
        ["房租涨了，我决定找个合租室友。", "来看房的，只有一个。"], "我上夜班，白天不吵你。"),
    3: ("夜里，一台打开的双开门冰箱正面特写，冰箱里透出暖光。冰箱正中间竖着贴了一条黑白条纹的分界胶带：左半边是女孩的东西"
        "（几盒外卖、半颗卷心菜、一排酸奶）；右半边是黑猫的东西（几瓶玻璃瓶牛奶、一小罐会发出琥珀金色微光的小星星、一条小鱼干）。"
        "画面里没有人和猫，只有冰箱。",
        ["我们约法三章：", "冰箱一人一半；不动对方的东西；不问对方的工作。"], None),
    4: (f"清晨天刚亮，合租房的门口，门开着一半。{GIRL}，背着包正要出门、回头看了一眼；{CAT}，正常家猫大小，"
        "刚从门外走进来，毛上带着一点夜露、尾巴尖的星光快熄了，抬头看她。一人一猫在门口擦肩而过，门外是淡淡的晨光。",
        ["我们几乎碰不到面。我出门，它回来。", "它说“早”，我说“晚安”。"], None),
    5: ([f"深夜，空无一人的老小区楼下，下着毛毛雨。{GIRL}的背影，背着包、拎着电脑包，疲惫地走回家；"
         "她头顶一盏老路灯亮着温暖的琥珀金色光，是整个黑白画面里唯一的光，路灯杆顶上隐约蹲着一只黑猫的剪影、两点金色的眼睛。",
         f"深夜，合租房的小厨房，只有打开的冰箱透出暖光。{GIRL}的半身近景，站在冰箱前，手里拿着一瓶还冒着热气的玻璃瓶牛奶，"
         "瓶身上贴着一张小纸条，她低头看着纸条，眼眶微红、嘴角却忍不住上扬。画面里没有猫。"],
        ["我加班到最晚的那天，楼下坏了半年的路灯亮了。", "我偷偷哭过的那晚，冰箱里多了一瓶热牛奶，", "纸条上写着：“买多了。”"], None),
    6: (f"中午，阳光明亮的小阳台（背景简单，只有一盆绿植）。中近景、镜头靠近：{GIRL}，单膝蹲着，双手捧到胸前，手心里是缩成只有巴掌大的黑猫夜，"
        "满脸担心地低头看着；巴掌大的夜（在画面中央、看得清楚）毛色暗淡没有光泽，额头的月牙纹不亮了，蔫蔫地趴在她手心里，半睁着眼看她。",
        ["有一天，它早上没回来。", "我在阳台找到它，缩成了巴掌大。"], "上班……用力过头了。"),
    7: (f"白天，公园里的木长椅，身后是虚化的树，阳光是温暖的琥珀金色、洒满画面。{GIRL}，坐在长椅上仰头闭眼晒太阳，"
        "神情放松；她衬衫左胸的口袋里探出一只巴掌大的小黑猫夜的脑袋，下巴搭在口袋边上、眯着眼晒太阳，额头的月牙纹重新有了一点微光。",
        ["我请了一天假。没问它的工作，这是我们的约定。", "只是把它揣进口袋，带它晒了一整天太阳。"], None),
    8: (f"傍晚，合租房的小阳台，远处是城市天际线和落日的琥珀金色余晖。{CAT}已经恢复，变得像沙发那么大，趴在阳台上，"
        f"毛色重新有了光泽、月牙纹发亮；{GIRL}，盘腿坐着、整个人放松地靠在夜毛茸茸的身上，侧头对它笑；夜别过脸去看夕阳，一副嘴硬的样子，"
        "尾巴却圈过来护着她。",
        ["我说：“室友嘛。”", "独立的人也可以互相照顾。不用问太多，在就好。"], ("先", "这次……算我欠你的。")),
    9: (f"深夜，纯黑的背景里只有一扇亮着暖光的小窗。{CAT}，正常家猫大小，坐在窗台上回头看向镜头，金色眼睛和额头的月牙纹发光，"
        "尾巴尖的星光一闪一闪，神情骄傲又有点温柔，像在等人说话。窗台以外的地方全是黑色。", None, None),
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
    """第 9 页：黑底，夜坐在窗台上；评论区找点点、下期预告。"""
    im = load(9, keep=0.15)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for y in range(int(860 * S), H):
        ld.line([(0, y), (W, y)], fill=(0, 0, 0, int(255 * min(1, (y / S - 860) / 160))))
    im.alpha_composite(layer)
    d = ImageDraw.Draw(im)
    lines = ["你身边有没有这样的人：", "话不多，但一直都在？"]
    for i, s in enumerate(lines):
        d.text(P(540, 1010 + i * 64), s, font=f(SONG, 40, 6), fill=(245, 240, 230), anchor="mm")
    d.text(P(540, 1170), "评论区 @点点，跟夜说说你今天怎么了", font=f(SONG, 40, 1), fill=AMBER, anchor="mm")
    d.text(P(540, 1236), "它嘴硬，但都会听。", font=f(SONG, 34, 6), fill=(200, 195, 185), anchor="mm")
    d.text(P(540, 1330), "下期：夜的夜班，到底是什么？", font=f(SONG, 30, 6), fill=(170, 165, 155), anchor="mm")
    d.text(P(540, 1404), "和夜一起住 · 01", font=f(SONG, 24, 6), fill=(120, 115, 108), anchor="mm")
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
