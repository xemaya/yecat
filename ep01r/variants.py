"""第 1 期重做视频要用的变体图（gpt-image 照原图改一处），出到 var/，有缓存。

  ../../../ucl-video/.venv/bin/python variants.py

  n3_first   放灯泡那幕的 H3 首帧：脚跟着地、盒子还关着（尾帧是 art/3.png）
  7_first    晒太阳那幕的 H3 首帧：小猫缩在口袋里只露耳朵尖（尾帧是第 1 期原图）
  5a_dry     回家那幕去掉雨；5a_empty 是同一条街没有人，视频里把她的身影抠出来，一处淡出、更远更小的下一处淡入，停三处
             （5a_walk1 / 5a_walk2 只改迈步姿势，轮流切太突兀，已不用）
  3_empty    冰箱那幕的空冰箱，视频里东西一样一样摆进去
  6_up / 6_curl   巴掌大的夜换两个姿势
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "clip10"))
import assets as base  # noqa: E402

OLD = os.path.join(HERE, "..", "ep01", "art_C")
VAR = os.path.join(HERE, "var")
KEEP = "其他所有东西一点都不要改：构图、机位、线条、画风、黑白和金色、人物和猫的位置大小完全一样。画面里不要任何文字。"
POR, LAND = "1024x1536", "1536x1024"

JOBS = {
    "n3_first": (os.path.join(HERE, "art", "3.png"), POR,
                 "同一张图、同一个房间和机位，只改女孩的动作：她脚跟着地站直（没有踮脚），双手捧着一只盖子关得严严实实的旧鞋盒，"
                 "刚举到衣柜顶的边上，看不见盒子里面。"),
    "7_first": (os.path.join(OLD, "7.png"), POR,
                "同一张图，只改女孩衬衫左胸的口袋：小黑猫整个缩在口袋里，只从口袋边露出两只小小的黑色耳朵尖，看不见它的脸和眼睛。"),
    "5a_dry": (os.path.join(OLD, "5a.png"), LAND,
               "同一张图，但是没有下雨：去掉所有雨丝，地面是干的、没有积水和倒影，女孩手里没有伞。女孩的背影、路灯的金光、灯杆顶上的猫剪影、树和楼都不变。"),
    "3_empty": (os.path.join(OLD, "3.png"), POR,
                "同一张图，只是冰箱里面是空的：每一层隔板上什么都没有，只剩空隔板和冰箱里的暖光，正中间那条黑白条纹的分界胶带还在。"),
    "6_up": (os.path.join(OLD, "6.png"), POR,
             "同一张图，只改女孩手心里的巴掌大小黑猫：它抬起小脑袋，睁着金色的圆眼睛往上看着女孩，耳朵竖起来。"),
    "6_curl": (os.path.join(OLD, "6.png"), POR,
               "同一张图，只改女孩手心里的巴掌大小黑猫：它把身子团成一个更紧的小球，尾巴绕过来盖住鼻子，眼睛闭着。"),
}
EMPTY = {"5a_empty": "同一张图，只把女孩去掉：路上没有人，原来她站的地方补成干的路面和背后的树丛，其余完全不变。"}
WALK = {
    "5a_walk1": "同一张图，只改女孩走路的步子：她的左腿向前迈出一大步、右脚脚跟抬起，手臂随步子自然前后摆动。",
    "5a_walk2": "同一张图，只改女孩走路的步子：她的右腿向前迈出一大步、左脚脚跟抬起，手臂随步子自然前后摆动。",
}


def run(jobs):
    todo = [(p + KEEP, [src], os.path.join(VAR, f"{k}.png"), size) for k, (src, size, p) in jobs.items()
            if not os.path.exists(os.path.join(VAR, f"{k}.png"))]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda a: base.edit(*a), todo))


if __name__ == "__main__":
    os.makedirs(VAR, exist_ok=True)
    run(JOBS)
    run({k: (os.path.join(VAR, "5a_dry.png"), LAND, p) for k, p in {**WALK, **EMPTY}.items()})
