#!/usr/bin/env python3
"""和夜一起住 · 剧本检查。只用标准库，系统自带的 python3 就能跑。

  python3 tools/check_script.py ep02/剧本.md          # 查一集
  python3 tools/check_script.py                       # 查所有 ep*/剧本.md
  python3 tools/check_script.py ep02/剧本.md --json   # 输出解析结果（给视频方排版用）

格式见 准则/剧本模板.md，规则见 准则/写稿.md。
错误必须清零；警告逐条看，要么改，要么在剧本“自审”一节写明为什么保留。
只查数得出来的东西，台词好不好还要过 准则/台词红队.md。
"""
import argparse
import glob
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "docs", "第一季设定与12集_v2.md")

# 视频时长：照 ep01/video.py 和 ep01r/video.py
LEAD, GAP, TAIL, FADE, END_HOLD = 0.6, 0.35, 0.9, 0.45, 3.5
MIN_SHOT, COVER_MIN, HIGHLIGHT_MIN = 4.0, 5.5, 7.0

EXCUSES = {1: "买多了", 2: "那就是风", 5: "路过", 8: "路上捡的", 10: "饺子，买多了", 12: "风写的"}
EP01_LINES = ["我上夜班，白天不吵你。", "买多了。", "上班……用力过头了。", "这次……算我欠你的。", "室友嘛。"]
META_KEYS = ["揭开", "推进", "借口", "尾尖闪", "名场面", "画面字", "通宵", "体型", "第9页收法", "她的手法", "偏离v2"]
ENDINGS = ["旁白", "晴", "夜", "纸条", "空镜"]
EP01_ENDING = "旁白"

EMOTION = ["难过", "伤心", "开心", "高兴", "快乐", "感动", "失望", "生气", "愤怒", "害怕", "孤独", "孤单", "心疼",
           "幸福", "心动", "害羞", "委屈", "想哭", "难受", "激动", "安心", "舍不得"]
CONNECT = ["然后", "接着", "后来", "于是", "那天", "有一天", "第二天", "从那以后", "就这样", "因为", "所以", "其实", "说实话"]
UNFILMABLE = ["意识到", "感到", "感觉", "觉得", "心想", "想起", "回想", "回忆", "明白", "气氛", "仿佛", "似乎", "内心",
              "心里", "心中", "知道"]
THEME = ["原来", "终于", "明白", "才知道", "一个人", "陪伴", "幸福", "孤单", "孤独", "治愈", "意义", "不再"]
BOSS = ["女人", "我的人", "听话", "不许", "给我"]
ORDER_START = ["别", "不要", "快", "过来", "回来", "睡", "穿", "吃", "喝", "记得", "小心", "等我", "跟我"]
TROPES = ["停电", "发烧", "卡在门框", "卡在窗框", "读心", "俯瞰全城", "尾巴扶"]
WRITING = ["写着", "字样", "上面写", "招牌上"]
# 上屏的字不写专业术语（配方「文案」，用户定的）
JARGON = re.compile(r"\d+\s*[Kk](?![A-Za-z])|色温|显色|显指|流明|勒克斯|照度|[Ll]ux|CRI")
# 第 1 期定下的样子，画面里写错了会画成别的
FIXED = {"电动车": "她走路回家，背帆布包、腰包，没有车（第 1 期 ep01r/var/5a_dry.png）",
         "自行车": "她走路回家，背帆布包、腰包，没有车（第 1 期 ep01r/var/5a_dry.png）",
         "庭院灯": "楼下是弯颈铁杆路灯，灯杆在右、弯臂往左，猫坐在弯臂上（参考 ep02/art/2.png）",
         "灯帽": "楼下是弯颈铁杆路灯，灯杆在右、弯臂往左，猫坐在弯臂上（参考 ep02/art/2.png）"}
HIGHLIGHT_SPAN = (0.40, 0.60)  # 名场面开始的位置占全片的比例（配方）
SOFA = re.compile(r"沙发那么大|沙发大小|像沙发一样大|变成沙发|沙发大的")
NEGATIVE = re.compile(r"没有(?!任何人|人|猫|下雨|雨|字|文字)[\u4e00-\u9fff]{1,4}|不是[\u4e00-\u9fff]{1,4}的")
COMPARE = re.compile(r"更暖|更亮|更暗|比以前|比之前|比平时")
FACE = ["眯着眼", "眯眼", "嘴角", "眼神", "表情", "笑"]
CONTINUOUS = re.compile(r"一盏一盏|一颗一颗|一个一个|一件一件|一段一段|慢慢地?(?:变|亮|走|飘)")

