"""和夜一起住 · 第 2 期插画。画面直接从 剧本.md 读（../tools/check_script.py 的 parse），画风和人物描述沿用 ../ep01r/gen.py。

  ../../../ucl-video/.venv/bin/python gen.py 1 6 7     # 出这几页的插画（有缓存），两格页写 5a / 5b
  ../../../ucl-video/.venv/bin/python gen.py           # 出全部插画

P2 不重画：第 1 期不下雨的回家图（../ep01r/var/5a_dry.png）去掉弯臂上的猫。
旧的方向 B（报价 800）在 _方向B作废/。
"""
import importlib.util
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_script import parse  # noqa: E402

# 第 1 期重做的 gen.py：画风、人物、构图的写法。和本文件同名，只能按路径载入
_spec = importlib.util.spec_from_file_location("ep01r_gen", os.path.join(ROOT, "ep01r", "gen.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)
base = G.base

ART = os.path.join(HERE, "art")
SCRIPT = asdict(parse(os.path.join(HERE, "剧本.md")))
PAGES = {p["no"]: p for p in SCRIPT["pages"]}
# 夜在班上的样子（准则/写稿.md「画面」）：身体溶在黑里，只看得出边缘一圈琥珀金轮廓线
CAT_WORK = G.CAT + "；夜里在班上时，身体是实心的黑，边缘有一圈细细的琥珀金发光轮廓线"
EDITS = {2: (os.path.join(ROOT, "ep01r", "var", "5a_dry.png"),
             "同一张图，只把路灯弯臂顶上那只黑猫的剪影去掉，弯臂上空着，补成夜空和灯杆。其他所有东西一点都不要改：构图、线条、画风、"
             "黑白和金色、女孩的位置大小、路灯的光完全一样。画面里不要任何文字。")}
# 剧本里的路灯参考是第 1 期的 5a（下雨、弯臂上有猫），照着画会把雨和猫一起画进来：换成 P2 这张不下雨、没猫的
LAMP_REF = {"ep01/art_C/5a.png": os.path.join(ART, "2.png")}
DARK = "路灯的灯罩被拆开了，灯是黑的、一点光都不发；画面里只有一盏路灯，没有别的灯。没有下雨。"
# 出图补充：剧本写了、但图模型老画错的地方
HINT = {
    "5b": DARK,
    "6": DARK + "镜头放在梯子下方很低的地方往上仰拍。路灯弯臂上的黑猫几乎完全融进黑夜，看不见身体和毛，只看得见两点琥珀金的眼睛、"
         "额头一道金色月牙和一圈极淡的金色耳朵轮廓。",
    "7": DARK,
    "8a": DARK,
}


def has_cat(scene):
    return "没有猫" not in scene and ("夜" in scene.replace("夜空", "").replace("夜晚", "") or "猫" in scene)


def art(key):
    """key：页码，或 "5a" / "5b"（两格页的上下格，横图）。"""
    out = os.path.join(ART, f"{key}.png")
    if os.path.exists(out):
        return out
    no = int(str(key).rstrip("ab"))
    p = PAGES[no]
    if no in EDITS:
        src, prompt = EDITS[no]
        base.edit(prompt, [src], out, size="1536x1024")
        return out
    panel = str(key)[-1] if str(key)[-1] in "ab" else ""
    scene = p["scenes"][panel]
    if panel:
        layout, size = "横版构图：人物和主要内容在画面中间，四周留一点余地。", "1536x1024"
    else:
        layout = G.COVER_LAYOUT if no == 1 else "竖版构图：人物和主要内容在画面中间偏上，脸部完整清楚。"
        size = "1024x1536"
    refs = [G.REF, G.GIRL_REF]
    extra = [LAMP_REF.get(r, os.path.join(ROOT, r)) for r in p["refs"]][:1]
    ref_note = "第三张参考图是故事里那个地方（路灯、房间）原来的样子，场景照它画，但人物的动作和构图照这里写的。" if extra else ""
    who = (G.GIRL + "。" if "她" in scene else "") + (CAT_WORK + "。" if has_cat(scene) else "")
    base.edit(f"{G.STYLE}。{who}场景：{scene}{HINT.get(str(key), "")}{layout}{ref_note}{G.NO_TEXT}", refs + extra, out, size=size)
    return out


def keys():
    for no, p in PAGES.items():
        yield from ([f"{no}{k}" for k in sorted(p["scenes"])] if "a" in p["scenes"] else [str(no)])


if __name__ == "__main__":
    os.makedirs(ART, exist_ok=True)
    want = sys.argv[1:] or list(keys())
    with ThreadPoolExecutor(6) as ex:
        print(list(ex.map(art, want)))
