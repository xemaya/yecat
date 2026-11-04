"""和夜一起住：角色设定 v2（更干净、女孩更修长）。用法：../../../ucl-video/.venv/bin/python v2.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ep01"))
import gen as G  # noqa: E402

out = os.path.join(HERE, "设定v2.png")
prompt = (f"{G.STYLE.replace('和参考图的画风、人物、黑猫完全一致', '参考图只用来参考黑猫的样子和暖色调')}。"
          "角色设定图（character sheet）构图，背景是干净的浅暖色纯色纸面，只有脚下一点淡淡的影子。"
          f"{G.GIRL.replace('就是参考图里的女孩，', '')}。{G.CAT.replace('就是参考图里的黑猫，', '')}，体型修长优雅。"
          "画面左半边：女孩全身站立、一只手插兜，普通家猫大小的夜蹲坐在她肩膀上，尾巴绕过她的脖子；"
          "画面右半边：同一个女孩和同一只夜，但夜变得巨大（趴下时比女孩还高），女孩放松地坐着靠在夜身上，夜低头用下巴轻轻护着她。"
          "两组人物都完整、不要裁切，比例真实修长，不要 Q 版、不要大头。竖版构图，上方 12% 留白。"
          "画面里不要任何文字、字母、数字、logo。每个人一共只有两只手。")
G.base.edit(prompt, [os.path.join(HERE, "1暖光厚涂.png")], out, size="1024x1536")
