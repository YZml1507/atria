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
let showNet = true;                               // 传播链路网总开关
let cam = { x: 0, y: 0, z: 1 }, sel = -1, camInit = false, camTarget = null, follow = -1;
let evIdx = [], pos = [], sayUntil = [], walking = [], doorAnchor = {}, lastSay = {};

function panelW() { return innerWidth > 820 ? 316 : 0; }
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
  g.font = "700 26px 'Noto Sans SC'"; g.textAlign = "center";
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
  g.fillStyle = "rgba(18,22,30,.85)";
  g.beginPath(); g.roundRect(sx - w / 2, sy - 16, w, 28, 6); g.fill();
  g.strokeStyle = "rgba(120,140,170,.35)"; g.lineWidth = 1; g.stroke();
  g.fillStyle = "#e8ecf2"; g.fillText(txt, sx, sy + 4);
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
  lastSay = {}; evPtr = 0;
  applyEvents(0);
  buildChapters();
  document.querySelectorAll(".tab").forEach(el => el.classList.toggle("on", el.dataset.r === rid));
  $("#panel").innerHTML = "<h2>点一个居民看记忆</h2><div class='role'>移动中角色头顶气泡是 run 里的真实台词</div>";
}
let evPtr = 0;
const tOf = e => (e[0] - 1) * 48 + e[1];
const normTxt = s => s.replace(/[\s，。！？!?,.…—\-~“”‘’"'：:；;、（）()【】\[\]]/g, '');

// 关键时刻章节: 开局 / 邮局事件或编造起点 / 饱和日 / 结局
function buildChapters() {
  const box = $("#chapters"); box.innerHTML = ""; chapterBtns.length = 0;
  const totalInf = Object.keys(R.informed).length;      // 该 run 知情总人数
  let satDay = null;
  for (let d = 1; d <= R.days; d++) {
    if (Object.values(R.informed).filter(v => v <= d).length >= totalInf) { satDay = d; break; }
  }
  const hasAnchor = run.startsWith("v2") || run.startsWith("v4np");
  const items = [["开局", 1]];
  if (hasAnchor) items.push(["📦 邮局事件", 2]);
  if (run.startsWith("hint0")) {
    const cd = Math.min(...Object.values(R.informed));
    items.push([`🌀 编造发酵 D${cd}`, cd]);
  }
  if (satDay && satDay < R.days && totalInf >= 24) items.push([`🔺 饱和 ${totalInf}/25 D${satDay}`, satDay]);
  else if (totalInf < 24) items.push([`🕸 停滞 ${totalInf}/25`, R.days]);
  items.push(["🏁 结局", R.days]);
  items.forEach(([lb, d]) => {
    const b = document.createElement("button");
    b.textContent = lb;
    b.onclick = () => { T = (d - 1) * 48; lastT = -1;
      if (lb.includes("邮局")) { const p = D.places.find(p => p.name === "邮局");
        if (p) poiFlash = { x: (p.box[0] + p.box[2]) / 2 + .5, y: p.box[3] + .7, t0: performance.now() }; } };
    b._day = d;
    box.appendChild(b);
    chapterBtns.push(b);
  });
}
let chapterBtns = [], poiFlash = null;
function applyEvents(t) {
  // 单调推进; 倒退(拖回去)时重置
  if (t < lastT) { pos = D.agents.map(a => (cellOfHome(a.home) || a.cell).slice()); walking = pos.map(() => null);
    sayUntil = pos.map(() => null); lastSay = {}; evPtr = 0; }
  while (evPtr < evIdx.length && tOf(evIdx[evPtr]) <= t) {
    const e = evIdx[evPtr]; const ai = e[2];
    if (ai >= 0) {
      const to = cellOfPlace(e[3]);
      walking[ai] = { from: pos[ai].slice(), to, t0: tOf(e), dur: 1.6 };
      pos[ai] = to.slice();
      if (e[4]) {
        // 同人同句整 run 只冒一次泡(LLM 复读是噪音);
        // 跨人重复照旧——B 复述 A 的话正是传播证据
        const ls = lastSay[ai], cur = sayUntil[ai];
        if (cur && cur.txt === e[4] && tOf(e) < cur.until + 6) {
          cur.until = Math.max(cur.until, tOf(e) + 1.2);
        } else if (!(ls && ls[normTxt(e[4])])) {
          const jit = (ai * 0.47) % 1.1;
          sayUntil[ai] = { txt: e[4], since: tOf(e) + jit,
            until: tOf(e) + jit + 2.0 + Math.min(4.0, e[4].length * 0.055) };
          (lastSay[ai] = lastSay[ai] || {})[normTxt(e[4])] = 1;
        }
      }
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
    cam.x = (W - panelW()) / 2 - cx * cam.z; cam.y = H * .5 - cy * cam.z; camInit = true; }
  ctx.save();
  ctx.translate(cam.x, cam.y); ctx.scale(cam.z, cam.z);
  ctx.drawImage(mapCv, 0, 0);

  // agents: 屏幕空间恒定大小绘制, 保证可读
  const order = D.agents.map((a, i) => {
    const p = interpPos(i);
    return { i, x: p[0], y: p[1] };
  }).sort((a, b) => (a.x + a.y) - (b.x + b.y));
  // 同格散开: 每格第 k 个人沿环偏移
  const cellCnt = {}, cellIdx = {};
  order.forEach(a => { const k = Math.round(a.x) + "," + Math.round(a.y);
    cellIdx[a.i] = cellCnt[k] || 0; cellCnt[k] = (cellCnt[k] || 0) + 1; });
  order.forEach(a => {
    a.bx = Math.round(a.x); a.by = Math.round(a.y);
    const k = cellIdx[a.i];
    if (k > 0) { const ang = k * 2.1 - 1;
      a.x += Math.cos(ang) * 0.42; a.y += Math.sin(ang) * 0.42; }
    const da = doorAnchor[a.bx + "," + a.by];
    if (da) { a.x = da[0] + (a.x - a.bx); a.y = da[1] + (a.y - a.by); }  // 室内→站门口
  });
  const day = Math.floor(T / 48) + 1;
  let know = 0;
  ctx.restore();
  const spos = {};
  for (const a of order) {
    const ag = D.agents[a.i];
    const [ix, iy] = iso(a.x, a.y);
    const sx = ix * cam.z + cam.x, sy = iy * cam.z + cam.y;
    spos[a.i] = [sx, sy + 8];
    const inf = (R.informed[a.i] || 999) <= day;
    if (inf) know++;
    drawAgent(sx, sy, ag, a.i, inf, day);
  }
  drawEdges(spos);
  if (showNet && R.edges && R.edges.length) {
    ctx.font = "600 11px 'Noto Sans SC'"; ctx.textAlign = "left";
    ctx.fillStyle = "rgba(10,12,18,.55)"; rr(10, H - 118, 172, 44, 6); ctx.fill();
    ctx.fillStyle = "#ffd166"; ctx.fillText("━ 首传(当日知情)", 20, H - 96);
    ctx.fillStyle = "rgba(160,180,210,.9)"; ctx.fillText("┅ 转述 · 点人看个人链", 20, H - 80);
  }
  const bubRects = [];
  for (const a of order) {
    const ag = D.agents[a.i];
    const [ix, iy] = iso(a.x, a.y);
    // 同格散开者的名字确定性错位: 第 k 个人左右交替偏 46px
    const k = cellIdx[a.i];
    const dx = k > 0 ? (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 46 : 0;
    drawNameBubble(ix * cam.z + cam.x + dx, iy * cam.z + cam.y - k * 8, ag, a.i, bubRects, ix * cam.z + cam.x);
  }
  if (poiFlash) {
    const age = (performance.now() - poiFlash.t0) / 1000;
    if (age > 8) poiFlash = null;
    else {
      const [fx, fy] = iso(poiFlash.x, poiFlash.y);
      const fsx = fx * cam.z + cam.x, fsy = fy * cam.z + cam.y;
      const ph = (age % 1.2) / 1.2, al = (1 - ph) * (age > 3 ? (4 - age) : 1);
      ctx.strokeStyle = `rgba(255,209,102,${.85 * al})`; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(fsx, fsy + 14, 14 + ph * 46, 0, 7); ctx.stroke();
      ctx.strokeStyle = `rgba(255,209,102,${.5 * al})`;
      ctx.beginPath(); ctx.arc(fsx, fsy + 14, 7, 0, 7); ctx.stroke();
      ctx.font = "700 14px 'Noto Sans SC'"; ctx.textAlign = "center";
      ctx.fillStyle = `rgba(255,209,102,${al})`; ctx.fillText("📦 邮局事件", fsx, fsy - 52);
    }
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

// 传播链路: 虚线弧 src->dst; 刚发生的首传亮黄点流动, showNet 时保留全部历史淡线
function drawEdges(spos) {
  if (!R.edges) return;
  for (const [s, dd, day, step, first] of R.edges) {
    const dt = T - ((day - 1) * 48 + step);
    const fresh = dt >= 0 && dt < 10;
    if (!fresh && !(showNet && dt >= 0)) continue;
    const p0 = spos[s], p1 = spos[dd];
    if (!p0 || !p1) continue;
    const mx = (p0[0] + p1[0]) / 2, my = Math.min(p0[1], p1[1]) - 26 - Math.abs(p1[0] - p0[0]) * .12;
    ctx.beginPath(); ctx.moveTo(p0[0], p0[1]); ctx.quadraticCurveTo(mx, my, p1[0], p1[1]);
    if (fresh) {
      ctx.strokeStyle = first ? "rgba(255,209,102,.9)" : "rgba(127,209,127,.85)";
      ctx.lineWidth = 2.4;
    } else {
      ctx.strokeStyle = first ? "rgba(255,209,102,.30)" : "rgba(120,150,190,.13)";
      ctx.lineWidth = 1;
    }
    ctx.setLineDash([5, 5]); ctx.stroke(); ctx.setLineDash([]);
    if (fresh) {
      const ph = Math.min(1, dt / 6), u = 1 - ph;
      const qx = u * u * p0[0] + 2 * u * ph * mx + ph * ph * p1[0];
      const qy = u * u * p0[1] + 2 * u * ph * my + ph * ph * p1[1];
      ctx.fillStyle = first ? "#ffd166" : "#7fd17f";
      ctx.beginPath(); ctx.arc(qx, qy, 4, 0, 7); ctx.fill();
    }
  }
}
function drawAgent(sx, sy, ag, i, inf, dayCur) {
  const bob = walking[i] ? Math.sin(T * 9 + i) * 2 : 0;
  const y0 = sy + 20;
  // 当天刚知情: 脉冲扩散环, 让“传播发生”一眼可见
  if (inf && R.informed[i] === dayCur) {
    const ph = (T * 0.8) % 1;
    ctx.strokeStyle = `rgba(127,209,127,${0.75 * (1 - ph)})`;
    ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(sx, y0 - 20 + bob, 14 + ph * 26, 0, 7); ctx.stroke();
  }
  // 影子
  ctx.fillStyle = "rgba(0,0,0,.28)"; ctx.beginPath();
  ctx.ellipse(sx, y0 + 3, 13, 5, 0, 0, 7); ctx.fill();
  // 身体
  ctx.fillStyle = sel === i ? "#ffd166" : PAL[i];
  ctx.strokeStyle = "rgba(0,0,0,.55)"; ctx.lineWidth = 1.6;
  rr(sx - 8, y0 - 27 + bob, 16, 24, 6); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.arc(sx, y0 - 34 + bob, 7.5, 0, 7); ctx.fill(); ctx.stroke();
  if (inf) {  // 知情: 头顶小亮点
    ctx.fillStyle = "#7fd17f"; ctx.strokeStyle = "rgba(0,0,0,.4)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(sx + 11, y0 - 41 + bob, 4.5, 0, 7); ctx.fill(); ctx.stroke();
  }
}
function drawNameBubble(sx, sy, ag, i, placed, ox) {
  const y0 = sy + 20;
  ctx.textAlign = "center";
  // 名字: 缩得太小只显示选中的; 钳进屏幕; 互撞先上移再侧移, 仍撞则不画
  if (cam.z >= 0.34 || sel === i) {
    ctx.font = "600 18px 'Noto Sans SC'";
    const nw = ctx.measureText(ag.name).width;
    let ny = y0 - 50, nt = 0;
    let nx = Math.min(Math.max(sx, nw / 2 + 6), innerWidth - panelW() - nw / 2 - 6);
    const tryPos = () => placed.some(q => nx - nw / 2 - 2 < q.x1 && nx + nw / 2 + 2 > q.x0 && ny - 20 < q.y1 && ny + 6 > q.y0);
    while (tryPos() && nt < 6) {
      const m = nt % 3;
      if (m === 0) ny -= 28;
      else if (m === 1) nx = Math.min(sx + 62, innerWidth - panelW() - nw / 2 - 6);
      else nx = Math.max(sx - 62, nw / 2 + 6);
      nt++;
    }
    sx = nx;
    const underHud = sel !== i && nx - nw / 2 < 470 && ny < 132;   // 左上角 HUD 区域不画名字
    if (tryPos() || underHud) { /* 避让失败/遮挡HUD: 跳过名字防叠读 */ } else {
    placed.push({ x0: sx - nw / 2 - 2, x1: sx + nw / 2 + 2, y0: ny - 20, y1: ny + 6 });
    // 避让拉开较远时画虚线牵引回本人头顶, 防止“有名字没人”
    if (ox !== undefined && (Math.abs(sx - ox) > 30 || ny < y0 - 66)) {
      ctx.strokeStyle = "rgba(235,238,245,.45)"; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
      ctx.beginPath(); ctx.moveTo(sx, ny + 5); ctx.lineTo(ox, y0 - 40); ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.lineWidth = 5; ctx.strokeStyle = "rgba(10,12,18,.8)";
    ctx.strokeText(ag.name, sx, ny);
    ctx.fillStyle = sel === i ? "#ffd166" : "rgba(235,238,245,.97)";
    ctx.fillText(ag.name, sx, ny);
    }
  }
  const s = sayUntil[i];
  if (s && T >= (s.since || 0) && T < s.until && s.txt) {
    const fade = Math.min(1, (T - (s.since || 0)) / 0.12, (s.until - T) / 0.15);
    ctx.save(); ctx.globalAlpha = Math.max(0, fade);
    const txt = s.txt.length > 22 ? s.txt.slice(0, 22) + "…" : s.txt;
    ctx.font = "700 13px 'Noto Sans SC'";
    const nw = ctx.measureText(ag.name).width;
    ctx.font = "600 17px 'Noto Sans SC'";
    const w = Math.max(ctx.measureText(txt).width, nw) + 26;
    // 气泡水平钳进可视区(留出右侧面板)
    sx = Math.min(Math.max(sx, w / 2 + 10), innerWidth - panelW() - 14 - w / 2);
    let by = Math.max(y0 - 96, 56);   // 顶部不裁切
    // 防重叠: 与已放气泡碰撞则上移一个槽位
    const rect = () => ({ x0: sx - w / 2 - 3, x1: sx + w / 2 + 3, y0: by - 46, y1: by + 17 });
    let r = rect(), tries = 0;
    while (placed.some(q => r.x0 < q.x1 && r.x1 > q.x0 && r.y0 < q.y1 && r.y1 > q.y0) && tries < 6) {
      by -= 54; r = rect(); tries++;
    }
    by = Math.max(by, 56);           // 避让后仍不越顶
    placed.push(r);
    ctx.fillStyle = "rgba(252,252,254,.97)";
    rr(sx - w / 2, by - 44, w, 50, 8); ctx.fill();
    ctx.strokeStyle = "rgba(50,60,80,.65)"; ctx.lineWidth = 1.4; ctx.stroke();
    ctx.font = "700 13px 'Noto Sans SC'";
    ctx.fillStyle = PAL[i]; ctx.fillText(ag.name, sx, by - 26);
    ctx.font = "600 17px 'Noto Sans SC'";
    ctx.fillStyle = "#1c2333"; ctx.fillText(txt, sx, by - 6);
    ctx.fillStyle = "rgba(252,252,254,.97)";
    ctx.beginPath(); ctx.moveTo(sx - 6, by + 6); ctx.lineTo(sx + 6, by + 6); ctx.lineTo(sx, by + 14); ctx.fill();
    ctx.restore();
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
    ${(() => {
      const ins = (R.edges || []).filter(e => e[1] === i && e[2] <= day);
      const outs = (R.edges || []).filter(e => e[0] === i && e[2] <= day);
      if (!ins.length && !outs.length) return "";
      const fmt = es => es.map(e => `${D.agents[e[0] === i ? e[1] : e[0]].name}<span class="d">D${e[2]}</span>`).join("，");
      return `<div id="chain">${ins.length ? `<div>◀ 被告知：${fmt(ins)}</div>` : ""}${outs.length ? `<div>▶ 告知了：${fmt(outs)}</div>` : ""}</div>`;
    })()}
    <div id="tlinfo">传闻相关记忆（到第 ${day} 天）</div>
    <div id="memlist">${mems.map(r =>
      `<div class="mrow ${r[2] === "对话" ? "tell" : ""}"><span class="d">D${r[0]}·${String(r[1]).padStart(2, "0")}步</span>${r[2]}：${esc(r[3])}</div>`
    ).join("") || "<div class='mrow'>还没有相关记忆</div>"}</div>`;
}
const esc = s => s.replace(/[<>&]/g, c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

// ---------- 交互 ----------
let drag = null;
function dbg(s) { let d = document.getElementById("dbg"); if (!d) { d = document.createElement("div"); d.id = "dbg"; d.style.cssText = "position:fixed;left:8px;top:180px;background:#000a;color:#ff0;font:20px monospace;padding:8px;z-index:99999"; document.body.appendChild(d); } d.textContent = s; }
cv.addEventListener("mousedown", e => drag = { x: e.clientX, y: e.clientY, cx: cam.x, cy: cam.y, moved: 0 });
addEventListener("mousemove", e => {
  if (!drag) return;
  camTarget = null; follow = -1;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 30) drag.moved = 1;
  cam.x = drag.cx + dx; cam.y = drag.cy + dy;
});
addEventListener("mouseup", e => {
  if (drag && !drag.moved) { try { pickAgent(e.clientX, e.clientY); } catch (err) { if (location.hash.includes("dbg")) dbg(`pickAgent throw: ${err.message}`); } } else if (drag && location.hash.includes("dbg")) dbg(`moved up(${e.clientX},${e.clientY})`); drag = null;
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
  if (bd < 26 / cam.z) { showAgent(best); follow = best; focusAgent(best); }
  else { sel = -1; follow = -1; }
  if (location.hash.includes("dbg")) dbg(`pick(${px},${py}) bd=${bd.toFixed(1)} z=${cam.z.toFixed(2)} sel=${best}`);
}
function focusAgent(i) {
  const p = interpPos(i); const [ix, iy] = iso(p[0], p[1]);
  const W = innerWidth, H = innerHeight;
  camTarget = { x: (W - panelW()) / 2 - ix * cam.z, y: H * .45 - iy * cam.z };
}
$("#slider").oninput = e => { playing = false; $("#playBtn").textContent = "▶ 播放"; T = e.target.value / 1000 * (R.days * 48 - 1); };
$("#playBtn").onclick = () => { playing = !playing; $("#playBtn").textContent = playing ? "⏸ 暂停" : "▶ 播放"; };
$("#spdBtn").onclick = () => { speed = speed >= 64 ? 1 : speed * 2; $("#spdBtn").textContent = speed + "×"; };
$("#netBtn").onclick = () => { showNet = !showNet; $("#netBtn").style.opacity = showNet ? 1 : .45; };

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
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => renderMap());
  // 建筑内部格→门口锚点(室内的人渲染到门前)
  const putDoor = (box) => { const [x0, y0, x1, y1] = box;
    const dx = (x0 + x1) / 2 + .5, dy = y1 + 1.05;
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) doorAnchor[x + "," + y] = [dx, dy]; };
  D.homes.forEach(h => putDoor(h.box));
  D.places.forEach(p => { if (p.name !== "镇公园") putDoor(p.box); });
  const tabs = $("#tabs");
  Object.keys(D.runs).forEach(rid => {
    const b = document.createElement("div"); b.className = "tab"; b.dataset.r = rid;
    const short = { "v2": "v2 锚+引", "v4np": "v4 锚·无引", "v4np2": "v4 种子2", "v3": "v3 零注入", "v3s2": "v3 零·种子2", "v3s3": "v3 零·种子3", "hint0": "v4 零锚+引", "hint0s2": "v4 零锚·种子2", "hint0g": "v4 零锚·银元", "v2s2": "v2 锚+引·种子2", "multi": "multi 双传闻", "debunk": "debunk 辟谣" };
    b.innerHTML = `${short[rid] || D.runs[rid].label}<br><span class="n">${Object.keys(D.runs[rid].informed).length}/25 知情</span>`;
    b.onclick = () => setupRun(rid); tabs.appendChild(b);
  });
  const q = new URLSearchParams(location.search);
  setupRun(q.get("run") || "v2");
  if (q.get("t")) { T = Math.min(R.days * 48 - 1, parseFloat(q.get("t"))); lastT = -1; }
  if (q.get("sel") != null) { const sq = q.get("sel"); const si = isNaN(+sq) ? D.agents.findIndex(a => a.name === sq) : +sq; if (si >= 0 && si < 25) showAgent(si); }
  if (q.get("z")) { cam.z = Math.min(3.2, Math.max(0.5, +q.get("z"))); }
  if (q.has("play")) { playing = true; $("#playBtn").textContent = "⏸ 暂停"; }
  if (q.has("tour")) {
    playing = true; $("#playBtn").textContent = "⏸ 暂停";
    let ci = 0;
    setInterval(() => {
      if (!chapterBtns.length) return;
      ci = (ci + 1) % chapterBtns.length;
      T = (chapterBtns[ci]._day - 1) * 48; lastT = -1;
    }, 9000);
  }
  if (q.get("speed")) { speed = Math.min(64, Math.max(1, +q.get("speed") || 8)); $("#spdBtn").textContent = speed + "×"; }
  // 遥控钩子: 若 hall/ 下存在 cmd.json 则每 0.7s 应用一次指令 (录制/演示脚本用; 无文件时静默)
  let lastCmd = null;
  setInterval(() => {
    fetch("cmd.json?_=" + Date.now()).then(r => r.ok ? r.json() : null).then(c => {
      if (!c || c.seq === lastCmd) return; lastCmd = c.seq;
      if (c.run && run !== c.run) setupRun(c.run);
      if (c.t != null) { T = Math.min(R.days * 48 - 1, +c.t); lastT = -1; }
      if (c.sel != null) { const si = isNaN(+c.sel) ? D.agents.findIndex(a => a.name === c.sel) : +c.sel; if (si >= 0) { showAgent(si); follow = si; focusAgent(si); } }
      if (c.z != null) cam.z = Math.min(3.2, Math.max(0.5, +c.z));
      if (c.cam) camTarget = { x: c.cam[0], y: c.cam[1] };
      if (c.center) { const [ix, iy] = iso(12.5, 12.5); camTarget = { x: (innerWidth - panelW()) / 2 - ix * cam.z, y: innerHeight * .45 - iy * cam.z }; }
      if (c.play != null) { playing = !!c.play; $("#playBtn").textContent = playing ? "⏸ 暂停" : "▶ 播放"; }
      if (c.speed) { speed = Math.min(64, Math.max(1, +c.speed)); $("#spdBtn").textContent = speed + "×"; }
      if (c.net != null) { showNet = !!c.net; $("#netBtn").style.opacity = showNet ? 1 : .45; }
      if (c.deselect) { sel = -1; follow = -1; $("#panel").innerHTML = ""; }
    }).catch(() => {});
  }, 700);
  requestAnimationFrame(loop);
});
