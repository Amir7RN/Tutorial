/* Small neural-network helpers for the step labs (pages 81-95).
   Same conventions as rlcore/deeprl.py: x is a row, z = xW + b, W is n_in × n_out,
   backward(dout) fills gW, gb (batch means) and returns dL/dx = δWᵀ. */
(function () {
const NN = window.NN = {};
NN.act = {
  tanh: { f: Math.tanh, d: z => 1 - Math.tanh(z) ** 2 },
  relu: { f: z => Math.max(0, z), d: z => z > 0 ? 1 : 0 },
  sigmoid: { f: z => 1 / (1 + Math.exp(-z)), d: z => { const s = 1 / (1 + Math.exp(-z)); return s * (1 - s); } },
  leaky: { f: z => z > 0 ? z : .01 * z, d: z => z > 0 ? 1 : .01 },
  linear: { f: z => z, d: () => 1 },
};
/* deterministic random numbers, so every lab opens on the same example */
NN.rng = (seed = 1) => () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
NN.gauss = r => { const u = Math.max(1e-12, r()), v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
/* layer with weights uniform in ±scale (default √(1/n_in), the tutor's init) */
NN.layer = (nin, nout, act, r, scale) => {
  const s = scale === undefined ? Math.sqrt(1 / nin) : scale;
  return { act, W: [...Array(nin)].map(() => [...Array(nout)].map(() => (2 * r() - 1) * s)), b: [...Array(nout)].map(() => (2 * r() - 1) * s) };
};
NN.net = (sizes, acts, seed = 3, lastScale) => {
  const r = NN.rng(seed);
  return sizes.slice(1).map((n, k) => NN.layer(sizes[k], n, acts[k], r, k === sizes.length - 2 ? lastScale : undefined));
};
NN.clone = net => net.map(l => ({ act: l.act, W: l.W.map(r => r.slice()), b: l.b.slice() }));
/* one sample: returns {a:[x, a1, ..., y], z:[z1, ..., zL]} */
NN.forward = (net, x) => {
  const a = [x.slice()], z = [];
  for (const l of net) {
    const prev = a[a.length - 1], n = l.b.length, zz = l.b.slice(), F = NN.act[l.act].f;
    for (let i = 0; i < prev.length; i++) { const xi = prev[i], Wi = l.W[i]; for (let j = 0; j < n; j++) zz[j] += xi * Wi[j]; }
    z.push(zz); const aa = new Array(n); for (let j = 0; j < n; j++) aa[j] = F(zz[j]); a.push(aa);
  }
  return { a, z };
};
/* one sample backward from dL/dy: deltas δk, gW = aᵀδ, gb = δ, dx = δWᵀ */
NN.backward = (net, c, dy) => {
  let d = dy.slice(); const gW = [], gb = [], delta = [], dA = [];
  for (let k = net.length - 1; k >= 0; k--) {
    const l = net[k], D = NN.act[l.act].d, n = d.length, zk = c.z[k], xk = c.a[k]; dA[k] = d;
    const dz = new Array(n), ak = c.a[k + 1];
    if (l.act === 'tanh') for (let j = 0; j < n; j++) dz[j] = d[j] * (1 - ak[j] * ak[j]); else for (let j = 0; j < n; j++) dz[j] = d[j] * D(zk[j]);
    delta[k] = dz;
    gW[k] = xk.map(xi => { const r = new Array(n); for (let j = 0; j < n; j++) r[j] = xi * dz[j]; return r; }); gb[k] = dz.slice();
    d = l.W.map(row => { let s = 0; for (let j = 0; j < n; j++) s += row[j] * dz[j]; return s; });
  }
  return { gW, gb, delta, dA, dx: d };
};
NN.step = (net, g, eta) => net.forEach((l, k) => { l.W.forEach((r, i) => r.forEach((_, j) => r[j] -= eta * g.gW[k][i][j])); l.b.forEach((_, j) => l.b[j] -= eta * g.gb[k][j]); });
/* gradient accumulator: add(g, weight) sums one sample's gradients; .g is the result */
NN.acc = net => { const A = { gW: net.map(l => l.W.map(r => r.map(() => 0))), gb: net.map(l => l.b.map(() => 0)) };
  A.add = (g, w) => { for (let k = 0; k < g.gW.length; k++) { const M = g.gW[k], T = A.gW[k]; for (let i = 0; i < M.length; i++) for (let j = 0; j < M[i].length; j++) T[i][j] += w * M[i][j];
    for (let j = 0; j < g.gb[k].length; j++) A.gb[k][j] += w * g.gb[k][j]; } }; return A; };
/* gradients averaged over a batch: items [{x, dy}] -> mean gradients and per-item dx */
NN.batchGrad = (net, items) => {
  const A = NN.acc(net), dxs = [];
  items.forEach(({ x, dy }) => { const c = NN.forward(net, x), g = NN.backward(net, c, dy); dxs.push(g.dx); A.add(g, 1 / items.length); });
  return { gW: A.gW, gb: A.gb, dxs };
};
/* Adam, as on page 80 / rlcore: state is created on first use */
NN.adam = (net, g, lr, S) => {
  if (!S.t) { S.t = 0; S.m = net.map(l => ({ W: l.W.map(r => r.map(() => 0)), b: l.b.map(() => 0) })); S.v = net.map(l => ({ W: l.W.map(r => r.map(() => 0)), b: l.b.map(() => 0) })); }
  S.t++; const b1 = .9, b2 = .999, c1 = 1 - Math.pow(b1, S.t), c2 = 1 - Math.pow(b2, S.t);
  const upd = (P, G, M, V, i, j) => { M[i][j] = b1 * M[i][j] + (1 - b1) * G; V[i][j] = b2 * V[i][j] + (1 - b2) * G * G; P[i][j] -= lr * (M[i][j] / c1) / (Math.sqrt(V[i][j] / c2) + 1e-8); };
  net.forEach((l, k) => { l.W.forEach((r, i) => r.forEach((_, j) => upd(l.W, g.gW[k][i][j], S.m[k].W, S.v[k].W, i, j)));
    const bw = [l.b], bm = [S.m[k].b], bv = [S.v[k].b]; l.b.forEach((_, j) => upd(bw, g.gb[k][j], bm, bv, 0, j)); });
};
/* The one-step toy of pages 89-90: r = −(a − g(s))², so Q*(s,a) = −(a − g(s))².
   A real DDPG (actor 1→16→16→1 tanh, critic 2→20→20→1, Adam, replay, batch 16). */
NN.toy = {
  g: s => .8 * Math.sin(Math.PI * s / 2),
  Qstar: (s, a) => -((a - NN.toy.g(s)) ** 2),
  fresh() {
    const A = { actor: NN.net([1, 16, 16, 1], ['tanh', 'tanh', 'tanh'], 5, 3e-3), critic: NN.net([2, 20, 20, 1], ['tanh', 'tanh', 'linear'], 9, 3e-3), sa: {}, sc: {}, buf: [] };
    A.mu = s => NN.forward(A.actor, [s]).a[3][0]; A.Q = (s, a) => NN.forward(A.critic, [s, a]).a[3][0];
    A.dQda = (s, a) => NN.backward(A.critic, NN.forward(A.critic, [s, a]), [1]).dx[1];
    return A;
  },
  train(eps, sig) {
    const AG = NN.toy.fresh(), r = NN.rng(77), last = []; let closs = 0;
    for (let e = 0; e < eps; e++) {
      const s = 2 * r() - 1, a = Math.max(-1, Math.min(1, AG.mu(s) + sig * NN.gauss(r)));
      AG.buf.push([s, a, NN.toy.Qstar(s, a)]); if (AG.buf.length > 5000) AG.buf.shift(); last.push(NN.toy.Qstar(s, AG.mu(s))); if (last.length > 100) last.shift();
      if (AG.buf.length < 16) continue;
      const B = [...Array(16)].map(() => AG.buf[Math.floor(r() * AG.buf.length)]);
      /* y = r (one-step episodes: d = 1); critic MSE */
      const gc = NN.acc(AG.critic), ga = NN.acc(AG.actor); let L = 0;
      B.forEach(([s, a, y]) => { const c = NN.forward(AG.critic, [s, a]), q = c.a[3][0]; L += (q - y) ** 2 / 16; gc.add(NN.backward(AG.critic, c, [2 * (q - y)]), 1 / 16); });
      NN.adam(AG.critic, gc, 2e-3, AG.sc); closs = L;
      /* dQ/da through the critic to its action input; −dQ/da seeds the actor */
      B.forEach(([s]) => { const ca = NN.forward(AG.actor, [s]), cc = NN.forward(AG.critic, [s, ca.a[3][0]]), dq = NN.backward(AG.critic, cc, [1]).dx[1];
        ga.add(NN.backward(AG.actor, ca, [-dq]), 1 / 16); });
      NN.adam(AG.actor, ga, 1e-3, AG.sa);
    }
    const ss = [...Array(41)].map((_, i) => -1 + i / 20);
    AG.log = { eps, sig, closs, meanR: last.reduce((x, y) => x + y, 0) / last.length, err: ss.reduce((x, s) => x + Math.abs(AG.mu(s) - NN.toy.g(s)), 0) / ss.length };
    return AG;
  },
};
NN.softmax = (z, T = 1) => { const m = Math.max(...z), e = z.map(v => Math.exp((v - m) / T)), s = e.reduce((a, b) => a + b, 0); return e.map(v => v / s); };
NN.nParams = sizes => sizes.slice(1).reduce((s, n, k) => s + sizes[k] * n + n, 0);
NN.e = (x, d = 2) => Math.abs(x) < 1e-300 ? '0' : x.toExponential(d);
/* draw a fully connected net in panel P (bounds any). sizes: [3,4,4,2].
   o: {W:[matrices] for edge colour/width, vals:[arrays] node values, hl: layer index to highlight,
       names:[labels], edge:(k,i,j)=>colour|null override, x0,x1,y0,y1} -> node positions */
NN.draw = (P, sizes, o = {}) => {
  const [bx0, bx1, by0, by1] = P.b, x0 = o.x0 ?? bx0 + (bx1 - bx0) * .08, x1 = o.x1 ?? bx1 - (bx1 - bx0) * .08;
  const y0 = o.y0 ?? by0 + (by1 - by0) * .12, y1 = o.y1 ?? by1 - (by1 - by0) * .1;
  const pos = sizes.map((n, k) => [...Array(n)].map((_, i) => [x0 + (x1 - x0) * k / (sizes.length - 1), n === 1 ? (y0 + y1) / 2 : y1 - (y1 - y0) * i / (n - 1)]));
  for (let k = 0; k < sizes.length - 1; k++) for (let i = 0; i < sizes[k]; i++) for (let j = 0; j < sizes[k + 1]; j++) {
    const w = o.W ? o.W[k][i][j] : .5, ov = o.edge && o.edge(k, i, j);
    if (ov === false) continue;
    P.line(pos[k][i], pos[k + 1][j], ov || (w >= 0 ? '--c' : '--bad'), Math.max(.6, Math.min(5, Math.abs(w) * 3.2)));
  }
  pos.forEach((L, k) => L.forEach((p, i) => {
    const v = o.vals && o.vals[k] ? o.vals[k][i] : null;
    P.dot(p, 11, o.hl === k ? '--a' : '--grey', true);
    if (v !== null && v !== undefined) P.text(p, SL.f(v, 2), '--ink', 0, 4, { size: 10, align: 'center' });
  }));
  if (o.names) o.names.forEach((s, k) => P.text([pos[k][0][0], by0], s, '--muted', 0, -4, { size: 11, align: 'center' }));
  return pos;
};
/* little bar chart in a panel: vals, colours, labels */
NN.bars = (P, vals, o = {}) => {
  const [x0, x1, y0, y1] = P.b, n = vals.length, w = (x1 - x0) / n;
  if (y0 < 0) P.line([x0, 0], [x1, 0], '--grey', 1);
  vals.forEach((v, i) => {
    const cx = x0 + w * (i + .5), cl = o.cols ? o.cols[i] : (v >= 0 ? '--a' : '--bad');
    const b0 = y0 > 0 ? y0 : y1 < 0 ? y1 : 0; P.poly([[cx - w * .32, b0], [cx + w * .32, b0], [cx + w * .32, Math.max(y0, Math.min(y1, v))], [cx - w * .32, Math.max(y0, Math.min(y1, v))]], cl, 1.5, null, cl, true);
    if (o.labels) P.text([cx, y0], o.labels[i], '--muted', 0, -4, { size: 11, align: 'center' });
    if (o.show !== false) P.text([cx, Math.max(y0, Math.min(y1, v))], SL.f(v, o.d ?? 2), '--ink', 0, v >= 0 ? -5 : 14, { size: 11, align: 'center' });
  });
};
/* text block in a [0,1]² panel: lines [[text, colour]] */
NN.lines = (P, rows, o = {}) => {
  const top = o.top ?? .14, gap = o.gap ?? Math.min(.16, .8 / Math.max(1, rows.length));
  rows.forEach(([s, cl], i) => P.label(P.x + P.w * (o.x ?? .03), P.y + P.h * (top + gap * i), s, cl || '--ink', { mono: o.mono !== false, size: o.size || 12 }));
};
})();