HANZI = re.compile(r"[一-鿿0-9A-Za-z]")
SENT = re.compile(r"[。？！?!；;]+")
CALLBACK = re.compile(r"（呼应[^）]*）\s*$")


def hanzi(s):
    return "".join(HANZI.findall(s))


def sentences(s):
    return [x for x in SENT.split(s) if hanzi(x)]


def secs(text):
    return max(1.6, 0.45 + 0.2 * len(text))  # 配方：约每秒 5 个字


@dataclass
class Line:
    panel: str      # "" / "a" / "b"
    who: str        # 剧本里写的说话人
    text: str       # 上屏的字
    kind: str       # 标题 / 旁白 / 晴 / 夜 / 画面字 / 配角
    writer: str     # 按谁的口吻查：夜 / 晴 / ""
    callback: str   # “呼应 第N集”，不上屏
    lineno: int


@dataclass
class Page:
    no: int
    tag: str
    beat: str = ""
    scenes: dict = field(default_factory=dict)   # {"": 画面} 或 {"a": 上格, "b": 下格}
    lines: list = field(default_factory=list)
    dur: dict = field(default_factory=dict)      # panel -> 建议秒数
    note: str = ""
    refs: list = field(default_factory=list)     # 参考图，相对仓库根目录
    lineno: int = 0
    has_text_field: bool = False

    @property
    def panels(self):
        return ["a", "b"] if "a" in self.scenes or "b" in self.scenes else [""]


@dataclass
class Episode:
    path: str
    no: int = 0
    title: str = ""
    meta: dict = field(default_factory=dict)
    pages: list = field(default_factory=list)
    review: str = ""
    problems: list = field(default_factory=list)   # 解析时就发现的错误


def classify(who):
    if who == "标题":
        return "标题", ""
    if who == "旁白":
        return "旁白", ""
    if who in ("晴", "夜"):
        return who, who
    if who == "星光字":
        return "画面字", "夜"
    m = re.match(r"^(纸条|飘字)(?:（(晴|夜)）)?$", who)
    if m:
        return "画面字", m.group(2) or ""
    return "配角", ""


