// 和夜一起住 01 视频版发小红书第二段：选合集「和夜一起住」、检查没误关联活动，再发布。用法：cat finish.mjs | ego-browser nodejs
const SHOT = `/private/tmp/claude-501/-Users-huanghaibin-Workspace/3228c31a-6aee-401c-8ceb-2b731017509b/scratchpad/yecat01v`;
const task = await taskSpace("publish quiz04");
const page = task.page("p1");

// 合集：点“选择合集”，选「和夜一起住」
const leaf = (s) => page.evaluate((s) => { const own = (e) => [...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim(); const e = [...document.querySelectorAll("*")].filter((e) => own(e) === s && e.offsetParent).at(-1); if (!e) return null; e.scrollIntoView({ block: "center" }); return true; }, s);
const rect = (s) => page.evaluate((s) => { const own = (e) => [...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim(); const e = [...document.querySelectorAll("*")].filter((e) => own(e) === s && e.offsetParent).at(-1); if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }, s);
await leaf("选择合集");
await page.waitForTimeout(500);
let b = await rect("选择合集");
await page.mouse.click(b.x, b.y, { label: "open collection picker" });
await page.waitForTimeout(1200);
b = await rect("和夜一起住");
await page.mouse.click(b.x, b.y, { label: "pick collection" });
await page.waitForTimeout(1000);
const col = await page.evaluate(() => { let c = [...document.querySelectorAll("*")].find((e) => e.children.length === 0 && e.textContent.trim() === "加入合集"); for (let i = 0; i < 3; i++) c = c.parentElement; return c.innerText; });
const linked = await page.evaluate(() => [...document.querySelectorAll("*")].some((e) => e.children.length === 0 && e.textContent.trim() === "取消关联"));
console.log({ collection: col.includes("和夜一起住"), activityLinked: linked });
if (!col.includes("和夜一起住") || linked) {
  await page.screenshot({ path: SHOT + "_stop.png" });
  throw new Error("合集没选上或误关联了活动，停下检查");
}
await page.screenshot({ path: SHOT + "_before.png" });

// 发布：底部固定栏的红色按钮
await page.mouse.click(796, 789, { label: "publish note" });
await page.waitForURL(/publish\/success/, { timeout: 30000 });
console.log("published", await page.url());
