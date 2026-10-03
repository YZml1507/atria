// 安镇实验展厅 — 等距小镇 + 时间轴回放
const $ = s => document.querySelector(s);
const cv = $("#cv"), ctx = cv.getContext("2d");
const TILE = "assets/tiles/", TS = 0.5;          // 瓦片缩放
const TW = 230 * TS, TH = 115 * TS;              // 单元格屏幕宽高
const AX = 128 * TS, AY = 186 * TS;              // 精灵内顶面中心锚点
const STOREY = 104 * TS;                          // 一层高度(屋顶抬升)

const OX = 2200, OY = 260;                        // iso 原点偏移(镇中心靠画布中)
let D = null, run = "v2", R = null;               // data, 当前 run
let T = 0, playing = false, speed = 8;            // 时间 t = day*48+step (float, 从 step0 起)
let cam = { x: 0, y: 0, z: 1 }, sel = -1, camInit = false, camTarget = null, follow = -1;
let evIdx = [], pos = [], sayUntil = [], walking = [];

const HUES = [210, 20, 150, 260, 40, 185, 330, 75, 285, 100, 175, 250, 15, 200, 130,
              300, 55, 225, 160, 90, 270, 45, 195, 120, 340];
const PAL = HUES.map(h => `hsl(${h},60%,62%)`);

// ---------- 建筑外观指派 ----------
const STYLE = {
  "邮局":      { roof: "roof_gableBrown",  wall: "building_doorBeige", tall: 2, sign: "邮" },
  "五金店":    { roof: "roof_slantBeige",  wall: "building_windows",   tall: 1, sign: "五金" },
  "杂货铺":    { roof: "roof_roundGreen",  wall: "building_windowsBeige", tall: 1, sign: "杂货" },
  "诊所":      { roof: "roof_pointBeige",  wall: "building_door",      tall: 2, sign: "十" },
  "镇学校":    { roof: "roof_churchBrown", wall: "building_doorWindows", tall: 1, sign: "学" },
  "镇公园":    { roof: null,               wall: null,                 tall: 0, sign: "" },
  "老磨坊酒吧": { roof: "roof_roundedBrown", wall: "building_doorWindowsBeige", tall: 1, sign: "酒" },
};
const HOME_ROOFS = ["roof_gableBeige", "roof_gableBrown", "roof_pointBeige", "roof_roundedBeige"];
const HOME_WALLS = ["building_window", "building_door", "building_windows"];

const tiles = {};
function loadTiles() {
  const need = new Set(["grass_center_S", "dirt_center_S", "grass_pathCrossing_S",
    "tree_single_S", "tree_multiple_S", "rocks_grass_S", "grass_path_S", "grass_path_E",
    "grass_pathCorner_S", "grass_pathCorner_E", "bridge_S"]);
  Object.values(STYLE).forEach(s => {
    if (s.roof) need.add(s.roof + "_S");
    if (s.wall) need.add(s.wall + "_S");
  });
  HOME_ROOFS.concat(HOME_WALLS).forEach(n => need.add(n + "_S"));
  // building_edge 变体用于侧面
  ["building_center", "building_window", "building_windows", "building_door",
   "building_centerBeige", "building_windowBeige", "building_windowsBeige", "building_doorBeige"]
    .forEach(n => ["_E", "_N"].forEach(d => need.add(n + d)));
  return Promise.all([...need].map(n => new Promise(res => {
    const im = new Image(); im.onload = () => { tiles[n] = im; res(); };
    im.onerror = () => { console.warn("missing", n); res(); }; im.src = TILE + n + ".png";
  })));
}

// ---------- 地图单元格 ----------
let cells = [];   // [x,y] -> {type, place, name}
function buildMap() {
  cells = [];
  const set = (b, t, name) => { for (let x = b[0]; x <= b[2]; x++) for (let y = b[1]; y <= b[3]; y++)
    cells[y * D.grid[0] + x] = { type: t, place: name }; };
  D.roads.forEach(r => set(r.box, "road", r.name));
  D.homes.forEach(h => set(h.box, "home", h.name));
  D.places.forEach(p => set(p.box, "place", p.name));
  cells.placeOf = (x, y) => (cells[Math.round(y) * D.grid[0] + Math.round(x)] || {}).place;
}

// 建筑墙/顶样式: 每个 place 一个 hash
function hash(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return Math.abs(h); }

