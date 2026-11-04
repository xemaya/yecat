"""和夜一起住：第二轮画风，同一场景五种画风。用法：../../../ucl-video/.venv/bin/python v3.py"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "clip10"))
import assets as base  # noqa: E402

BLANK = os.path.join(HERE, "_blank.png")
SCENE = ("场景：夜里，小小的出租屋，一扇大窗外是城市夜景和月亮。一个二十五六岁的女孩（高挑修长、比例真实不要大头，"
         "利落的齐肩黑色短发，燕麦色衬衫袖子挽起、深灰色直筒长裤，手腕一块旧手表）坐在地板上，放松地靠在一只巨大的黑猫身上；"
         "黑猫“夜”变得像沙发那么大，毛色深黑，琥珀金色的眼睛微微发光，额头一道银色月牙纹，尾巴尖有几点星星似的微光，"
         "它把尾巴圈过来护着她，低头看她。女孩手里捧着一杯热牛奶，侧脸带着累了一天后的放松微笑。"
         "画面干净、道具少。竖版构图，上方 20% 是干净的夜空或墙面（之后放标题）。"
         "画面里不要任何文字、字母、数字、logo。每个人一共只有两只手。")
STYLES = {
    "A日系清新": "清新的日系插画：干净利落的细线稿、柔和的赛璐璐上色、通透的光感和大面积干净色块，颜色清爽明亮，像热门日系插画师的作品。",
    "B深蓝扁平": "极简的扁平插画：深夜蓝和暖橘两种主色，几何化的干净色块、没有线稿、没有纹理，窗外的光和猫眼是唯一的亮点，像高级绘本和杂志插画。",
    "C黑白点金": "黑白漫画线稿风：干净的黑色线条和大块纯黑、纯白，整张画只有一个颜色点缀——猫的金色眼睛、月牙纹和牛奶杯的暖光是琥珀金色，非常克制高级。",
    "D韩系治愈": "韩系治愈插画：柔和低饱和的奶油色调、圆润简洁的造型、轻微的柔光，人物五官简洁可爱但比例修长，像小红书热门的韩系治愈插画。",
    "E三维动画": "院线级三维动画电影的渲染画面（不是手绘）：真实的三维体积感和柔和全局光照、蓬松的毛发渲染、人物是三维动画角色造型，像一部三维动画电影的剧照。",
}


def one(name):
    out = os.path.join(HERE, "v3_" + name + ".png")
    if not os.path.exists(out):
        base.edit(f"画风：{STYLES[name]}\n{SCENE}", [BLANK], out, size="1024x1536")
    return out


def compare():
    font = ImageFont.truetype("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/4a418d1fa4860652a3241e8ee457806c8557fc64.asset/AssetData/Yuanti.ttc", 40, index=2)
    w, h = 520, 780
    out = Image.new("RGB", (w * 5 + 60, h + 90), (245, 240, 232))
    d = ImageDraw.Draw(out)
    for i, name in enumerate(STYLES):
        out.paste(Image.open(os.path.join(HERE, "v3_" + name + ".png")).convert("RGB").resize((w, h), Image.LANCZOS), (10 + i * (w + 10), 80))
        d.text((10 + i * (w + 10) + w / 2, 40), name, font=font, fill=(60, 40, 30), anchor="mm")
    out.save(os.path.join(HERE, "对比v3.jpg"), quality=90)


if __name__ == "__main__":
    with ThreadPoolExecutor(5) as ex:
        print(list(ex.map(one, STYLES)))
    compare()
