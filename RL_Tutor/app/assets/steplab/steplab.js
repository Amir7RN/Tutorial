/* Step-lab framework: one page = a picture you can change, a numbered list of
   steps, and the live math for the current step.

   SL.app({
     title, sub,
     steps: [[title, text], ...],
     controls: [{id, label, min, max, step, value, fmt}],   values in SL.v[id]
     buttons: [{id, label, toggle, pressed, onclick}],
     legend: [[cssVar, label], ...],
     view: '2d' | '3d',
     setup(ctx), draw(ctx), math(st) -> html, stats() -> html,
     play: {tick(dt)}            optional: adds Play/Reset
     reset()                     optional
   })
   ctx is a Plot2D (2d) or Scene3D (3d). SL.st = current step, SL.anim ∈ [0,1].
*/
(function () {
const SL = window.SL = {};
SL.v = {}; SL.st = 0; SL.anim = 1;
SL.css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
SL.f = (x, d = 2) => { if (!isFinite(x)) return '∞'; const r = Math.abs(x) < 0.5 * Math.pow(10, -d) ? 0 : x; return r.toFixed(d); };
SL.sf = (x, d = 2) => (x >= 0 ? '+' : '') + SL.f(x, d);
SL.vs = (v, d = 2) => '(' + v.map(x => SL.f(x, d)).join(', ') + ')';
SL.deg = r => SL.f(r * 180 / Math.PI, 1) + '°';
/* matrix as aligned monospace text */
SL.mat = (A, d = 2, name) => {
  const s = A.map(r => r.map(x => SL.f(x, d)));
  const w = Math.max(...s.flat().map(x => x.length));
  const rows = s.map(r => r.map(x => x.padStart(w)).join('  '));
  const pad = name ? ' '.repeat(name.length + 3) : '';
  return rows.map((r, i) => (i === Math.floor((rows.length - 1) / 2) && name ? name + ' = ' : pad) + '[ ' + r + ' ]').join('\n');
};
SL.eq = s => `<span class="eq">${s}</span>`;
SL.m = s => `<span class="m">${s}</span>`;
SL.ul = a => '<ul>' + a.map(x => '<li>' + x + '</li>').join('') + '</ul>';
SL.ol = a => '<ol>' + a.map(x => '<li>' + x + '</li>').join('') + '</ol>';
SL.lerp = (a, b, t) => Array.isArray(a) ? a.map((x, i) => x + (b[i] - x) * t) : a + (b - a) * t;
SL.ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

/* ---------------- 2-D plotting ---------------- */
class Panel {
  constructor(P, x, y, w, h, b, equal = true) { Object.assign(this, { P, x, y, w, h, b, equal }); this.fit(); }
  fit() {
    const [x0, x1, y0, y1] = this.b; let sx = this.w / (x1 - x0), sy = this.h / (y1 - y0);
    if (this.equal) { const s = Math.min(sx, sy); sx = sy = s; }
    this.sx = sx; this.sy = sy;
    this.ox = this.x + (this.w - (x1 - x0) * sx) / 2 - x0 * sx;
    this.oy = this.y + (this.h - (y1 - y0) * sy) / 2 + y1 * sy;
  }
  S(p) { return [this.ox + p[0] * this.sx, this.oy - p[1] * this.sy]; }
  inv(x, y) { return [(x - this.ox) / this.sx, (this.oy - y) / this.sy]; }
  get c() { return this.P.c; }
  col(cl) { return cl && cl.startsWith('--') ? SL.css(cl) : cl; }
  frame(title) {
    const c = this.c; c.save(); c.fillStyle = SL.css('--inset'); c.strokeStyle = SL.css('--line'); c.lineWidth = 1;
    c.fillRect(this.x, this.y, this.w, this.h); c.strokeRect(this.x, this.y, this.w, this.h); c.restore();
    if (title) this.label(this.x + 8, this.y + 16, title, '--muted');
  }
  clip(fn) { const c = this.c; c.save(); c.beginPath(); c.rect(this.x, this.y, this.w, this.h); c.clip(); fn(); c.restore(); }
  grid(step = 1, cl = '--line') {
    const [x0, x1, y0, y1] = this.b;
    for (let x = Math.ceil(x0 / step) * step; x <= x1 + 1e-9; x += step) this.line([x, y0], [x, y1], cl, 1);
    for (let y = Math.ceil(y0 / step) * step; y <= y1 + 1e-9; y += step) this.line([x0, y], [x1, y], cl, 1);
  }
  axes(cl = '--grey') { const [x0, x1, y0, y1] = this.b; this.line([x0, 0], [x1, 0], cl, 1); this.line([0, y0], [0, y1], cl, 1); }
  line(a, b, cl, w = 2, dash) {
    const c = this.c, A = this.S(a), B = this.S(b); c.beginPath(); c.strokeStyle = this.col(cl); c.lineWidth = w;
    c.setLineDash(dash || []); c.moveTo(...A); c.lineTo(...B); c.stroke(); c.setLineDash([]);
  }
  poly(pts, cl, w = 2, dash, fill, close) {
    if (pts.length < 2) return; const c = this.c; c.beginPath();
    pts.forEach((p, i) => { const s = this.S(p); i ? c.lineTo(...s) : c.moveTo(...s); });
    if (close || fill) c.closePath();
    if (fill) { c.fillStyle = this.col(fill); c.globalAlpha = .18; c.fill(); c.globalAlpha = 1; }
    if (cl) { c.strokeStyle = this.col(cl); c.lineWidth = w; c.setLineDash(dash || []); c.stroke(); c.setLineDash([]); }
  }
  arrow(o, v, cl, w = 2.5, label, dash, ldx = 8, ldy = -6) {
    const c = this.c, A = this.S(o), B = this.S([o[0] + v[0], o[1] + v[1]]), dx = B[0] - A[0], dy = B[1] - A[1], L = Math.hypot(dx, dy);
    const col = this.col(cl); c.beginPath(); c.strokeStyle = col; c.lineWidth = w; c.setLineDash(dash || []);
    c.moveTo(...A); c.lineTo(...B); c.stroke(); c.setLineDash([]);
    if (L > 5) {
      const ux = dx / L, uy = dy / L, h = Math.min(11, L * .45); c.beginPath(); c.fillStyle = col; c.moveTo(...B);
      c.lineTo(B[0] - ux * h - uy * h * .45, B[1] - uy * h + ux * h * .45); c.lineTo(B[0] - ux * h + uy * h * .45, B[1] - uy * h - ux * h * .45); c.closePath(); c.fill();
    }
    if (label) this.label(B[0] + ldx, B[1] + ldy, label, cl);
  }
  dot(p, r = 4, cl = '--ink', ring) {
    const c = this.c, s = this.S(p); c.beginPath(); c.arc(s[0], s[1], r, 0, 2 * Math.PI);
    if (ring) { c.fillStyle = SL.css('--panel'); c.fill(); c.strokeStyle = this.col(cl); c.lineWidth = 2.5; c.stroke(); }
    else { c.fillStyle = this.col(cl); c.fill(); }
  }
  circle(p, r, cl, w = 1.5, dash) {   // r in world units
    const c = this.c, s = this.S(p); c.beginPath(); c.ellipse(s[0], s[1], r * this.sx, r * this.sy, 0, 0, 2 * Math.PI);
    c.strokeStyle = this.col(cl); c.lineWidth = w; c.setLineDash(dash || []); c.stroke(); c.setLineDash([]);
  }
  /* image of the unit circle under the 2×2 map A, centred at p */
  ellipse(p, A, cl, w = 2, dash, fill) {
    const pts = []; for (let i = 0; i <= 96; i++) { const t = i / 96 * 2 * Math.PI, u = [Math.cos(t), Math.sin(t)];
      pts.push([p[0] + A[0][0] * u[0] + A[0][1] * u[1], p[1] + A[1][0] * u[0] + A[1][1] * u[1]]); }
    this.poly(pts, cl, w, dash, fill, true);
  }
  text(p, s, cl = '--ink', dx = 0, dy = 0, o = {}) { const P = this.S(p); this.label(P[0] + dx, P[1] + dy, s, cl, o); }
  label(x, y, s, cl = '--ink', o = {}) {
    const c = this.c; c.fillStyle = this.col(cl); c.font = `${o.mono ? '600 12px ' + SL.css('--mono') : (o.bold === false ? '' : '700 ') + (o.size || 13) + 'px ' + SL.css('--body')}`;
    c.textAlign = o.align || 'left'; c.fillText(s, x, y); c.textAlign = 'left';
  }
  /* arc of radius r (pixels) around p from angle a0 to a1 (radians, world sense) */
  arc(p, r, a0, a1, cl, w = 2.5, head = true, label) {
    const c = this.c, s = this.S(p), col = this.col(cl); if (Math.abs(a1 - a0) < 1e-3) return;
    c.beginPath(); c.strokeStyle = col; c.lineWidth = w; c.arc(s[0], s[1], r, -a0, -a1, a1 > a0); c.stroke();
    if (head) { const e = -a1, ex = s[0] + r * Math.cos(e), ey = s[1] + r * Math.sin(e), dir = a1 > a0 ? -1 : 1;
      const tx = -Math.sin(e) * dir, ty = Math.cos(e) * dir; c.beginPath(); c.fillStyle = col;
      c.moveTo(ex + tx * 8, ey + ty * 8); c.lineTo(ex - ty * 4.5, ey + tx * 4.5); c.lineTo(ex + ty * 4.5, ey - tx * 4.5); c.closePath(); c.fill(); }
    if (label) this.label(s[0] + (r + 6) * Math.cos(-(a0 + a1) / 2), s[1] + (r + 6) * Math.sin(-(a0 + a1) / 2) + 4, label, cl, { mono: true });
  }
  /* a planar serial arm: links + joint rings */
  arm(P, o = {}) {
    const jc = o.jc || ['--d', '--e', '--c', '--f'];
    for (let i = 0; i < P.length - 1; i++) this.line(P[i], P[i + 1], o.ghost ? '--grey' : (o.col || '--link'), o.w || 6, o.ghost ? [5, 4] : null);
    if (o.ghost) return;
    P.slice(0, -1).forEach((p, i) => this.dot(p, 7, jc[i % jc.length], true));
    this.dot(P[P.length - 1], 4.5, '--ink');
  }
  /* time-series axes helper: draws a function list [{pts, cl, label}] */
  series(list, o = {}) {
    this.frame(o.title); const [x0, x1, y0, y1] = this.b;
    this.clip(() => { if (y0 < 0 && y1 > 0) this.line([x0, 0], [x1, 0], '--grey', 1); list.forEach(s => this.poly(s.pts, s.cl, s.w || 2, s.dash)); });
    let lx = this.x + 8; list.forEach(s => { if (!s.label) return; this.c.font = '12px ' + SL.css('--body');
      this.label(lx, this.y + this.h - 8, s.label, s.cl, { size: 12 }); lx += this.c.measureText(s.label).width + 16; });
    if (o.yl) this.label(this.x + this.w - 6, this.y + 16, o.yl, '--muted', { align: 'right', size: 12 });
  }
}
class Plot2D {
  constructor(cv) { this.cv = cv; this.c = cv.getContext('2d'); this.panels = []; }
  resize() { const r = this.cv.getBoundingClientRect(), d = window.devicePixelRatio || 1; this.W = r.width; this.H = r.height;
    this.cv.width = Math.round(r.width * d); this.cv.height = Math.round(r.height * d); this.d = d; }
  begin() { this.c.setTransform(this.d, 0, 0, this.d, 0, 0); this.c.clearRect(0, 0, this.W, this.H); this.panels = []; }
  /* panel in fractions of the canvas: fx, fy, fw, fh ∈ [0,1] */
  panel(fx, fy, fw, fh, b, equal = true) { const p = new Panel(this, fx * this.W, fy * this.H, fw * this.W, fh * this.H, b, equal); this.panels.push(p); return p; }
}

/* ---------------- 3-D scene (z up; three.js) ---------------- */
class Scene3D {
  constructor(cv, view, o = {}) {
    this.cv = cv; this.view = view;
    this.r = new THREE.WebGLRenderer({ canvas: cv, antialias: true });
    this.scene = new THREE.Scene(); this.cam = new THREE.PerspectiveCamera(40, 1.3, .02, 200);
    this.scene.add(new THREE.AmbientLight(0xffffff, .62)); const dl = new THREE.DirectionalLight(0xffffff, .7); dl.position.set(4, 8, 6); this.scene.add(dl);
    this.orb = Object.assign({ az: .7, el: .45, r: 5, tgt: [0, 0, .5] }, o);
    this.dyn = new THREE.Group(); this.scene.add(this.dyn); this.labels = [];
    let drag = null;
    cv.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY]; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove', e => { if (!drag) return; this.orb.az -= (e.clientX - drag[0]) * .008;
      this.orb.el = Math.max(-.2, Math.min(1.5, this.orb.el + (e.clientY - drag[1]) * .006)); drag = [e.clientX, e.clientY]; SL.redraw(); });
    ['pointerup', 'pointercancel'].forEach(t => cv.addEventListener(t, () => drag = null));
    cv.addEventListener('wheel', e => { e.preventDefault(); this.orb.r = Math.max(1.5, Math.min(30, this.orb.r * (1 + Math.sign(e.deltaY) * .08))); SL.redraw(); }, { passive: false });
  }
  V(p) { return new THREE.Vector3(p[0], p[2], -p[1]); }
  col(c) { return new THREE.Color(c.startsWith('--') ? SL.css(c) : c); }
  resize() { const w = this.cv.clientWidth, h = this.cv.clientHeight; if (!w) return; this.r.setPixelRatio(window.devicePixelRatio || 1);
    this.r.setSize(w, h, false); this.cam.aspect = w / h; this.cam.updateProjectionMatrix(); }
  begin() {
    while (this.dyn.children.length) { const o = this.dyn.children.pop(); o.geometry && o.geometry.dispose(); }
    this.labels.forEach(l => l.remove()); this.labels = [];
    this.scene.background = this.col('--panel');
    const t = this.orb.tgt, o = this.orb;
    this.cam.position.copy(this.V([t[0] + o.r * Math.cos(o.el) * Math.cos(o.az), t[1] + o.r * Math.cos(o.el) * Math.sin(o.az), t[2] + o.r * Math.sin(o.el)]));
    this.cam.up.set(0, 1, 0); this.cam.lookAt(this.V(t));
  }
  end() { this.r.render(this.scene, this.cam); }
  mat(c, o = {}) { return new THREE.MeshStandardMaterial({ color: this.col(c), roughness: .55, metalness: .1, transparent: !!o.opacity, opacity: o.opacity || 1, side: THREE.DoubleSide }); }
  grid(size = 4, div = 16, z = 0) { const g = new THREE.GridHelper(size, div, this.col('--line'), this.col('--line')); g.position.y = z; this.dyn.add(g); }
  line(pts, c, dash) {
    const g = new THREE.BufferGeometry().setFromPoints(pts.map(p => this.V(p)));
    const m = dash ? new THREE.LineDashedMaterial({ color: this.col(c), dashSize: .06, gapSize: .05 }) : new THREE.LineBasicMaterial({ color: this.col(c) });
    const l = new THREE.Line(g, m); if (dash) l.computeLineDistances(); this.dyn.add(l); return l;
  }
  arrow(o, v, c, k = 1, head) {
    const d = this.V(v).multiplyScalar(k), L = d.length(); if (L < 1e-4) return;
    const a = new THREE.ArrowHelper(d.clone().normalize(), this.V(o), L, this.col(c), head || Math.min(.14, L * .3), Math.min(.08, L * .2)); this.dyn.add(a); return a;
  }
  cyl(a, b, r, c, o) {
    const A = this.V(a), B = this.V(b), L = A.distanceTo(B); if (L < 1e-6) return;
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, L, 20), this.mat(c, o));
    m.position.copy(A.clone().add(B).multiplyScalar(.5)); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.clone().sub(A).normalize());
    this.dyn.add(m); return m;
  }
  box(T, size, c, o) {                       // box with pose T (4×4, robot frame)
    const m = new THREE.Mesh(new THREE.BoxGeometry(size[0], size[2], size[1]), this.mat(c, o)); this.place(m, T); this.dyn.add(m); return m;
  }
  ellipsoid(T, radii, c, o) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 20), this.mat(c, o)); m.scale.set(radii[0], radii[2], radii[1]); this.place(m, T); this.dyn.add(m); return m;
  }
  place(m, T) {                               // robot pose → three object (scale kept)
    const R = T.slice(0, 3).map(r => r.slice(0, 3)), ex = this.V(MR.col(R, 0)), ey = this.V(MR.col(R, 1)), ez = this.V(MR.col(R, 2));
    const s = m.scale.clone(), M4 = new THREE.Matrix4().makeBasis(ex, ez, ey.clone().negate());
    m.quaternion.setFromRotationMatrix(M4); m.position.copy(this.V([T[0][3], T[1][3], T[2][3]])); m.scale.copy(s);
  }
  sphere(p, r, c, o) { const m = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), this.mat(c, o)); m.position.copy(this.V(p)); this.dyn.add(m); return m; }
  frame(T, L = .3, lab) {                     // coordinate triad of pose T
    const p = MR.pof(T), R = MR.Rof(T);
    ['#e05555', '#3fb950', '#4e8cff'].forEach((c, j) => this.arrow(p, MR.scl(MR.col(R, j), L), c, 1, L * .28));
    if (lab) this.label(p, lab, '--muted');
  }
  label(p, s, cl = '--ink') {
    const v = this.V(p).project(this.cam); if (v.z > 1) return;
    const d = document.createElement('div'); d.className = 'lbl'; d.style.color = cl.startsWith('--') ? `var(${cl})` : cl; d.textContent = s;
    const r = this.cv.getBoundingClientRect(), vr = this.view.getBoundingClientRect();
    d.style.left = (r.left - vr.left + (v.x + 1) / 2 * r.width) + 'px'; d.style.top = (r.top - vr.top + (1 - v.y) / 2 * r.height) + 'px';
    this.view.appendChild(d); this.labels.push(d);
  }
}
SL.Plot2D = Plot2D; SL.Scene3D = Scene3D;