def parse(path):
    ep = Episode(path=path)
    section, page, in_text = None, None, False
    with open(path, encoding="utf-8") as fh:
        rows = fh.read().splitlines()
    for i, raw in enumerate(rows, 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^#\s*第\s*(\d+)\s*集\s*[｜|]\s*(.+)$", line)
        if m:
            ep.no, ep.title = int(m.group(1)), m.group(2).strip()
            continue
        m = re.match(r"^##\s*(.+?)\s*$", line)
        if m:
            head = m.group(1)
            in_text = False
            pm = re.match(r"^P(\d+)\s*(.*)$", head)
            if pm:
                page = Page(no=int(pm.group(1)), tag=pm.group(2).strip(), lineno=i)
                ep.pages.append(page)
                section = "page"
            elif head == "本集":
                section, page = "meta", None
            elif head == "自审":
                section, page = "review", None
            else:
                section, page = None, None
            continue
        if section == "review":
            ep.review += line + "\n"
            continue
        if in_text and re.match(r"^\s+-", line):
            body = re.sub(r"^\s+-\s*", "", line)
            pm = re.match(r"^([ab])\s+(.*)$", body)
            panel, body = (pm.group(1), pm.group(2)) if pm else ("", body)
            if body.strip() in ("（无字）", "(无字)"):
                continue
            wm = re.match(r"^([^：:]+?)\s*[：:]\s*(.+)$", body)
            if not wm:
                ep.problems.append((f"P{page.no}", f"第 {i} 行看不懂：{body}（应为“说话人：内容”）"))
                continue
            who, text = wm.group(1).strip(), wm.group(2).strip()
            cb = CALLBACK.search(text)
            callback = ""
            if cb:
                callback, text = cb.group(0).strip("（） "), text[: cb.start()].strip()
            kind, writer = classify(who)
            page.lines.append(Line(panel, who, text, kind, writer, callback, i))
            continue
        fm = re.match(r"^-\s*([^：:]+?)\s*[：:]\s*(.*)$", line)
        if not fm:
            continue
        key, val = fm.group(1).replace(" ", ""), fm.group(2).strip()
        if section == "meta":
            ep.meta[key] = val
        elif section == "page":
            in_text = key == "字"
            if key == "拍点":
                page.beat = val
            elif key in ("画面", "画面a", "画面b"):
                page.scenes[key[2:]] = val
            elif key == "字":
                page.has_text_field = True
            elif key == "时长":
                for part in re.split(r"[，,；;\s]+(?=[ab]\s|\d)", val):
                    dm = re.match(r"^(?:([ab])\s*)?(\d+(?:\.\d+)?)", part.strip())
                    if dm:
                        page.dur[dm.group(1) or ""] = float(dm.group(2))
            elif key == "落地备注":
                page.note = val
            elif key == "参考":
                page.refs = [x for x in re.split(r"[、，,\s]+", val) if x]
    return ep


def v2_section(no):
    """v2 里这一集的段落，去掉引号里的台词（台词是有意沿用的）。"""
    if not os.path.exists(V2):
        return ""
    text = open(V2, encoding="utf-8").read()
    m = re.search(rf"^## 第 {no} 集｜.*?(?=^## |^# )", text, re.S | re.M)
    if not m:
        return ""
    return re.sub(r"“[^”]*”|「[^」]*」", "", m.group(0))


def grams(s, n=6):
    out = set()
    for seg in re.split(r"[^一-鿿0-9A-Za-z]+", s):
        out.update(seg[i:i + n] for i in range(len(seg) - n + 1))
    return out


def page_no(val):
    m = re.search(r"P(\d+)", val or "")
    return int(m.group(1)) if m else None


def load_others(ep):
    others = {}
    for p in glob.glob(os.path.join(ROOT, "ep*", "剧本.md")):
        if os.path.abspath(p) == os.path.abspath(ep.path):
            continue
        try:
            o = parse(p)
        except Exception:
            continue
        if o.no and o.pages:
            others[o.no] = o
    return others


def estimate(ep):
    hi = page_no(ep.meta.get("名场面"))
    shots = []
    for p in sorted(ep.pages, key=lambda p: p.no):
        for k in p.panels:
            caps = [ln for ln in p.lines if ln.kind != "标题" and (ln.panel == k or (k == "a" and ln.panel == ""))]
            d = LEAD + sum(secs(ln.text) for ln in caps) + GAP * max(0, len(caps) - 1) + TAIL if caps else 0
            floor = COVER_MIN if p.no == 1 else HIGHLIGHT_MIN if p.no == hi else MIN_SHOT
            d = max(d, floor, p.dur.get(k, 0))
            shots.append((p.no, k, d))
    if not shots:
        return 0, 0, None
    shots[-1] = (*shots[-1][:2], shots[-1][2] + END_HOLD)
    t, hi_t = 0.0, None
    for i, (no, _k, d) in enumerate(shots):
        if no == hi and hi_t is None:
            hi_t = t
        t += d - (FADE if i < len(shots) - 1 else 0)
    return len(shots), t, hi_t


def check(ep):
    E, W = [], []
    err = lambda where, msg: E.append((where, msg))
    warn = lambda where, msg: W.append((where, msg))
    for where, msg in ep.problems:
        err(where, msg)

    # 结构
    if not ep.no:
        err("标题", "第一行要写成“# 第 NN 集｜标题”")
    for k in META_KEYS:
        if k not in ep.meta:
            err("本集", f"缺“{k}”")
    nos = [p.no for p in ep.pages]
    if nos != list(range(1, 10)):
        err("页", f"要正好是 P1–P9，现在是 {nos}")
    pages = {p.no: p for p in ep.pages}
    for p in ep.pages:
        if not p.beat:
            err(f"P{p.no}", "缺拍点")
        if not p.scenes:
            err(f"P{p.no}", "缺画面")
        if not p.has_text_field:
            err(f"P{p.no}", "缺“字”（没有字就写“（无字）”）")
        two = p.panels != [""]
        if two and not ("a" in p.scenes and "b" in p.scenes):
            err(f"P{p.no}", "两格页要同时写画面a和画面b")
        for ln in p.lines:
            if two and not ln.panel and ln.kind != "标题":
                warn(f"P{p.no}", f"两格页的字要标 a 或 b：{ln.text}")
            if not two and ln.panel:
                warn(f"P{p.no}", f"单格页不用标 {ln.panel}：{ln.text}")

    lines = [ln for p in sorted(ep.pages, key=lambda p: p.no) for ln in p.lines]
    body = [ln for ln in lines if ln.kind != "标题"]
    where_of = {}
    for p in ep.pages:
        for ln in p.lines:
            where_of[id(ln)] = f"P{p.no}{ln.panel}"
    at = lambda ln: where_of[id(ln)]

    # 旁白
    for p in ep.pages:
        nar = [s for ln in p.lines if ln.kind == "旁白" for s in sentences(ln.text)]
        cap = 2 if p.no == 9 else 0 if p.no == 1 else 1
        if len(nar) > cap:
            (warn if p.no == 1 else err)(f"P{p.no}", f"旁白 {len(nar)} 句，这一页最多 {cap} 句")
    total = sum(len(hanzi(ln.text)) for ln in body)
    nar_total = sum(len(hanzi(ln.text)) for ln in body if ln.kind == "旁白")
    if total and nar_total / total > 0.5:
        err("全集", f"旁白占 {nar_total / total:.0%}，要在一半以下")
    used = [(c, ln) for ln in body if ln.kind == "旁白" for c in CONNECT if c in ln.text]
    if len(used) > 2:
        warn("全集", "旁白里的时间、因果连接词超过两个：" + "、".join(f"{c}（{at(ln)}）" for c, ln in used))
    nars = [ln for ln in body if ln.kind == "旁白"]
    for a, b in zip(nars, nars[1:]):
        if a.text.startswith("我") and b.text.startswith("我"):
            warn(at(b), f"连着两句旁白都用“我”开头：{a.text} / {b.text}")
    src = grams(v2_section(ep.no))
    for ln in nars:
        hit = sorted(g for g in grams(ln.text) if g in src)
        if hit:
            warn(at(ln), f"旁白和 v2 事件段有连续 6 个字一样（{hit[0]}），像在照抄梗概：{ln.text}")

    # 各人的口吻
    for ln in body:
        if ln.kind == "旁白" and len(ln.text) > 25:
            warn(at(ln), f"旁白一句 {len(ln.text)} 个字符，视频方定的是不超过 25 个：{ln.text}")
        elif len(ln.text) > 30:
            warn(at(ln), f"一句 {len(ln.text)} 个字符，字幕会超过两行：{ln.text}")
        m = JARGON.search(ln.text)
        if m:
            err(at(ln), f"上屏的字不写专业术语“{m.group(0)}”（配方「文案」）：{ln.text}")
        if ln.kind in ("旁白", "晴") or ln.writer == "晴":
            for w in EMOTION:
                if w in ln.text:
                    warn(at(ln), f"直接说出情绪“{w}”，换成动作或道具：{ln.text}")
        if ln.kind == "画面字" and not ln.writer:
            warn(at(ln), f"{ln.who}要标出谁写的：纸条（晴）/ 纸条（夜）/ 星光字 / 飘字（晴|夜）")
        if ln.writer == "晴":
            for s in sentences(ln.text):
                if len(hanzi(s)) > 15:
                    warn(at(ln), f"晴的一句超过 15 个字：{s}")
        if ln.writer == "夜":
            for s in sentences(ln.text):
                n = len(hanzi(s))
                if n > 8:
                    err(at(ln), f"夜的一句 {n} 个字，要 8 个字以内：{s}")
            if re.search(r"[！!]", ln.text):
                err(at(ln), f"夜不用感叹号：{ln.text}")
            for w in BOSS:
                if w in ln.text:
                    err(at(ln), f"夜不说霸总词“{w}”：{ln.text}")
            bare = ln.text.lstrip("…. ")
            for w in ORDER_START:
                if bare.startswith(w):
                    warn(at(ln), f"夜像在下指令（“{w}”开头），它只说陈述句：{ln.text}")
                    break

    # 配角
    side = [ln for ln in body if ln.kind == "配角"]
    if len({ln.who for ln in side}) > 1:
        warn("全集", "开口的配角超过一个：" + "、".join(sorted({ln.who for ln in side})))
    if len(side) > 2:
        warn("全集", f"配角说了 {len(side)} 句，最多两句")

    # 画面
    tail_pages = []
    for p in ep.pages:
        for k, sc in p.scenes.items():
            w = f"P{p.no}{k}"
            for f, why in FIXED.items():
                if f in sc:
                    warn(w, f"画面里有“{f}”：{why}")
            for u in UNFILMABLE:
                if u in sc:
                    warn(w, f"画面里有拍不出来的“{u}”，改成动作、表情、道具或光")
            if "没有猫" not in sc and "猫" not in sc:
                warn(w, "画面没提猫：有猫就写“黑猫夜”，没有猫就写明“画面里没有猫”，不然会凭空画一只（配方第 2 条）")
            if any(x in sc for x in WRITING) and not any(ln.kind == "画面字" for ln in p.lines):
                warn(w, "画面里要出字？AI 不画字，写成一行“纸条（…）：”或“星光字：”，由视频方叠")
            if "尾尖" in sc and any(x in sc for x in ("闪", "变亮", "亮起")):
                tail_pages.append(w)
            if SOFA.search(sc) and ep.no != 5:
                warn(w, "沙发大全季只在第 5 集再用一次")
            if "巴掌大" in sc:
                warn(w, "巴掌大只在第 1 期出现过，本季不再用")
            for t in TROPES:
                if t in sc:
                    warn(w, f"“{t}”是红队清单里的桥段，全季最多一次，记进 准则/连续性.md")
            if "猫" in sc and "没有猫" not in sc and "月牙" not in sc:
                warn(w, "画面里有夜，写明月牙亮度（暗 / 微光 / 发亮），v2 制作备注")
            neg = NEGATIVE.search(sc)
            if neg:
                warn(w, f"“{neg.group(0)}”是否定句，出图容易反着画，改成写看得见的样子（比如“空的螺口灯座”）")
            cmp_ = COMPARE.search(sc)
            if cmp_:
                warn(w, f"“{cmp_.group(0)}”画不出来，写成看得见的差别（灯泡形状、光的颜色）")
            cont = CONTINUOUS.search(sc)
            if cont:
                warn(w, f"“{cont.group(0)}”是连续动作，单张图画不出来，写成停住的那一刻（比如“已经亮了三盏”）；动作交给动效写在落地备注")
            if "剪影" in sc and "眼" in sc:
                warn(w, "剪影里看不见眼睛")
            if "远景" in sc:
                hits = [f for f in FACE if f in sc]
                if hits:
                    warn(w, f"远景里看不清“{'、'.join(hits)}”")
    if len(tail_pages) > 1:
        err("全集", f"尾尖闪了 {len(tail_pages)} 次（{'、'.join(tail_pages)}），每集最多一次")
    want = page_no(ep.meta.get("尾尖闪"))
    if want and not any(page_no(t) == want for t in tail_pages):
        warn(f"P{want}", "本集写了尾尖闪在这一页，画面里没写“尾尖……闪/变亮”")
    if not want and tail_pages and "无" in ep.meta.get("尾尖闪", ""):
        warn("本集", "本集写了尾尖闪“无”，画面里却有")

    hi = page_no(ep.meta.get("名场面"))
    if hi and hi in pages and any(ln.kind != "标题" for ln in pages[hi].lines):
        warn(f"P{hi}", "名场面页默认无字，交给金光动效")
    if not hi:
        err("本集", "名场面要写成 P几")

    text_spots = sorted({at(ln) for ln in body if ln.kind == "画面字"})
    if len(text_spots) > 1 and "例外" not in ep.meta.get("画面字", ""):
        warn("全集", f"画面字出现在 {len(text_spots)} 处（{'、'.join(text_spots)}），v2 定的是每集最多一处；例外要在“本集 · 画面字”里写明")
    meta_spot = ep.meta.get("画面字", "")
    if text_spots and "无" == meta_spot.strip():
        warn("本集", "本集写了画面字“无”，剧本里却有")

    # 第 9 页
    if 9 in pages:
        for ln in pages[9].lines:
            hits = [w for w in THEME if w in ln.text] if ln.kind == "旁白" else []
            if hits:
                warn(f"P9{ln.panel}", f"第 9 页旁白有“{'、'.join(hits)}”，像在把主题说出来：{ln.text}")
    end = ep.meta.get("第9页收法", "")
    if end and not any(e in end for e in ENDINGS):
        warn("本集", f"第9页收法写成 {'/'.join(ENDINGS)} 之一")

    # 借口链
    exc = ep.meta.get("借口", "").strip("“”「」 ")
    planned = EXCUSES.get(ep.no)
    ye = [ln for ln in body if ln.writer == "夜"]
    if planned and exc != planned:
        warn("本集", f"v2 借口链里第 {ep.no} 集是“{planned}”，这里写的是“{exc}”")
    if not planned and exc and exc != "无":
        warn("本集", f"v2 借口链里第 {ep.no} 集没有借口，新加会冲淡借口链")
    if exc and exc != "无" and not any(hanzi(exc) in hanzi(ln.text) for ln in ye):
        err("本集", f"借口“{exc}”没出现在夜的台词或字里")
    if ep.no != 12:
        for ln in ye:
            if "想跟你" in ln.text or "喜欢" in ln.text:
                warn(at(ln), f"这么直白的话留给第 12 集：{ln.text}")

    # 体型
    if "沙发" in ep.meta.get("体型", "") and ep.no != 5:
        warn("本集", "沙发大全季只在第 5 集再用一次")

    # 和别的集撞台词
    others = load_others(ep)
    seen = {hanzi(t): "第 1 集" for t in EP01_LINES}
    for o in others.values():
        for p in o.pages:
            for ln in p.lines:
                if ln.kind in ("晴", "夜", "画面字", "旁白"):
                    seen.setdefault(hanzi(ln.text), f"第 {o.no} 集")
    for ln in body:
        key = hanzi(ln.text)
        if len(key) >= 3 and key in seen and not ln.callback:
            warn(at(ln), f"和{seen[key]}的字一样，故意的就在句尾加“（呼应 {seen[key]}）”：{ln.text}")
    prev_end = EP01_ENDING if ep.no == 2 else others[ep.no - 1].meta.get("第9页收法", "") if ep.no - 1 in others else ""
    if prev_end and end and prev_end == end:
        warn("本集", f"第 9 页收法和第 {ep.no - 1} 集一样（{end}），连着两集要换")
    for p in ep.pages:
        for r in p.refs:
            if not os.path.exists(os.path.join(ROOT, r)):
                warn(f"P{p.no}", f"参考图不存在：{r}")

    stats = {k: sum(len(hanzi(ln.text)) for ln in body if ln.kind == k) for k in ("旁白", "晴", "夜", "配角", "画面字")}
    n_shots, dur, hi_t = estimate(ep)
    lo, up = HIGHLIGHT_SPAN
    if hi_t is not None and dur and not lo <= hi_t / dur <= up:
        warn(f"P{hi}", f"名场面约在全片 {hi_t / dur:.0%} 处开始，配方定的是 {lo:.0%}–{up:.0%}；"
                       "调无字镜头的建议时长，不靠加字")
    return E, W, stats, total, (n_shots, dur, hi_t)


def report(ep):
    E, W, stats, total, (n_shots, dur, hi_t) = check(ep)
    rel = os.path.relpath(ep.path, ROOT)
    print(f"{rel}  第 {ep.no:02d} 集｜{ep.title}")
    share = f"（{stats['旁白'] / total:.0%}）" if total else ""
    print(f"  字数：旁白 {stats['旁白']}{share} · 晴 {stats['晴']} · 夜 {stats['夜']} · 配角 {stats['配角']} · 画面字 {stats['画面字']}")
    hi = ep.meta.get("名场面", "?")
    lo, up = HIGHLIGHT_SPAN
    hi_s = (f"，名场面 {hi} 约从 {hi_t:.0f} 秒开始（全片 {hi_t / dur:.0%}，配方定 {lo:.0%}–{up:.0%}）"
            if hi_t is not None and dur else "")
    print(f"  估算：{n_shots} 个镜头，约 {dur:.0f} 秒{hi_s}")
    print(f"  错误 {len(E)} · 警告 {len(W)}")
    for where, msg in E:
        print(f"  [错误] {where}  {msg}")
    for where, msg in W:
        print(f"  [警告] {where}  {msg}")
    return len(E)


def main():
    ap = argparse.ArgumentParser(description="和夜一起住 · 剧本检查")
    ap.add_argument("paths", nargs="*", help="剧本.md；不给就查所有 ep*/剧本.md")
    ap.add_argument("--json", action="store_true", help="输出解析结果，不做检查")
    a = ap.parse_args()
    paths = a.paths or sorted(glob.glob(os.path.join(ROOT, "ep*", "剧本.md")))
    if a.json:
        out = []
        for p in paths:
            ep = parse(p)
            d = asdict(ep)
            d.pop("problems")
            out.append(d)
        print(json.dumps(out if len(out) > 1 else out[0], ensure_ascii=False, indent=2))
        return 0
    errors = 0
    for p in paths:
        ep = parse(p)
        if not ep.pages or "本集" not in open(p, encoding="utf-8").read():
            print(f"{os.path.relpath(p, ROOT)}  不是 准则/剧本模板.md 的格式，跳过")
            continue
        errors += report(ep)
        print()
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
