# 和夜一起住

小红书（秋浓）原创漫画 / 动画系列：独居女孩和一只会变大变小、上夜班的黑猫「夜」合租。画风 C 黑白点金。

- `style/`：画风测试，定稿参考图 `v3_C黑白点金.png`
- `ep01/`：第 1 期《我的新室友，是一只上夜班的猫》
  - `gen.py` 插画 + 图文排版；`h3.py` 4090 上 MiniMax H3 图生视频；`layers.py` 分层动效（眨眼、呼吸、光）；`video.py` 合成成片
  - `publish*.mjs` / `finish_video.mjs`：ego-browser 发小红书
- `ep02/`：第 2 期（构思中，`剧本.md` 的方向 B 已被否）

依赖仓库外的东西：`../../clip10/assets.py`（gpt-image 出图）、`../../music.py`、`../../../ucl-video/`（venv 与 museum/h3.py）。
成片 mp4、配音、音乐、中间检查图不进仓库（见 `.gitignore`）。