/* ---------------- the page ---------------- */
SL.app = cfg => {
  SL.cfg = cfg;
  document.title = cfg.title;
  document.body.innerHTML = `
<div class="wrap">
  <div class="top"><h1>${cfg.title}</h1><p>${cfg.sub || ''}</p></div>
  <div class="grid">
    <div class="left">
      <div class="card view" id="view"><canvas id="cv"></canvas></div>
      ${cfg.legend ? `<div class="legend">${cfg.legend.map(([c, l]) => `<span><span class="sw" style="background:var(${c})"></span>${l}</span>`).join('')}</div>` : ''}
      <div class="card"><div class="controls" id="controls"></div><div class="btns" id="btns" style="margin-top:6px"></div><div class="stat" id="stat" style="margin-top:6px"></div></div>
    </div>
    <div class="side">
      <div class="card"><div class="h">Step by step</div><div class="steps" id="steps"></div>
        <div class="nav"><button id="back">Back</button><button id="next" class="primary">Next step</button></div></div>
      <div class="card"><div class="h">The math for this step (live numbers)</div><div class="math" id="math"></div></div>
    </div>
  </div>
</div>`;
  const ctl = document.getElementById('controls');
  (cfg.controls || []).forEach(c => {
    SL.v[c.id] = c.value;
    const d = document.createElement('label'); d.className = 'ctl';
    d.innerHTML = `<span>${c.label}</span><input type="range" min="${c.min}" max="${c.max}" step="${c.step || 1}" value="${c.value}"><output></output>`;
    const inp = d.querySelector('input'), out = d.querySelector('output'), fmt = c.fmt || (x => x);
    out.textContent = fmt(c.value);
    inp.oninput = () => { SL.v[c.id] = +inp.value; out.textContent = fmt(+inp.value); if (cfg.onControl) cfg.onControl(c.id); SL.redraw(); };
    c.set = x => { inp.value = x; SL.v[c.id] = +x; out.textContent = fmt(+x); };
    ctl.appendChild(d);
  });
  SL.setControl = (id, x) => { const c = cfg.controls.find(k => k.id === id); if (c) c.set(x); };
  const bt = document.getElementById('btns');
  const addBtn = b => { const e = document.createElement('button'); e.textContent = b.label; if (b.primary) e.className = 'primary';
    if (b.toggle) e.setAttribute('aria-pressed', b.pressed ? 'true' : 'false'); e.onclick = () => b.onclick(e); bt.appendChild(e); return e; };
  if (cfg.play) {
    SL.playing = false;
    const pb = addBtn({ label: 'Play', primary: true, onclick: e => { SL.playing = !SL.playing; e.textContent = SL.playing ? 'Pause' : 'Play'; if (SL.playing) { last = 0; requestAnimationFrame(loop); } } });
    SL.stopPlay = () => { SL.playing = false; pb.textContent = 'Play'; };
    addBtn({ label: 'Reset', onclick: () => { SL.stopPlay(); cfg.reset && cfg.reset(); SL.redraw(); } });
    let last = 0;
    const loop = now => { if (!SL.playing) return; const dt = last ? Math.min(.05, (now - last) / 1000) : 0; last = now; cfg.play.tick(dt); SL.redraw(); requestAnimationFrame(loop); };
  }
  (cfg.buttons || []).forEach(addBtn);

  const view = document.getElementById('view'), cv = document.getElementById('cv');
  const ctx = cfg.view === '3d' ? new Scene3D(cv, view, cfg.orbit) : new Plot2D(cv);
  SL.ctx = ctx;
  if (cfg.view !== '3d' && cfg.drag) {     // drag handles: [{pos:()=>[x,y], panel:()=>Panel, set:(p)=>{}}]
    let h = null;
    const pt = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    const find = p => cfg.drag().find(d => { const pn = d.panel(); if (!pn) return false; const s = pn.S(d.pos()); return Math.hypot(s[0] - p[0], s[1] - p[1]) < 16; });
    cv.addEventListener('pointerdown', e => { h = find(pt(e)); if (h) cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove', e => { const p = pt(e); if (!h) { cv.style.cursor = find(p) ? 'grab' : 'default'; return; } h.set(h.panel().inv(...p)); SL.redraw(); });
    ['pointerup', 'pointercancel'].forEach(t => cv.addEventListener(t, () => h = null));
  }
  const stepsEl = document.getElementById('steps'), mathEl = document.getElementById('math'), statEl = document.getElementById('stat');
  const renderSteps = () => {
    stepsEl.innerHTML = cfg.steps.map((s, i) => `<button class="step" data-i="${i}" aria-current="${i === SL.st}"><span class="n">${i}</span><span><b>${s[0]}</b><span class="t">${s[1]}</span></span></button>`).join('');
    stepsEl.querySelectorAll('.step').forEach(b => b.onclick = () => SL.go(+b.dataset.i, false));
    document.getElementById('back').disabled = SL.st === 0; document.getElementById('next').disabled = SL.st === cfg.steps.length - 1;
  };
  let raf = 0;
  SL.go = (i, animate = true) => {
    SL.st = i; renderSteps(); cancelAnimationFrame(raf); cfg.onStep && cfg.onStep(i);
    if (!animate || matchMedia('(prefers-reduced-motion: reduce)').matches) { SL.anim = 1; SL.redraw(); return; }
    const t0 = performance.now(); const tk = now => { SL.anim = Math.min(1, (now - t0) / 750); SL.redraw(); if (SL.anim < 1) raf = requestAnimationFrame(tk); }; raf = requestAnimationFrame(tk);
  };
  document.getElementById('next').onclick = () => SL.go(SL.st + 1);
  document.getElementById('back').onclick = () => SL.go(SL.st - 1, false);
  let mathKey = '';
  SL.redraw = () => {
    if (cfg.view === '3d') { ctx.begin(); cfg.draw(ctx); ctx.end(); cfg.draw3dLabels && cfg.draw3dLabels(ctx); }
    else { if (!ctx.W) return; ctx.begin(); cfg.draw(ctx); }
    const html = cfg.math ? cfg.math(SL.st) : ''; if (html !== mathKey) { mathEl.innerHTML = html; mathKey = html; }
    if (cfg.stats) statEl.innerHTML = cfg.stats();
  };
  const size = () => { ctx.resize(); SL.redraw(); };
  new ResizeObserver(size).observe(cv);
  new MutationObserver(() => SL.redraw()).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => SL.redraw());
  document.addEventListener('keydown', e => { if (e.key === 'ArrowRight' && SL.st < cfg.steps.length - 1) SL.go(SL.st + 1); if (e.key === 'ArrowLeft' && SL.st > 0) SL.go(SL.st - 1, false); });
  cfg.setup && cfg.setup(ctx);
  renderSteps(); size();
};
})();
