"""第 1 期重做视频的 H3 镜头（4090 上的 MiniMax H3，排队方式同 ../ep01/h3.py：只往空着的实例里插）。

  ../../../ucl-video/.venv/bin/python h3.py [镜头 ...]     出 h3/<镜头>_s<种子>.mp4，已有的跳过

  n2   人字梯：台灯轻轻晃、关一下再开，天花板的光斑跟着动（只钉首帧）
  n3   放灯泡：首帧脚跟着地、盒子关着（var/n3_first），尾帧踮脚开盒（art/3）
  7    晒太阳：首帧口袋里只露耳朵（var/7_first），尾帧小猫探出头眯眼（第 1 期原图）
"""
import os
import subprocess
import sys
import time

import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
# 第 1 期的 h3.py：MEDIUM / ENDING 提示词、M（museum/h3.py）、remote。和本文件同名，只能按路径载入
_spec = importlib.util.spec_from_file_location("ep01_h3", os.path.join(HERE, "..", "ep01", "h3.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
M, remote = E.M, E.remote

OUT = os.path.join(HERE, "h3")
SUB, WORK = "yecat01r", f"{remote.ROOT}/h3_yecat01r"
SEEDS = [int(s) for s in os.environ.get("H3_SEEDS", "42,7").split(",")]
# 第 1 期的 MEDIUM 写了黑猫，没有猫的镜头会凭空画出一只猫来：这两个镜头她还没遇见夜，换成不提猫的版本
NO_CAT = ("A black-and-white manga illustration: clean black ink line art and screentone on white paper. "
          "The only colour is soft gold, used only for the warm lamp light and the old light bulbs. "
          "The young woman has short black bob hair and a white shirt. There is no cat and no animal anywhere in this scene, "
          "and no stars or sparkles. Everything stays black-and-white ink manga line art. ")
MEDIUM = {"n2": NO_CAT, "n3": NO_CAT}
SHOTS = {
    "n2": (os.path.join(HERE, "art", "2.png"), None,
           "In the dark empty shop the young woman sitting on the ladder gently tilts and sways the small glowing lamp in her hands; "
           "the warm lamp light sways and the bright spot of light on the dark ceiling slides back and forth with it; "
           "once she clicks the lamp off so the room goes almost dark, then clicks it on again and the warm light returns."),
    "n3": (os.path.join(HERE, "var", "n3_first.png"), os.path.join(HERE, "art", "3.png"),
           "The young woman lifts the closed old shoebox onto the top of the wardrobe, rises up onto her tiptoes and opens the lid; "
           "inside are a few old light bulbs glowing faintly gold; she looks down at them calmly."),
    "7": (os.path.join(HERE, "var", "7_first.png"), os.path.join(HERE, "..", "ep01", "art_C", "7.png"),
          "On the park bench in the warm sun, a tiny black kitten slowly pokes its head out of the woman's shirt pocket, looks around, "
          "then narrows its eyes happily in the sunlight; steam curls from her cup; the leaves sway; her face stays tilted to the sun with closed eyes."),
}


def jobs(keys):
    js = []
    for k in keys:
        for seed in SEEDS:
            if not os.path.exists(os.path.join(OUT, f"{k}_s{seed}.mp4")):
                js.append(dict(k=k, seed=seed, tag=f"yecat01r_{k}_s{seed}", w=832, h=1248, tries=0))
    return js


def upload(js):
    M.sh(f"mkdir -p {M.COMFY_IN}/{SUB} {WORK}")
    tmp = os.path.join(OUT, "_prompts")
    os.makedirs(tmp, exist_ok=True)
    for j in js:
        first, last, motion = SHOTS[j["k"]]
        open(os.path.join(tmp, j["tag"] + ".txt"), "w").write(MEDIUM.get(j["k"], E.MEDIUM) + motion + E.ENDING)
        for role, src in (("first", first), ("last", last)):
            if src:
                remote._retry(["scp", "-q"] + remote.OPTS + [src, f"{remote.HOST}:{M.COMFY_IN}/{SUB}/{j['k']}_{role}.png"], check=True)
    remote._retry(["scp", "-q", "-r"] + remote.OPTS + [tmp + "/.", f"{remote.HOST}:{WORK}/"], check=True)


def launch(j, port):
    j["tries"] += 1
    j["port"] = port
    last = f"--last {SUB}/{j['k']}_last.png " if SHOTS[j["k"]][1] else ""
    args = (f"--port {port} --first {SUB}/{j['k']}_first.png {last}--w {j['w']} --h {j['h']} --sec 6 --steps 8 --lora {M.LORA} "
            f"--seed {j['seed'] + j['tries'] - 1} --prompt-file {WORK}/{j['tag']}.txt --prefix {SUB}/{j['tag']}")
    M.sh(f"(cd /home/huanghaibin/bin; setsid nohup {M.PY} -u {M.H3RUN} {args} > {WORK}/{j['tag']}.log 2>&1 < /dev/null &)")
    print(f"launch {j['tag']} on {port} (try {j['tries']})", flush=True)


def status(j):
    log = M.sh(f"cat {WORK}/{j['tag']}.log 2>/dev/null")
    for line in log.splitlines():
        if line.startswith("DONE"):
            return "done", line[line.index("["):].strip("[]' ").split("'")[0]
    if "Traceback" in log or "status_str" in log or "Error" in log:
        return "fail", log[-800:]
    return "run", None


def fetch(j, rel):
    raw = os.path.join(OUT, f"_raw_{j['tag']}.mp4")
    remote._retry(["scp", "-q"] + remote.OPTS + [f"{remote.HOST}:{M.COMFY_OUT}/{rel}", raw], check=True)
    subprocess.run([E.imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", raw, "-an", "-c:v", "copy",
                    os.path.join(OUT, f"{j['k']}_s{j['seed']}.mp4")], check=True)
    os.remove(raw)
    print(f"done {j['tag']}", flush=True)


def run(keys):
    todo = jobs(keys)
    if not todo:
        return
    upload(todo)
    flying = []
    while todo or flying:
        for j in list(flying):
            st, info = status(j)
            if st == "done":
                fetch(j, info)
                flying.remove(j)
            elif st == "fail":
                print(f"fail {j['tag']}: {info}", flush=True)
                flying.remove(j)
                if j["tries"] < 3:
                    todo.append(j)
        busy = {j["port"] for j in flying}
        for port, (running, pending) in sorted(M.queues().items(), key=lambda kv: kv[1]):
            if todo and port not in busy and running == 0 and pending == 0:
                j = todo.pop(0)
                launch(j, port)
                flying.append(j)
                busy.add(port)
        time.sleep(30)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    run(sys.argv[1:] or list(SHOTS))
