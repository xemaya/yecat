"""她和黑猫夜：角色设定图，同一张设定四种画风对比。"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "clip10"))
import assets as base  # noqa: E402

BLANK = os.path.join(HERE, "_blank.png")
GIRL = ("女孩：二十五六岁的原创年轻女性，独立干练、眼神坚定又温柔，齐肩黑色短发、一侧别在耳后，"
        "穿宽松的燕麦色衬衫（袖子挽到手肘）、深灰色工装裤和白色帆布鞋，手腕上一块旧手表")
CAT = ("黑猫“夜”：一只神秘的大黑猫，毛色深黑、在光下泛着一点蓝紫色光泽，琥珀金色的眼睛微微发光，"
       "额头正中有一道细细的银色月牙形纹路，尾巴尖有几点像星星一样的微光；不戴项圈，神情骄傲、有点嘴硬但很温柔")
SCENE = (f"角色设定图（character sheet）构图，背景是干净的浅暖色纸面，只有地面一点淡淡的影子。{GIRL}。{CAT}。"
         "画面左半边：女孩全身站立、双手插兜，正常大小的夜（普通家猫大小）蹲坐在她肩膀上，尾巴绕过她的脖子；"
         "画面右半边：同一个女孩和同一只夜，但夜变得巨大（趴下时比女孩还高，像一张大沙发），女孩闭着眼、放松地整个人靠在夜毛茸茸的身上，"
         "夜低头用下巴轻轻护着她。左右两组之间留出空隙，两组人物和猫都完整、不要裁切。"
         "竖版构图，上方 15% 留白（之后放标题文字）。每个人一共只有两只手。画面里不要任何文字、字母、数字、logo。")
STYLES = {
    "1暖光厚涂": "温暖的手绘动画电影质感：厚涂笔触、柔和的暖色光影、细腻的毛发和布料质感，像一部治愈系手绘动画电影的设定集原画。",
    "2水彩绘本": "治愈系水彩绘本插画：柔和水彩晕染加一点彩铅线条，颜色淡雅温暖、留白多，像获奖绘本。",
    "3软萌平涂": "干净的软萌扁平插画：细圆润线条、柔和平涂、少量渐变，配色清新，像小红书热门治愈系账号的插画。",
    "4三维动画": "高品质三维动画电影质感：柔和的全局光照、蓬松真实的毛发渲染、略带卡通比例的人物，像院线级三维动画电影的角色设定渲染图。",
}


def one(name):
    out = os.path.join(HERE, name + ".png")
    if not os.path.exists(out):
        base.edit(f"画风：{STYLES[name]}\n{SCENE}", [BLANK], out, size="1024x1536")
    return out


def compare():
    font = ImageFont.truetype("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/4a418d1fa4860652a3241e8ee457806c8557fc64.asset/AssetData/Yuanti.ttc", 40, index=2)
    w, h = 600, 900
    out = Image.new("RGB", (w * 4 + 50, h + 90), (245, 240, 232))
    d = ImageDraw.Draw(out)
    for i, name in enumerate(STYLES):
        out.paste(Image.open(os.path.join(HERE, name + ".png")).convert("RGB").resize((w, h), Image.LANCZOS), (10 + i * (w + 10), 80))
        d.text((10 + i * (w + 10) + w / 2, 40), name, font=font, fill=(60, 40, 30), anchor="mm")
    out.save(os.path.join(HERE, "对比.jpg"), quality=90)


if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex:
        print(list(ex.map(one, STYLES)))
    compare()
