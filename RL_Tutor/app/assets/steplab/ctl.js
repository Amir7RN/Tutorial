/* Control helpers for the systems-and-stability step labs: complex numbers,
   polynomials (coefficients highest power first), roots, transfer functions,
   step / frequency responses. Runs in the browser and under node. */
(function (root) {
const C = {};
/* complex numbers as [re, im] */
C.c = (re, im = 0) => [re, im];
C.cadd = (a, b) => [a[0] + b[0], a[1] + b[1]];
C.csub = (a, b) => [a[0] - b[0], a[1] - b[1]];
C.cmul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
C.cdiv = (a, b) => { const d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; };
C.cabs = a => Math.hypot(a[0], a[1]);
C.carg = a => Math.atan2(a[1], a[0]);
C.cexp = a => { const r = Math.exp(a[0]); return [r * Math.cos(a[1]), r * Math.sin(a[1])]; };
C.cscl = (a, k) => [a[0] * k, a[1] * k];
/* polynomials: [a_n, ..., a_0] */
C.peval = (p, s) => p.reduce((acc, a) => C.cadd(C.cmul(acc, s), [a, 0]), [0, 0]);
C.pevalr = (p, x) => p.reduce((acc, a) => acc * x + a, 0);
C.pmul = (p, q) => { const r = new Array(p.length + q.length - 1).fill(0); p.forEach((a, i) => q.forEach((b, j) => r[i + j] += a * b)); return r; };
C.padd = (p, q) => { const n = Math.max(p.length, q.length), P = Array(n - p.length).fill(0).concat(p), Q = Array(n - q.length).fill(0).concat(q); return P.map((a, i) => a + Q[i]); };
C.pscl = (p, k) => p.map(a => a * k);
C.fromRoots = rs => {           // rs: list of complex roots (conjugates included) → real coefficients
  let p = [[1, 0]];
  rs.forEach(r => { const q = new Array(p.length + 1).fill(null).map(() => [0, 0]);
    p.forEach((a, i) => { q[i] = C.cadd(q[i], a); q[i + 1] = C.csub(q[i + 1], C.cmul(a, r)); }); p = q; });
  return p.map(a => a[0]);
};
/* all roots by Durand–Kerner */
C.roots = p => {
  while (p.length > 1 && Math.abs(p[0]) < 1e-14) p = p.slice(1);
  const n = p.length - 1; if (n < 1) return [];
  const a = p.map(x => x / p[0]);
  let z = [...Array(n)].map((_, k) => { let w = [1, 0]; for (let i = 0; i < k; i++) w = C.cmul(w, [.4, .9]); return w; });
  for (let it = 0; it < 500; it++) {
    let delta = 0;
    z = z.map((zi, i) => { let den = [1, 0]; z.forEach((zj, j) => { if (i !== j) den = C.cmul(den, C.csub(zi, zj)); });
      const step = C.cdiv(C.peval(a, zi), den); delta = Math.max(delta, C.cabs(step)); return C.csub(zi, step); });
    if (delta < 1e-13) break;
  }
  return z.map(r => [Math.abs(r[0]) < 1e-9 ? 0 : r[0], Math.abs(r[1]) < 1e-9 ? 0 : r[1]]).sort((x, y) => y[0] - x[0] || y[1] - x[1]);
};
/* transfer function G = num/den, optional delay T (seconds) */
C.tf = (num, den, delay = 0) => ({ num, den, delay });
C.freq = (G, w) => { const s = [0, w]; let v = C.cdiv(C.peval(G.num, s), C.peval(G.den, s)); if (G.delay) v = C.cmul(v, C.cexp([0, -w * G.delay])); return v; };
C.db = x => 20 * Math.log10(x);
C.unwrapPhase = ph => { const out = [ph[0]]; for (let i = 1; i < ph.length; i++) { let d = ph[i] - ph[i - 1]; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI; out.push(out[i - 1] + d); } return out; };
C.logspace = (a, b, n) => [...Array(n)].map((_, i) => Math.pow(10, a + (b - a) * i / (n - 1)));
/* closed loop of a unity-feedback loop L = num/den: T = num/(den + num) */
C.feedback = L => ({ num: L.num, den: C.padd(L.den, L.num), delay: 0 });
/* simulate y for input u(t) (function) through a proper G (no delay) with RK4 on
   the controllable canonical form. Returns [[t, y, u], ...]. */
C.sim = (G, u, T, dt = 1e-3, x0) => {
  const den = G.den.map(x => x / G.den[0]), n = den.length - 1;
  let num = G.num.map(x => x / G.den[0]); num = Array(n + 1 - num.length).fill(0).concat(num);
  const d = num[0], b = num.slice(1).map((x, i) => x - d * den[i + 1]);       // strictly proper part
  let x = x0 ? x0.slice() : new Array(n).fill(0);
  const f = (x, uu) => { const dx = new Array(n); for (let i = 0; i < n - 1; i++) dx[i] = x[i + 1];
    dx[n - 1] = uu - den.slice(1).reduce((acc, a, i) => acc + a * x[n - 1 - i], 0); return dx; };
  const out = (x, uu) => b.reduce((acc, bi, i) => acc + bi * x[n - 1 - i], 0) + d * uu;
  const res = []; const N = Math.round(T / dt);
  for (let k = 0; k <= N; k++) {
    const t = k * dt, uu = u(t); res.push([t, out(x, uu), uu]);
    const k1 = f(x, uu), k2 = f(x.map((v, i) => v + dt / 2 * k1[i]), u(t + dt / 2)), k3 = f(x.map((v, i) => v + dt / 2 * k2[i]), u(t + dt / 2)), k4 = f(x.map((v, i) => v + dt * k3[i]), u(t + dt));
    x = x.map((v, i) => v + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]));
  }
  return res;
};
C.step = (G, T, dt) => C.sim(G, t => 1, T, dt);
/* step metrics from a simulated response */
C.metrics = (res, yf) => {
  yf = yf === undefined ? res[res.length - 1][1] : yf;
  let peak = -Infinity, tp = 0, t10 = null, t90 = null, ts = 0;
  res.forEach(([t, y]) => { if (y > peak) { peak = y; tp = t; } if (t10 === null && y >= .1 * yf) t10 = t; if (t90 === null && y >= .9 * yf) t90 = t; if (Math.abs(y - yf) > .02 * Math.abs(yf)) ts = t; });
  return { yf, peak, tp, os: yf ? Math.max(0, (peak - yf) / yf * 100) : 0, tr: t90 !== null && t10 !== null ? t90 - t10 : NaN, ts };
};
/* margins of a loop L over a log grid: gain crossover / phase margin, phase crossover / gain margin */
C.margins = (L, w0 = -2, w1 = 4, n = 4000) => {
  const ws = C.logspace(w0, w1, n), H = ws.map(w => C.freq(L, w)), mag = H.map(C.cabs), ph = C.unwrapPhase(H.map(C.carg));
  let wc = null, pm = null, w180 = null, gm = null;
  for (let i = 1; i < n; i++) {
    if (wc === null && mag[i - 1] >= 1 && mag[i] < 1) { const t = (Math.log(mag[i - 1])) / (Math.log(mag[i - 1]) - Math.log(mag[i])); wc = ws[i - 1] * Math.pow(ws[i] / ws[i - 1], t); pm = 180 + (ph[i - 1] + t * (ph[i] - ph[i - 1])) * 180 / Math.PI; }
    if (w180 === null && ph[i - 1] > -Math.PI && ph[i] <= -Math.PI) { const t = (ph[i - 1] + Math.PI) / (ph[i - 1] - ph[i]); w180 = ws[i - 1] * Math.pow(ws[i] / ws[i - 1], t); const m = mag[i - 1] * Math.pow(mag[i] / mag[i - 1], t); gm = -C.db(m); }
  }
  return { ws, mag, ph, wc, pm, w180, gm };
};
/* Routh array for a real polynomial: returns rows and the sign changes of the first column */
C.routh = p => {
  const n = p.length - 1, rows = [p.filter((_, i) => i % 2 === 0), p.filter((_, i) => i % 2 === 1)];
  const w = Math.ceil((n + 1) / 2); rows.forEach(r => { while (r.length < w) r.push(0); });
  for (let k = 2; k <= n; k++) {
    const a = rows[k - 2], b = rows[k - 1].slice(); if (Math.abs(b[0]) < 1e-12) b[0] = 1e-9;
    const r = []; for (let j = 0; j < w - 1; j++) r.push((b[0] * a[j + 1] - a[0] * b[j + 1]) / b[0]); r.push(0); rows.push(r);
    rows[k - 1] = b;
  }
  const col = rows.map(r => r[0]); let changes = 0; for (let i = 1; i < col.length; i++) if (Math.sign(col[i]) !== Math.sign(col[i - 1])) changes++;
  return { rows, col, changes };
};
root.CTL = C;
if (typeof module !== 'undefined') module.exports = C;
})(typeof window !== 'undefined' ? window : globalThis);
