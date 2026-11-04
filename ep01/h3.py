"""和夜一起住 · 第 1 期视频版的动态镜头：每张插画用 4090 上的 MiniMax H3（用户的 ComfyUI + h3run.py）图生视频。

  ../../../ucl-video/.venv/bin/python h3.py [镜头 ...]     不写就全做；已有 h3/<镜头>.mp4 的跳过
排队、上传、取回都借 ucl-video/museum/h3.py：只往没有排队任务的实例里插，每个实例同时最多一条我们的任务。
首尾帧都钉成原图（守住黑白点金的画风），成片去掉 H3 自带的音轨存到 h3/<镜头>.mp4。
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MUSEUM = os.path.join(HERE, "..", "..", "..", "ucl-video", "museum")
sys.path.insert(0, os.path.dirname(MUSEUM))
sys.path.insert(0, MUSEUM)
import h3 as M  # noqa: E402
import remote  # noqa: E402
import imageio_ffmpeg  # noqa: E402

ART = os.path.join(HERE, "art_C")
OUT = os.path.join(HERE, "h3")
SUB, WORK = "yecat01", f"{remote.ROOT}/h3_yecat01"
SEC = float(os.environ.get("H3_SEC", 6.0))
LAST = {"7b": "8"}  # 首尾不同的镜头：变身，从 7b 的小猫长成 8 的大猫
SUFFIX = os.environ.get("H3_SUFFIX", "")
SIZE = {"land": (1248, 832), "port": (832, 1248)}  # 插画是 2:3，宽高都取 32 的倍数

MEDIUM = ("A black-and-white manga illustration: clean black ink line art and screentone on white paper. "
          "The only colour is soft gold: the black cat's golden eyes, the gold crescent mark on its forehead, tiny gold stars and warm lamp or sun light. "
          "The young woman has short black bob hair and a white shirt; the cat is solid black. Everything stays black-and-white ink manga line art. ")
ENDING = (" The whole shot keeps exactly the look, line art, proportions and colours of the first frame. Gentle small natural motion only, "
          "faces stay the same, no new objects, no text. One single continuous take with a locked static camera showing the whole picture "
          "the entire time: no cuts, no close-ups, no zoom, no fade to black.")
MOTION = {
    "1": "The big black cat slowly blinks its golden eyes and its tail curls a little; the woman leaning on it breathes softly and her hair sways in a light breeze; the tiny gold stars in its fur twinkle.",
    "2": "The black cat on the chair lifts one paw and taps the table, its tail sways; the woman reading the paper looks at the cat and laughs softly; steam rises gently from the cup.",
    "3": "The open fridge is still; the tiny gold stars inside the glass jar slowly drift and twinkle; a faint cold mist curls out of the fridge.",
    "4": "The woman at the door turns her head and looks down at the black cat with a small smile; the cat looks up, blinks and slowly swishes its tail; her hair moves slightly.",
    "5a": "Rain falls steadily; the woman walks slowly forward under the glowing streetlight; raindrops splash on the wet pavement; the leaves tremble in the rain.",
    "5b": "Warm steam rises from the bottle of milk in her hand; the woman reads the small note, smiles and blinks slowly.",
    "6": "The tiny black cat curled in her palms breathes slowly and its ears twitch once; the woman looks down at it tenderly and her hair sways a little; the leaves of the plant move in a breeze.",
    "7": "The woman sitting on the bench tilts her face up to the sun with closed eyes and smiles; steam curls from her cup; the tiny cat in her shirt pocket blinks; leaves sway softly overhead.",
    "7b": ("At sunset on the balcony the small black cat beside the sitting woman stretches, then slowly and magically grows bigger and bigger, "
           "its black fur swelling softly like a cloud with tiny gold stars sparkling around it, until it is a huge fluffy cat sitting behind her "
           "and wrapping its big tail around her; she looks up and smiles."),
    "8": "The huge black cat behind her slowly turns its head toward the woman and blinks; its fur ruffles in the evening breeze; the woman smiles with closed eyes and steam rises from her cup; the sun sinks a little over the city.",
    "9": "The black cat and the woman at the window look at each other; the cat blinks slowly and the woman smiles; the lamp sways very slightly and the curtains move in a soft breeze.",
}


def jobs(keys):
    from PIL import Image
    js = []
    for k in keys:
        if os.path.exists(os.path.join(OUT, f"{k}{SUFFIX}.mp4")):
            continue
        im = Image.open(os.path.join(ART, f"{k}.png"))
        w, h = SIZE["land" if im.width > im.height else "port"]
        js.append(dict(k=k, tag=f"yecat01_{k}{SUFFIX}", w=w, h=h, prompt=MEDIUM + MOTION[k] + ENDING, tries=0))
    return js


def upload(js):
    M.sh(f"mkdir -p {M.COMFY_IN}/{SUB} {WORK}")
    tmp = os.path.join(OUT, "_prompts")
    os.makedirs(tmp, exist_ok=True)
    for j in js:
        open(os.path.join(tmp, j["tag"] + ".txt"), "w").write(j["prompt"])
        for k in {j["k"], LAST.get(j["k"], j["k"])}:
            remote._retry(["scp", "-q"] + remote.OPTS + [os.path.join(ART, f"{k}.png"), f"{remote.HOST}:{M.COMFY_IN}/{SUB}/{k}.png"], check=True)
    remote._retry(["scp", "-q", "-r"] + remote.OPTS + [tmp + "/.", f"{remote.HOST}:{WORK}/"], check=True)


def launch(j, port):
    j["tries"] += 1
    j["port"] = port
    img = f"{SUB}/{j['k']}.png"
    last = f"--last {img} " if os.environ.get("H3_LAST", "0") == "1" else ""  # 首尾都钉住时 H3 中段会发灰、冒出新东西，默认只钉首帧
    if j["k"] in LAST:
        last = f"--last {SUB}/{LAST[j['k']]}.png "
    args = (f"--port {port} --first {img} {last}--w {j['w']} --h {j['h']} --sec {SEC} --steps 8 --lora {M.LORA} "
            f"--seed {int(os.environ.get('H3_SEED', 42)) + j['tries']} --prompt-file {WORK}/{j['tag']}.txt --prefix {SUB}/{j['tag']}")
    M.sh(f"(cd /home/huanghaibin/bin; setsid nohup {M.PY} -u {M.H3RUN} {args} > {WORK}/{j['tag']}.log 2>&1 < /dev/null &)")
    print(f"launch {j['k']} on {port} (try {j['tries']})", flush=True)


def status(j):
    log = M.sh(f"cat {WORK}/{j['tag']}.log 2>/dev/null")
    for line in log.splitlines():
        if line.startswith("DONE"):
            return "done", line[line.index("["):].strip("[]' ").split("'")[0]
    if "Traceback" in log or "status_str" in log or "Error" in log:
        return "fail", log[-800:]
    return "run", None


def fetch(j, rel):
    raw = os.path.join(OUT, f"_raw_{j['k']}.mp4")
    remote._retry(["scp", "-q"] + remote.OPTS + [f"{remote.HOST}:{M.COMFY_OUT}/{rel}", raw], check=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", raw, "-an", "-c:v", "copy",
                    os.path.join(OUT, f"{j['k']}{SUFFIX}.mp4")], check=True)
    os.remove(raw)
    print(f"done {j['k']}", flush=True)


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
                print(f"fail {j['k']}: {info}", flush=True)
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
    run(sys.argv[1:] or list(MOTION))