// ---------- iso 投影 ----------
function iso(x, y, z = 0) { return [ OX + (x - y) * TW / 2, OY + (x + y) * TH / 2 - z * STOREY ]; }
function drawTile(name, sx, sy, g) {
  const im = tiles[name]; if (!im) return;
  (g || ctx).drawImage(im, sx - AX, sy - AY, im.width * TS, im.height * TS);
}

// ---------- 静态地图缓存 ----------
const mapCv = document.createElement("canvas");
function renderMap() {
  const [GW, GH] = D.grid;
  mapCv.width = OX * 2 + 400; mapCv.height = (GW + GH) * TH / 2 + OY + 420;
  const g = mapCv.getContext("2d");

  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    const c = cells[y * GW + x] || { type: "grass" };
    const [sx, sy] = iso(x + .5, y + .5);
    if (c.type === "road") {
      const n = (dx, dy) => (cells[(y + dy) * GW + x + dx] || {}).type === "road";
      const ew = n(-1,0) || n(1,0), ns = n(0,-1) || n(0,1);
      drawTile((ew && ns) ? "grass_pathCrossing_S" : ns && !ew ? "grass_path_E" : "grass_path_S", sx, sy, g);
    } else drawTile("grass_center_S", sx, sy, g);
    if (!c.type && (hash(x + "," + y) % 23 === 0)) drawTile("tree_single_S", sx, sy - STOREY * 0.55, g);
  }
  // 建筑: 每 place 一个块, 逐 cell 画墙+顶
  const drawB = (name, box, style, key) => {
    const [x0, y0, x1, y1] = box;
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
      const [sx, sy] = iso(x + .5, y + .5);
      const front = (y === y1) || (x === x1);           // 可见的两面
      let wallN;
      if (style.wall) {
        wallN = front ? style.wall + "_S" : "building_center_S";
        // 门面: 每栋正面中间放一个 door
        const midX = Math.round((x0 + x1) / 2);
        if (y === y1 && x === midX && style.sign) wallN = "building_door_S";
        drawTile(wallN, sx, sy, g);
        for (let z = 1; z < style.tall; z++) drawTile("building_window_S", sx, sy - z * STOREY, g);
        // 屋顶只铺可见边缘(前/右), 内部留平顶 — 剪影更干净
        if (style.roof && front) drawTile(style.roof + "_S", sx, sy - style.tall * STOREY, g);
      }
    }
  };
  D.homes.forEach((h, i) => drawB(h.name, h.box,
    { roof: HOME_ROOFS[hash(h.name) % HOME_ROOFS.length],
      wall: HOME_WALLS[hash(h.name) % HOME_WALLS.length], tall: 1, sign: "" }));
  D.places.forEach(p => {
    const st = STYLE[p.name] || { roof: HOME_ROOFS[hash(p.name) % 4], wall: "building_windows", tall: 1, sign: p.name.slice(0, 2) };
    if (p.name === "镇公园") return drawPark(p.box, g);
    drawB(p.name, p.box, st);
  });
  // 地名标注: 贴在建筑正面上方
  g.font = "600 15px 'Noto Sans SC'"; g.textAlign = "center";
  D.places.forEach(p => {
    if (p.name === "镇公园") {
      const [sx, sy] = iso((p.box[0] + p.box[2]) / 2 + .5, p.box[3] + .5);
      label(g, p.name, sx, sy + 4); return;
    }
    const st = STYLE[p.name] || { tall: 1 };
    const [sx, sy] = iso((p.box[0] + p.box[2]) / 2 + .5, p.box[3] + .5);
    label(g, p.name, sx, sy - (st.tall + 1) * STOREY - 4);
  });
  D.homes.slice(0, 5).forEach(() => {});
}
function label(g, txt, sx, sy) {
  const w = g.measureText(txt).width + 14;
  g.fillStyle = "rgba(18,22,30,.82)";
  g.beginPath(); g.roundRect(sx - w / 2, sy - 10, w, 17, 4); g.fill();
  g.fillStyle = "#e8ecf2"; g.fillText(txt, sx, sy + 2);
}
function drawPark(box, g) {
  const [x0, y0, x1, y1] = box;
  for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
    const [sx, sy] = iso(x + .5, y + .5);
    if ((x + y) % 5 === 0) drawTile("tree_multiple_S", sx, sy - STOREY * .3, g);
  }
}

