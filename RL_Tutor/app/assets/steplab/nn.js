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
  net.forEach(l => {
    const prev = a[a.length - 1], zz = l.b.map((b, j) => b + prev.reduce((s, xi, i) => s + xi * l.W[i][j], 0));
    z.push(zz); a.push(zz.map(NN.act[l.act].f));
  });
  return { a, z };
};
/* one sample backward from dL/dy: deltas δk, gW = aᵀδ, gb = δ, dx = δWᵀ */
NN.backward = (net, c, dy) => {
  let d = dy.slice(); const gW = [], gb = [], delta = [], dA = [];
  for (let k = net.length - 1; k >= 0; k--) {
    const l = net[k]; dA[k] = d.slice();
    const dz = d.map((g, j) => g * NN.act[l.act].d(c.z[k][j])); delta[k] = dz;
    gW[k] = c.a[k].map(xi => dz.map(g => xi * g)); gb[k] = dz.slice();
    d = l.W.map(row => row.reduce((s, w, j) => s + w * dz[j], 0));
  }
  return { gW, gb, delta, dA, dx: d };
};
NN.step = (net, g, eta) => net.forEach((l, k) => { l.W.forEach((r, i) => r.forEach((_, j) => r[j] -= eta * g.gW[k][i][j])); l.b.forEach((_, j) => l.b[j] -= eta * g.gb[k][j]); });
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
    P.poly([[cx - w * .32, 0], [cx + w * .32, 0], [cx + w * .32, Math.max(y0, Math.min(y1, v))], [cx - w * .32, Math.max(y0, Math.min(y1, v))]], cl, 1.5, null, cl, true);
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
