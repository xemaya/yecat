"""第 2 期视频的 H3 镜头（4090 上的 MiniMax H3，排队方式同 ../ep01/h3.py：只往空着的实例里插）。

  ../../../ucl-video/.venv/bin/python h3.py [镜头 ...]     出 h3/<镜头>_s<种子>.mp4，已有的跳过

  5b   取星：首帧她的手伸进发光的灯罩（art/5b_first），尾帧星托在掌心、灯罩黑了（art/5b）
"""
import os
import subprocess
import sys
import time

import importlib.util

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# 第 1 期的 h3.py：MEDIUM / ENDING 提示词、M（museum/h3.py）、remote。和本文件同名，只能按路径载入
_spec = importlib.util.spec_from_file_location("ep01_h3", os.path.join(HERE, "..", "ep01", "h3.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
M, remote = E.M, E.remote

OUT = os.path.join(HERE, "h3")
SUB, WORK = "yecat02", f"{remote.ROOT}/h3_yecat02"
SEEDS = [int(s) for s in os.environ.get("H3_SEEDS", "42,7").split(",")]
# 第 1 期的 MEDIUM 写了黑猫，没有猫的镜头会凭空画出一只猫来：换成不提猫、只有一颗星的版本
ONE_STAR = ("A black-and-white manga illustration: clean black ink line art and screentone on white paper. "
            "The only colour is soft gold, used only for one small glowing star and the light it gives. "
            "The young woman has short black bob hair and a white shirt. There is no cat and no animal anywhere in this scene, "
            "and there is only that one star, no other stars or sparkles. Everything stays black-and-white ink manga line art. ")
MEDIUM = {"5b": ONE_STAR}
SHOTS = {
    "5b": (os.path.join(HERE, "art", "5b_first.png"), os.path.join(HERE, "art", "5b.png"),
           "At night on top of the wooden ladder, the young woman reaches into the open round metal lamp shade and gently lifts out "
           "the small glowing gold star; as the star leaves, the inside of the lamp shade goes dark; she brings the star down and holds it "
           "in her open palm, where it flickers softly, brighter and dimmer, like a breathing candle. The lamp post, the tree and the building stay still."),
}


def jobs(keys):
    js = []
    for k in keys:
        for seed in SEEDS:
            if not os.path.exists(os.path.join(OUT, f"{k}_s{seed}.mp4")):
                w, h = (1248, 832) if Image.open(SHOTS[k][0]).width > Image.open(SHOTS[k][0]).height else (832, 1248)
                js.append(dict(k=k, seed=seed, tag=f"yecat02_{k}_s{seed}", w=w, h=h, tries=0))
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