// ---------- agent 状态推进 ----------
function setupRun(rid) {
  run = rid; R = D.runs[rid]; T = 0; sel = -1;
  // 事件按 (day,step) 排序; t = (day-1)*48 + step
  evIdx = R.events;
  pos = D.agents.map(a => (cellOfHome(a.home) || a.cell).slice());
  sayUntil = D.agents.map(() => null); walking = D.agents.map(() => null);
  evPtr = 0;
  applyEvents(0);
  document.querySelectorAll(".tab").forEach(el => el.classList.toggle("on", el.dataset.r === rid));
  $("#panel").innerHTML = "<h2>点一个居民看记忆</h2><div class='role'>移动中角色头顶气泡是 run 里的真实台词</div>";
}
let evPtr = 0;
const tOf = e => (e[0] - 1) * 48 + e[1];
function applyEvents(t) {
  // 单调推进; 倒退(拖回去)时重置
  if (t < lastT) { pos = D.agents.map(a => (cellOfHome(a.home) || a.cell).slice()); walking = pos.map(() => null);
    sayUntil = pos.map(() => null); evPtr = 0; }
  while (evPtr < evIdx.length && tOf(evIdx[evPtr]) <= t) {
    const e = evIdx[evPtr]; const ai = e[2];
    if (ai >= 0) {
      const to = cellOfPlace(e[3]);
      walking[ai] = { from: pos[ai].slice(), to, t0: tOf(e), dur: 1.6 };
      pos[ai] = to.slice();
      if (e[4]) sayUntil[ai] = { txt: e[4], until: tOf(e) + 3.2 };
    }
    evPtr++;
  }
  lastT = t;
}
let lastT = 0;
const pList = () => D.places.concat(D.homes).concat([{ name: "__road", box: null }]);
function cellOfPlace(pi) {
  const all = pList();
  const p = all[pi];
  if (p && p.box) return [(p.box[0] + p.box[2]) / 2 + .5, p.box[3] + .7];  // 站门前街边
  return [20, 9];
}
function cellOfHome(name) {
  const b = (D.homes.find(h => h.name === name) || D.places.find(p => p.name === name));
  if (!b) return null;
  return [(b.box[0] + b.box[2]) / 2 + .5, b.box[3] + .7];
}

// ---------- 渲染 ----------
function render() {
  const W = cv.width = innerWidth, H = cv.height = innerHeight;
  ctx.clearRect(0, 0, W, H);
  // 底纹
  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, "#0d1017"); bg.addColorStop(1, "#12161f");
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  if (!camInit) { cam.z = 0.5; const [cx, cy] = iso(D.grid[0] / 2 + 1, D.grid[1] / 2 - 1);
    cam.x = (W - 316) / 2 - cx * cam.z; cam.y = H * .5 - cy * cam.z; camInit = true; }
  ctx.save();
  ctx.translate(cam.x, cam.y); ctx.scale(cam.z, cam.z);
  ctx.drawImage(mapCv, 0, 0);

  // agents: 屏幕空间恒定大小绘制, 保证可读
  const order = D.agents.map((a, i) => {
    const p = interpPos(i);
    return { i, x: p[0], y: p[1] };
  }).sort((a, b) => (a.x + a.y) - (b.x + b.y));
  const day = Math.floor(T / 48) + 1;
  let know = 0;
  ctx.restore();
  for (const a of order) {
    const ag = D.agents[a.i];
    const [ix, iy] = iso(a.x, a.y);
    const sx = ix * cam.z + cam.x, sy = iy * cam.z + cam.y;
    const inf = (R.informed[a.i] || 999) <= day;
    if (inf) know++;
    drawAgent(sx, sy, ag, a.i, inf);
  }
  for (const a of order) {
    const ag = D.agents[a.i];
    const [ix, iy] = iso(a.x, a.y);
    drawNameBubble(ix * cam.z + cam.x, iy * cam.z + cam.y, ag, a.i);
  }
  const dayCur = Math.min(Math.floor(T / 48) + 1, R.days);
  const stepCur = Math.floor(T % 48);
  $("#daylab").textContent = `第 ${dayCur} 天 · ${String(Math.floor(stepCur / 2)).padStart(2, "0")}:${stepCur % 2 ? "30" : "00"}`;
  $("#knowN").innerHTML = `${know}<span style="font-size:13px;color:#8b93a3">/25</span>`;
  drawSpark(dayCur);
  $("#slider").value = Math.round(T / (R.days * 48 - 1) * 1000);
}

