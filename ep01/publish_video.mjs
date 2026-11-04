// 和夜一起住 01 视频版发小红书第一段：上传 和夜一起住01_v4.mp4、填标题正文话题。用法：cat publish_video.mjs | ego-browser nodejs
// 读 视频正文.txt：【标题】一行、正文、#话题一行；【合集】【发完后…】行不发。
const fs = await import("node:fs/promises");
const DIR = `/Users/huanghaibin/Workspace/neuro-workers/yecat/ep01/`;
const SHOT = `/private/tmp/claude-501/-Users-huanghaibin-Workspace/3228c31a-6aee-401c-8ceb-2b731017509b/scratchpad/yecat01v`;
const raw = (await fs.readFile(DIR + "视频正文.txt", "utf8")).split("\n");
const title = raw.find((l) => l.startsWith("【标题】")).slice(4);
const tagLine = raw.find((l) => l.startsWith("#"));
const tags = tagLine.split(/\s+/).filter(Boolean).map((t) => t.slice(1));
const body = raw.filter((l) => !l.startsWith("【") && l !== tagLine);
while (body[0] === "") body.shift();
while (body.at(-1) === "") body.pop();

const task = await taskSpace("publish quiz04");
const page = task.page("p1");
try { await page.goto("https://creator.xiaohongshu.com/publish/publish?source=official", { timeout: 20000 }); } catch (e) {}
await page.waitForFunction(() => [...document.querySelectorAll("span,div")].some((e) => e.children.length === 0 && e.textContent.trim() === "上传视频"), undefined, { timeout: 30000 });
await page.evaluate(() => [...document.querySelectorAll("span,div")].filter((e) => e.children.length === 0 && e.textContent.trim() === "上传视频").forEach((e) => e.click()));
await page.waitForTimeout(1500);
await page.setInputFiles("input.upload-input", [`${DIR}和夜一起住01_v4.mp4`]);
await page.waitForSelector("input[placeholder*='标题']", { state: "visible", timeout: 120000 });
// 等视频传完（页面出现“上传成功”或“重新上传”）
await page.waitForFunction(() => /上传成功|重新上传|替换视频/.test(document.body.innerText), undefined, { timeout: 300000 });
await page.waitForTimeout(3000);
await page.fill("input[placeholder*='标题']", title);

// 正文：tiptap 编辑器，粘 HTML 段落
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
await page.click(".tiptap.ProseMirror", { label: "focus note body" });
await page.keyboard.paste({ text: body.join("\n"), html: body.map((p) => `<p>${p ? esc(p) : "<br>"}</p>`).join("") });
await page.waitForTimeout(800);

// 话题：每次把光标放到末尾，打 #词，用真实鼠标点弹层里的同名项
const toEnd = () => page.evaluate(() => { const el = document.querySelector(".tiptap.ProseMirror"); el.focus(); const r = document.createRange(); r.selectNodeContents(el.lastElementChild); r.collapse(false); const s = getSelection(); s.removeAllRanges(); s.addRange(r); });
await toEnd();
await page.keyboard.press("Enter");
for (const t of tags) {
  await toEnd();
  await page.keyboard.type("#" + t);
  let box = null;
  for (let k = 0; k < 20 && !box; k++) {
    await page.waitForTimeout(600);
    box = await page.evaluate((t) => {
      const el = [...document.querySelectorAll("[id^='tippy-'] .item, [id^='tippy-'] li")].filter((e) => e.offsetParent).find((e) => e.innerText.trim().split("\n")[0].replace(/^#/, "") === t);
      if (!el) return null; el.scrollIntoView({ block: "nearest" }); const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    }, t);
  }
  if (box) await page.mouse.click(box.x, box.y, { label: "pick topic " + t });
  else await page.keyboard.type(" ");
  await page.waitForTimeout(800);
}
const topics = await page.evaluate(() => [...document.querySelectorAll(".tiptap.ProseMirror a.tiptap-topic")].map((a) => JSON.parse(a.dataset.topic).name));
console.log({ title, tags, topics });

await page.screenshot({ path: SHOT + "_filled.png", fullPage: true });