function interpPos(i) {
  const w = walking[i];
  if (!w) return pos[i];
  const k = Math.min(1, (T - w.t0) / w.dur);
  if (k >= 1) { walking[i] = null; return pos[i]; }
  const e = k * k * (3 - 2 * k);
  return [w.from[0] + (w.to[0] - w.from[0]) * e, w.from[1] + (w.to[1] - w.from[1]) * e];
}

function drawAgent(sx, sy, ag, i, inf) {
  const bob = walking[i] ? Math.sin(T * 9 + i) * 1.5 : 0;
  const y0 = sy + 14;
  // 影子
  ctx.fillStyle = "rgba(0,0,0,.28)"; ctx.beginPath();
  ctx.ellipse(sx, y0 + 2, 8, 3.2, 0, 0, 7); ctx.fill();
  // 身体
  ctx.fillStyle = sel === i ? "#ffd166" : PAL[i];
  ctx.strokeStyle = "rgba(0,0,0,.5)"; ctx.lineWidth = 1;
  rr(sx - 5, y0 - 17 + bob, 10, 15, 4); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.arc(sx, y0 - 21 + bob, 4.6, 0, 7); ctx.fill(); ctx.stroke();
  if (inf) {  // 知情: 头顶小亮点
    ctx.fillStyle = "#7fd17f"; ctx.beginPath(); ctx.arc(sx + 7, y0 - 26 + bob, 2.6, 0, 7); ctx.fill();
  }
}
function drawNameBubble(sx, sy, ag, i) {
  const y0 = sy + 14;
  ctx.font = "10.5px 'Noto Sans SC'"; ctx.textAlign = "center";
  ctx.fillStyle = sel === i ? "#ffd166" : "rgba(215,220,230,.92)";
  ctx.fillText(ag.name, sx, y0 - 30);
  const s = sayUntil[i];
  if (s && T < s.until && s.txt) {
    const txt = s.txt.length > 16 ? s.txt.slice(0, 16) + "…" : s.txt;
    ctx.font = "11px 'Noto Sans SC'";
    const w = ctx.measureText(txt).width + 14;
    const by = y0 - 58;
    ctx.fillStyle = "rgba(250,250,252,.96)";
    rr(sx - w / 2, by - 15, w, 19, 5); ctx.fill();
    ctx.strokeStyle = "rgba(60,70,90,.6)"; ctx.stroke();
    ctx.fillStyle = "#222a3a"; ctx.fillText(txt, sx, by - 1);
    ctx.fillStyle = "rgba(250,250,252,.96)";
    ctx.beginPath(); ctx.moveTo(sx - 4, by + 4); ctx.lineTo(sx + 4, by + 4); ctx.lineTo(sx, by + 9); ctx.fill();
  }
}
function rr(x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// ---------- 知情曲线 ----------
function drawSpark(dayCur) {
  const c = $("#spark"), g = c.getContext("2d");
  g.clearRect(0, 0, c.width, c.height);
  const days = R.days, xs = d => d / days * (c.width - 8) + 4, ys = n => c.height - 4 - n / 25 * (c.height - 8);
  g.strokeStyle = "#2b3346"; g.beginPath(); g.moveTo(4, c.height - 4); g.lineTo(c.width - 4, c.height - 4); g.stroke();
  g.strokeStyle = "#7fd17f"; g.lineWidth = 1.6; g.beginPath();
  for (let d = 1; d <= days; d++) {
    const n = D.agents.filter((a, i) => (R.informed[i] || 999) <= d).length;
    d === 1 ? g.moveTo(xs(d), ys(n)) : g.lineTo(xs(d), ys(n));
  }
  g.stroke();
  g.fillStyle = "#4d8dff"; g.fillRect(xs(dayCur) - 1, 0, 2, c.height);
}

// ---------- 面板 ----------
function showAgent(i) {
  sel = i; const a = D.agents[i];
  const day = Math.floor(T / 48) + 1;
  const inf = R.informed[i];
  const mems = (R.mem_rumor[i] || []).filter(r => r[0] <= day).slice(-40);
  $("#panel").innerHTML = `
    <h2>${a.name} <span class="role">· ${a.role}</span></h2>
    <div>${a.seed_role ? `<span class="tag">${a.seed_role}</span>` : ""}
    <span class="tag ${inf && inf <= day ? "inf" : ""}">${inf ? (inf <= day ? `D${inf} 知情` : `D${inf} 将知情`) : "未知情"}</span>
    <span class="tag">住 ${a.home}</span></div>
    <div class="persona">${a.persona || "（无人设注入）"}</div>
    <div id="tlinfo">传闻相关记忆（到第 ${day} 天）</div>
    <div id="memlist">${mems.map(r =>
      `<div class="mrow ${r[2] === "对话" ? "tell" : ""}"><span class="d">D${r[0]}·${String(r[1]).padStart(2, "0")}步</span>${r[2]}：${esc(r[3])}</div>`
    ).join("") || "<div class='mrow'>还没有相关记忆</div>"}</div>`;
}
const esc = s => s.replace(/[<>&]/g, c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

// ---------- 交互 ----------
let drag = null;
cv.addEventListener("mousedown", e => drag = { x: e.clientX, y: e.clientY, cx: cam.x, cy: cam.y, moved: 0 });
addEventListener("mousemove", e => {
  if (!drag) return;
  camTarget = null; follow = -1;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = 1;
  cam.x = drag.cx + dx; cam.y = drag.cy + dy;
});
addEventListener("mouseup", e => {
  if (drag && !drag.moved) pickAgent(e.clientX, e.clientY); drag = null;
});
cv.addEventListener("wheel", e => {
  e.preventDefault();
  const k = e.deltaY < 0 ? 1.12 : 0.9;
  cam.z = Math.min(3.2, Math.max(0.5, cam.z * k));
}, { passive: false });
function pickAgent(px, py) {
  const lx = (px - cam.x) / cam.z, ly = (py - cam.y) / cam.z;
  let best = null, bd = 1e9;
  D.agents.forEach((a, i) => {
    const p = interpPos(i); const [sx, sy] = iso(p[0], p[1]);
    const d = Math.hypot(sx - lx, sy + 14 - ly);
    if (d < bd) { bd = d; best = i; }
  });
  if (bd < 30) { showAgent(best); follow = best; focusAgent(best); }
  else { sel = -1; follow = -1; }
}
function focusAgent(i) {
  const p = interpPos(i); const [ix, iy] = iso(p[0], p[1]);
  const W = innerWidth, H = innerHeight;
  camTarget = { x: (W - 316) / 2 - ix * cam.z, y: H * .45 - iy * cam.z };
}
$("#slider").oninput = e => { playing = false; $("#playBtn").textContent = "▶ 播放"; T = e.target.value / 1000 * (R.days * 48 - 1); };
$("#playBtn").onclick = () => { playing = !playing; $("#playBtn").textContent = playing ? "⏸ 暂停" : "▶ 播放"; };
$("#spdBtn").onclick = () => { speed = speed >= 64 ? 4 : speed * 2; $("#spdBtn").textContent = speed + "×"; };

let last = performance.now();
function loop(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (camTarget) {
    const k = Math.min(1, dt * 4);
    cam.x += (camTarget.x - cam.x) * k; cam.y += (camTarget.y - cam.y) * k;
    if (Math.hypot(camTarget.x - cam.x, camTarget.y - cam.y) < 2) camTarget = null;
  }
  if (follow >= 0 && !camTarget) focusAgent(follow);   // 选中的人移动时镜头跟住
  if (playing) T = Math.min(R.days * 48 - 1, T + dt * speed);
  applyEvents(T); render();
  if (sel >= 0) { /* 面板内容随时间更新一次/秒 */ if (!loop._t || now - loop._t > 1000) { showAgent(sel); loop._t = now; } }
  requestAnimationFrame(loop);
}

fetch("data.json").then(r => r.json()).then(async d => {
  D = d; await loadTiles(); buildMap(); renderMap();
  const tabs = $("#tabs");
  Object.keys(D.runs).forEach(rid => {
    const b = document.createElement("div"); b.className = "tab"; b.dataset.r = rid;
    b.innerHTML = `${D.runs[rid].label}<br><span class="n">${Object.keys(D.runs[rid].informed).length}/25 知情</span>`;
    b.onclick = () => setupRun(rid); tabs.appendChild(b);
  });
  const q = new URLSearchParams(location.search);
  setupRun(q.get("run") || "v2");
  if (q.get("t")) { T = Math.min(R.days * 48 - 1, parseFloat(q.get("t"))); lastT = -1; }
  if (q.get("play")) playing = true;
  requestAnimationFrame(loop);
});
