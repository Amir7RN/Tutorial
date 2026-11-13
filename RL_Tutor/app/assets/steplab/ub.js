/* Upper-body balance: the planar chain (legs, torso, arms) on a pinned ankle.
   A line-for-line port of ctrlcore/upperbody.py, tested against it
   (tests/test_upperbody.py runs this file under node). Same conventions:
   x forward, y up, pitch positive = top of the link moves forward, q relative,
   q = 0 standing straight with the arms hanging. */
(function (root) {
const UB = {};
const G0 = 9.81;

/* ---------------- tiny linear algebra ---------------- */
const zeros = (r, c) => Array.from({ length: r }, () => new Array(c).fill(0));
const eye = n => zeros(n, n).map((row, i) => (row[i] = 1, row));
const T = A => A[0].map((_, j) => A.map(r => r[j]));
const mul = (A, B) => A.map(r => B[0].map((_, j) => r.reduce((s, v, k) => s + v * B[k][j], 0)));
const mv = (A, x) => A.map(r => r.reduce((s, v, k) => s + v * x[k], 0));
const add = (A, B) => A.map((r, i) => r.map((v, j) => v + B[i][j]));
const sub = (A, B) => A.map((r, i) => r.map((v, j) => v - B[i][j]));
const scl = (A, s) => A.map(r => r.map(v => v * s));
const vadd = (a, b) => a.map((v, i) => v + b[i]);
const vsub = (a, b) => a.map((v, i) => v - b[i]);
const vscl = (a, s) => a.map(v => v * s);
const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
function solve(A, b) {               // Gaussian elimination with partial pivoting
  const n = A.length, M = A.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]];
    const d = M[c][c]; if (Math.abs(d) < 1e-14) throw new Error('singular');
    for (let r = 0; r < n; r++) { if (r === c) continue; const f = M[r][c] / d; if (!f) continue; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  return M.map((r, i) => r[n] / r[i]);
}
function inv(A) { const n = A.length, I = eye(n), cols = I.map((_, j) => solve(A, I.map(r => r[j]))); return T(cols); }
function lstsq(A, b) {               // min ||A x - b||, via the normal equations (tiny, well-scaled)
  const At = T(A), N = mul(At, A), n = N.length;
  for (let i = 0; i < n; i++) N[i][i] += 1e-12;
  return solve(N, mv(At, b));
}
Object.assign(UB, { zeros, eye, T, mul, mv, add, sub, scl, solve, inv, lstsq });

/* ---------------- the three planes ---------------- */
const L = (name, joint, m, len, r, I, off = 0, lo = -1e9, hi = 1e9) => ({ name, joint, m, L: len, r, I, off, lo, hi });
UB.planes = {
  sagittal: { plane: 'sagittal', g: G0, foot: 0.10, links: [
    L('legs + pelvis', 'ankle pitch', 17.0, 0.72, 0.42, 0.73),
    L('torso + head', 'waist pitch', 11.0, 0.36, 0.20, 0.15, 0, -0.52, 0.52),
    L('upper arms (x2)', 'shoulder pitch', 3.2, 0.22, 0.11, 0.013, Math.PI, -3.0, 2.6),
    L('forearms + hands (x2)', 'elbow pitch', 2.8, 0.26, 0.14, 0.016, 0, -2.0, 0.3)] },
  frontal: { plane: 'frontal', g: G0, foot: 0.10, links: [
    L('legs + pelvis', 'ankle roll', 17.0, 0.72, 0.42, 0.73),
    L('torso + head', 'waist roll', 11.0, 0.36, 0.20, 0.15, 0, -0.52, 0.52),
    L('arms, straight (x2)', 'shoulder roll', 6.0, 0.48, 0.2267, 0.1224, Math.PI, -1.6, 1.6)] },
  transverse: { plane: 'transverse', g: 0, foot: 0.10, links: [
    L('legs + pelvis (seen from above)', 'feet on the floor (yaw)', 17.0, 0.0, 0.0, 0.25),
    L('torso (spine to shoulder)', 'waist yaw', 11.0, 0.16, 0.0, 0.20, 0, -2.6, 2.6),
    L('arms, held out forward (x2)', 'shoulder yaw', 6.0, 0.48, 0.2267, 0.1224, -Math.PI / 2, -1.6, 1.6)] },
};
UB.mtot = model => model.links.reduce((s, l) => s + l.m, 0);
UB.tauAnkleMax = model => model.g ? UB.mtot(model) * model.g * model.foot : 0;
const pc = (ax, ay, bx, by) => ay * bx - ax * by;      // pitch-sense cross product
UB.pcross = pc;

/* ---------------- the core: everything at one state ---------------- */
UB.core = function (model, q, qd, opt = {}) {
  const links = model.links, n = links.length, momentum = opt.momentum !== false, about = opt.about;
  const phi = []; let s = 0;
  for (let i = 0; i < n; i++) { s += q[i] + links[i].off; phi.push(s); }
  const ux = phi.map(Math.sin), uy = phi.map(Math.cos);
  const px = [0], py = [0], cx = [], cy = [];
  links.forEach((l, i) => { cx.push(px[i] + l.r * ux[i]); cy.push(py[i] + l.r * uy[i]); px.push(px[i] + l.L * ux[i]); py.push(py[i] + l.L * uy[i]); });
  const Jx = zeros(n, n), Jy = zeros(n, n);
  for (let i = 0; i < n; i++) for (let j = 0; j <= i; j++) { Jx[i][j] = cy[i] - py[j]; Jy[i][j] = -(cx[i] - px[j]); }
  const M = zeros(n, n);
  links.forEach((l, i) => { for (let a = 0; a <= i; a++) for (let b = a; b <= i; b++) {
    const v = l.m * (Jx[i][a] * Jx[i][b] + Jy[i][a] * Jy[i][b]) + l.I; M[a][b] += v; if (a !== b) M[b][a] += v; } });
  const g = new Array(n).fill(0);
  if (model.g) for (let j = 0; j < n; j++) { let t = 0; for (let i = j; i < n; i++) t += links[i].m * (cx[i] - px[j]); g[j] = -model.g * t; }
  const out = { phi, p: px.map((x, i) => [x, py[i]]), c: cx.map((x, i) => [x, cy[i]]), Jx, Jy, M, g };
  if (!qd) return out;
  const w = []; s = 0; for (let i = 0; i < n; i++) { s += qd[i]; w.push(s); }
  const pdx = [0], pdy = [0];
  for (let j = 1; j <= n; j++) { let a = 0, b = 0; for (let k = 0; k < j; k++) { a += qd[k] * (py[j] - py[k]); b += -qd[k] * (px[j] - px[k]); } pdx.push(a); pdy.push(b); }
  const vx = [], vy = [], ax = [], ay = [];
  for (let i = 0; i < n; i++) {
    let vxi = 0, vyi = 0; for (let j = 0; j <= i; j++) { vxi += qd[j] * Jx[i][j]; vyi += qd[j] * Jy[i][j]; }
    vx.push(vxi); vy.push(vyi);
    let axi = 0, ayi = 0; for (let j = 0; j <= i; j++) { axi += qd[j] * (vyi - pdy[j]); ayi += -qd[j] * (vxi - pdx[j]); }
    ax.push(axi); ay.push(ayi);
  }
  const cvec = new Array(n).fill(0);
  for (let j = 0; j < n; j++) { let t = 0; for (let i = j; i < n; i++) t += links[i].m * (Jx[i][j] * ax[i] + Jy[i][j] * ay[i]); cvec[j] = t; }
  Object.assign(out, { qd, w, v: vx.map((x, i) => [x, vy[i]]), a: ax.map((x, i) => [x, ay[i]]), cvec });
  if (!momentum) return out;
  const mt = UB.mtot(model);
  let xc = 0, yc = 0, vcx = 0, vcy = 0;
  links.forEach((l, i) => { xc += l.m * cx[i]; yc += l.m * cy[i]; vcx += l.m * vx[i]; vcy += l.m * vy[i]; });
  xc /= mt; yc /= mt; vcx /= mt; vcy /= mt;
  let ox, oy, vox, voy;
  if (about) { ox = about[0]; oy = about[1]; vox = voy = 0; } else { ox = xc; oy = yc; vox = vcx; voy = vcy; }
  const A = zeros(3, n), A_O = zeros(3, n), bias = [0, 0, 0], link_H = new Array(n).fill(0); let H_O = 0;
  links.forEach((l, i) => {
    const dx = cx[i] - ox, dy = cy[i] - oy;
    for (let j = 0; j <= i; j++) {
      A[0][j] += l.m * Jx[i][j]; A[1][j] += l.m * Jy[i][j];
      A[2][j] += l.I + l.m * pc(dx, dy, Jx[i][j], Jy[i][j]);
      A_O[2][j] += l.I + l.m * pc(cx[i], cy[i], Jx[i][j], Jy[i][j]);
    }
    bias[0] += l.m * ax[i]; bias[1] += l.m * ay[i];
    bias[2] += l.m * (pc(vx[i] - vox, vy[i] - voy, vx[i], vy[i]) + pc(dx, dy, ax[i], ay[i]));
    link_H[i] = l.I * w[i] + l.m * pc(cx[i], cy[i], vx[i], vy[i]); H_O += link_H[i];
  });
  A_O[0] = A[0].slice(); A_O[1] = A[1].slice();
  Object.assign(out, { xc: [xc, yc], vc: [vcx, vcy], A, bias, A_O, H_O, link_H, h: mv(A, qd) });
  return out;
};
UB.pointJacobian = function (model, q, k) {
  const c = UB.core(model, q), n = model.links.length, J = zeros(2, n);
  for (let j = 0; j < Math.min(k, n); j++) { const dx = c.p[k][0] - c.p[j][0], dy = c.p[k][1] - c.p[j][1]; J[0][j] = dy; J[1][j] = -dx; }
  return J;
};
UB.energy = function (model, q, qd) {
  const k = UB.core(model, q, qd, { momentum: false });
  return { T: 0.5 * dot(qd, mv(k.M, qd)), V: model.links.reduce((s, l, i) => s + l.m * model.g * k.c[i][1], 0) };
};
UB.selection = (n, free) => { const S = zeros(n, free.length); free.forEach((j, k) => S[j][k] = 1); return S; };
UB.locked = function (model, q, qd, free) {
  const S = UB.selection(model.links.length, free), St = T(S), k = UB.core(model, q, qd);
  return { S, M: mul(mul(St, k.M), S), c: mv(St, k.cvec), g: mv(St, k.g), A: mul(k.A, S), A_O: mul(k.A_O, S) };
};

/* ---------------- gains ---------------- */
UB.gains = (o = {}) => Object.assign({
  task: 'dcm', k_dcm: 3, kp_lean: 40, kd_lean: 12, w_task: 1, kp_post: 40, kd_post: 10, lam_post: 0.05,
  tau_max: [0, 88, 50, 50], ankle_k: 300, ankle_b: 30, law: 'lqr',
  kappa_p: 0.15, kappa_d: 0.08, k_x: 1500, b_x: 220,
  lean_max: 0.1, posture_max: 0.5, lean_rate_max: 1.0, posture_rate_max: 5.0 }, o);
UB.ankleTorque = function (model, q, qd, g) {
  const t = -g.ankle_k * q[0] - g.ankle_b * qd[0], lim = UB.tauAnkleMax(model);
  return Math.max(-lim, Math.min(lim, t));
};
const clip = (v, lim) => Math.max(-lim, Math.min(lim, v));
const defaultActive = (n, active) => (active || Array.from({ length: n - 1 }, (_, i) => i + 1)).filter(i => i > 0 && i < n);

/* ---------------- the momentum law (resolved momentum, box QP) ---------------- */
UB.boxQP = function (R, r0, lo, hi) {
  const n = R[0].length, res = x => vadd(mv(R, x), r0), cost = x => dot(res(x), res(x));
  let x = lstsq(R, vscl(r0, -1));
  if (x.every((v, i) => v >= lo[i] - 1e-9 && v <= hi[i] + 1e-9)) return { x: x.map((v, i) => Math.max(lo[i], Math.min(hi[i], v))), tried: 0 };
  let best = x.map((v, i) => Math.max(lo[i], Math.min(hi[i], v))), bestCost = null, tried = 0;
  const total = Math.pow(3, n);
  for (let code = 1; code < total; code++) {
    const states = []; let c = code; for (let i = 0; i < n; i++) { states.push(c % 3); c = Math.floor(c / 3); }
    tried++;
    const y = states.map((st, i) => st === 1 ? lo[i] : hi[i]);
    const free = [], fixed = [];
    states.forEach((st, i) => (st === 0 ? free : fixed).push(i));
    if (free.length) {
      const rhs = r0.map((v, k) => -(v + fixed.reduce((s, i) => s + R[k][i] * y[i], 0)));
      const Rf = R.map(r => free.map(i => r[i]));
      const xf = lstsq(Rf, rhs);
      let ok = true; free.forEach((i, k) => { y[i] = xf[k]; if (xf[k] < lo[i] - 1e-9 || xf[k] > hi[i] + 1e-9) ok = false; });
      if (!ok) continue;
    }
    const cst = cost(y);
    if (bestCost === null || cst < bestCost) { best = y; bestCost = cst; }
  }
  return { x: best, tried };
};
UB.dcm = function (model, k) {
  const w = Math.sqrt(model.g / Math.max(k.xc[1], 0.05));
  return { xi: k.xc[0] + k.vc[0] / w, w };
};
UB.momentumStep = function (model, q, qd, g, active, qHome, detail) {
  const n = model.links.length;
  active = defaultActive(n, active);
  qHome = qHome || new Array(n).fill(0);
  const k = UB.core(model, q, qd), M = k.M, cg = k.cvec.map((v, i) => v + k.g[i]), A = k.A, b = k.bias;
  const xc = k.xc, vc = k.vc, H = dot(A[2], qd), tau1 = UB.ankleTorque(model, q, qd, g);
  const tau = new Array(n).fill(0); tau[0] = tau1;
  if (!active.length) return detail ? { tau, target: 0, saturated: 0, xi: 0 } : tau;
  const u = active, nu = u.length;
  const e0 = new Array(n).fill(0); e0[0] = (tau1 - cg[0]) / M[0][0];
  const E = zeros(n, nu); u.forEach((j, kk) => { E[0][kk] = -M[0][j] / M[0][0]; E[j][kk] = 1; });
  let xi = 0, target, row, off;
  if (g.task === 'dcm' && model.g) {
    const d = UB.dcm(model, k); xi = d.xi;
    const pCmp = xi * (1 + g.k_dcm / d.w);
    target = UB.mtot(model) * model.g * pCmp + tau1;
    row = mul(A, E)[2]; off = mv(A, e0)[2] + b[2];
  } else {
    target = -g.kp_lean * q[0] - g.kd_lean * qd[0];
    row = E[0].slice(); off = e0[0];
  }
  const qddPost = u.map(j => -g.kp_post * (q[j] - qHome[j]) - g.kd_post * qd[j]);
  const ME = mul(M, E), Tm = u.map(j => ME[j]), Me0 = mv(M, e0), t0 = u.map(j => Me0[j] + cg[j]);
  const Tinv = inv(Tm), sw = Math.sqrt(g.w_task), sl = Math.sqrt(g.lam_post);
  const rT = mv(T(Tinv), row);                       // row @ Tinv
  const R = [rT.map(v => v * sw), ...scl(Tinv, sl)];
  const Tinvt0 = mv(Tinv, t0);
  const r0 = [sw * (off - target - dot(rT, t0)), ...qddPost.map((v, i) => sl * (-Tinvt0[i] - v))];
  const lim = u.map(j => g.tau_max[j]);
  const { x: tauU, tried } = UB.boxQP(R, r0, lim.map(v => -v), lim);
  u.forEach((j, kk) => tau[j] = tauU[kk]);
  if (!detail) return tau;
  const qddU = mv(Tinv, vsub(tauU, t0)), qdd = vadd(mv(E, qddU), e0);
  return { tau, target, achieved: dot(row, qddU) + off, qdd, H, xc, vc, xi, row, off, T: Tm, t0, saturated: tried, tau_unclipped: lstsq(R, vscl(r0, -1)) };
};

/* ---------------- the counterweight law ---------------- */
UB.upperCom = function (model, k, u) {
  const links = model.links, mUp = links.slice(1).reduce((s, l) => s + l.m, 0);
  let xUp = 0, yUp = 0; const J = new Array(links.length).fill(0);
  links.forEach((l, i) => { if (i >= 1) { xUp += l.m * k.c[i][0]; yUp += l.m * k.c[i][1]; for (let j = 0; j <= i; j++) J[j] += l.m * k.Jx[i][j] / mUp; } });
  return { mUp, xUp: xUp / mUp, yUp: yUp / mUp, xdUp: dot(J, k.qd), J: u.map(j => J[j]) };
};
UB.counterweightStep = function (model, q, qd, g, active, qHome, detail) {
  const n = model.links.length;
  active = defaultActive(n, active);
  qHome = qHome || new Array(n).fill(0);
  const k = UB.core(model, q, qd), tau = new Array(n).fill(0);
  tau[0] = UB.ankleTorque(model, q, qd, g);
  if (!active.length) return detail ? { tau } : tau;
  const u = active, { mUp, xUp, xdUp, J } = UB.upperCom(model, k, u), mLegs = model.links[0].m;
  const xcDes = -(g.kappa_p * q[0] + g.kappa_d * qd[0]);
  const xUpDes = (UB.mtot(model) * xcDes - mLegs * k.c[0][0]) / mUp;
  const F = g.k_x * (xUpDes - xUp) - g.b_x * xdUp;
  const JJ = dot(J, J), pinv = JJ > 1e-12 ? J.map(v => v / JJ) : J.map(() => 0);
  const post = u.map(j => -g.kp_post * (q[j] - qHome[j]) - g.kd_post * qd[j]);
  const Npost = post.map((v, i) => v - pinv[i] * dot(J, post));
  const tauU = u.map((j, i) => J[i] * F + k.cvec[j] + k.g[j] + Npost[i]);
  u.forEach((j, i) => tau[j] = clip(tauU[i], g.tau_max[j]));
  return detail ? { tau, x_c_des: xcDes, x_up_des: xUpDes, x_up: xUp, F, J, xc: k.xc, H: k.h[2], tau_unclipped: tauU } : tau;
};

/* ---------------- the linear law: LQR, ankle spring included ---------------- */
UB.linearise = function (model, active, g, opt = {}) {
  const n = model.links.length, eps = 1e-5;
  active = active.filter(j => j > 0 && j < n).sort((a, b) => a - b);
  const free = [0, ...active], S = UB.selection(n, free), St = T(S), nf = free.length, nu = active.length;
  const q0 = opt.q0 || new Array(n).fill(0);
  const f = (x, u) => {
    const qf = x.slice(0, nf), qdf = x.slice(nf), q = vadd(q0, mv(S, qf)), qd = mv(S, qdf);
    const tau = new Array(n).fill(0); tau[0] = -g.ankle_k * q[0] - g.ankle_b * qd[0]; active.forEach((j, kk) => tau[j] = u[kk]);
    const k = UB.core(model, q, qd, { momentum: false });
    const rhs = tau.map((v, i) => v - k.cvec[i] - k.g[i]);
    return [...qdf, ...solve(mul(mul(St, k.M), S), mv(St, rhs))];
  };
  const x0 = new Array(2 * nf).fill(0), u0 = new Array(nu).fill(0), A = zeros(2 * nf, 2 * nf), B = zeros(2 * nf, nu);
  for (let i = 0; i < 2 * nf; i++) { const e = x0.slice(); e[i] = eps; const em = x0.slice(); em[i] = -eps; const d = vsub(f(e, u0), f(em, u0)); for (let r = 0; r < 2 * nf; r++) A[r][i] = d[r] / (2 * eps); }
  for (let i = 0; i < nu; i++) { const e = u0.slice(); e[i] = eps; const em = u0.slice(); em[i] = -eps; const d = vsub(f(x0, e), f(x0, em)); for (let r = 0; r < 2 * nf; r++) B[r][i] = d[r] / (2 * eps); }
  return { A, B, free };
};
/* Continuous-time LQR without an eigen-solver: iterate the discrete Riccati
   equation of the Euler-discretised system with a small step. Its fixed
   point converges to the CARE solution as dt -> 0. */
UB.care = function (A, B, Q, R, dt = 2e-4, iters = 400000) {
  const n = A.length, Ad = add(eye(n), scl(A, dt)), Bd = scl(B, dt), Qd = scl(Q, dt), Rd = scl(R, dt);
  const AdT = T(Ad), BdT = T(Bd);
  let P = Qd.map(r => r.slice());
  for (let it = 0; it < iters; it++) {
    const PA = mul(P, Ad), BtPA = mul(BdT, PA), S = add(Rd, mul(BdT, mul(P, Bd)));
    const Kd = mul(inv(S), BtPA);
    const Pr = add(Qd, sub(mul(AdT, PA), mul(T(BtPA), Kd)));
    const Pn = Pr.map((r, i) => r.map((v, j) => 0.5 * (v + Pr[j][i])));      // keep P symmetric, or it drifts
    let dmax = 0, pmax = 0;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { dmax = Math.max(dmax, Math.abs(Pn[i][j] - P[i][j])); pmax = Math.max(pmax, Math.abs(Pn[i][j])); }
    P = Pn;
    if (dmax < 1e-9 * pmax && it > 50) break;
  }
  return { K: mul(inv(R), mul(T(B), P)), P };
};
const lqrCache = new Map();
UB.lqrGain = function (model, g, active) {
  const n = model.links.length;
  active = (active || []).filter(j => j > 0 && j < n).sort((a, b) => a - b);
  const key = JSON.stringify([model.plane, model.links, model.foot, active, g.ankle_k, g.ankle_b, g.lean_max, g.posture_max, g.lean_rate_max, g.posture_rate_max, g.tau_max]);
  if (lqrCache.has(key)) return lqrCache.get(key);
  const { A, B, free } = UB.linearise(model, active, g), nf = free.length;
  const qmax = [g.lean_max, ...new Array(nf - 1).fill(g.posture_max)], vmax = [g.lean_rate_max, ...new Array(nf - 1).fill(g.posture_rate_max)];
  const Q = zeros(2 * nf, 2 * nf); [...qmax, ...vmax].forEach((v, i) => Q[i][i] = 1 / (v * v));
  const R = zeros(active.length, active.length); active.forEach((j, i) => R[i][i] = 1 / (g.tau_max[j] * g.tau_max[j]));
  // the iteration's error is O(dt): two step sizes and a Richardson step take it below 0.1 %
  const K = active.length ? sub(scl(UB.care(A, B, Q, R, 1e-4).K, 2), UB.care(A, B, Q, R, 2e-4).K) : zeros(0, 2 * nf);
  const out = { K, free, A, B };
  lqrCache.set(key, out);
  return out;
};
UB.lqrStep = function (model, q, qd, g, active, qHome, detail) {
  const n = model.links.length;
  active = defaultActive(n, active).sort((a, b) => a - b);
  const tau = new Array(n).fill(0); tau[0] = UB.ankleTorque(model, q, qd, g);
  if (!active.length) return detail ? { tau } : tau;
  const { K, free } = UB.lqrGain(model, g, active);
  const x = [...free.map(j => q[j]), ...free.map(j => qd[j])], u = mv(K, x).map(v => -v);
  active.forEach((j, kk) => tau[j] = clip(u[kk], g.tau_max[j]));
  return detail ? { tau, K, x, u } : tau;
};
UB.LAWS = { lqr: 'lqrStep', counterweight: 'counterweightStep', momentum: 'momentumStep' };
UB.controlStep = (model, q, qd, g, active, qHome, detail) => UB[UB.LAWS[g.law]](model, q, qd, g, active, qHome, detail);

UB.stopTorque = function (model, q, qd, k = 400, b = 15) {
  return model.links.map((l, j) => {
    if (j === 0) return 0;
    if (q[j] > l.hi) return -k * (q[j] - l.hi) - b * Math.max(qd[j], 0);
    if (q[j] < l.lo) return -k * (q[j] - l.lo) - b * Math.min(qd[j], 0);
    return 0;
  });
};

/* ---------------- simulation ---------------- */
UB.push = (o = {}) => Object.assign({ force: 80, t0: 0.2, duration: 0.1, point: 2 }, o);
UB.simulate = function (model, g, push, active, opt = {}) {
  const n = model.links.length, dt = opt.dt || 1e-3, Tend = opt.T || 3, sample = opt.sample || 10, fallDeg = opt.fall_deg || 30;
  const controller = opt.controller || UB.controlStep;
  g = g || UB.gains(); push = push || UB.push();
  let q = (opt.q0 || new Array(n).fill(0)).slice(), qd = new Array(n).fill(0);
  active = active || Array.from({ length: n - 1 }, (_, i) => i + 1);
  const free = [0, ...active.filter(j => j > 0 && j < n).sort((a, b) => a - b)], S = UB.selection(n, free), St = T(S), allFree = free.length === n;
  const genForce = (t, qq) => {
    if (t >= push.t0 && t < push.t0 + push.duration && push.force) { const J = UB.pointJacobian(model, qq, push.point); return J[0].map(v => v * push.force); }
    return null;
  };
  const accel = (t, qq, qqd, tau) => {
    const k = UB.core(model, qq, qqd, { momentum: false }), stop = UB.stopTorque(model, qq, qqd);
    let rhs = tau.map((v, i) => v + stop[i] - k.cvec[i] - k.g[i]);
    const f = genForce(t, qq); if (f) rhs = vadd(rhs, f);
    if (allFree) return { qdd: solve(k.M, rhs), hold: new Array(n).fill(0) };
    const qdd = mv(S, solve(mul(mul(St, k.M), S), mv(St, rhs)));
    return { qdd, hold: vsub(mv(k.M, qdd), rhs) };
  };
  const out = { t: [], q: [], qd: [], tau: [], xc: [], H_O: [], H_c: [], link_H: [], fell: false, t_fall: null, free };
  const steps = Math.round(Tend / dt);
  for (let i = 0; i <= steps; i++) {
    const t = i * dt, tau = controller(model, q, qd, g, active);
    if (i % sample === 0) {
      const k = UB.core(model, q, qd), { hold } = accel(t, q, qd, tau);
      out.t.push(t); out.q.push(q.slice()); out.qd.push(qd.slice()); out.tau.push(vadd(tau, hold));
      out.xc.push(k.xc); out.H_O.push(k.H_O); out.H_c.push(k.h[2]); out.link_H.push(k.link_H);
    }
    if (Math.abs(q[0]) > fallDeg * Math.PI / 180) { out.fell = true; out.t_fall = t; break; }
    const k1v = accel(t, q, qd, tau).qdd, k1x = qd;
    const k2v = accel(t + dt / 2, vadd(q, vscl(k1x, dt / 2)), vadd(qd, vscl(k1v, dt / 2)), tau).qdd, k2x = vadd(qd, vscl(k1v, dt / 2));
    const k3v = accel(t + dt / 2, vadd(q, vscl(k2x, dt / 2)), vadd(qd, vscl(k2v, dt / 2)), tau).qdd, k3x = vadd(qd, vscl(k2v, dt / 2));
    const k4v = accel(t + dt, vadd(q, vscl(k3x, dt)), vadd(qd, vscl(k3v, dt)), tau).qdd, k4x = vadd(qd, vscl(k3v, dt));
    q = q.map((v, j) => v + dt / 6 * (k1x[j] + 2 * k2x[j] + 2 * k3x[j] + k4x[j]));
    qd = qd.map((v, j) => v + dt / 6 * (k1v[j] + 2 * k2v[j] + 2 * k3v[j] + k4v[j]));
  }
  out.peak_lean_deg = out.q.length ? Math.max(...out.q.map(r => Math.abs(r[0]))) * 180 / Math.PI : 0;
  return out;
};
/* one step of the same integrator, for an animated lab that runs live */
UB.stepper = function (model, g, push, active, opt = {}) {
  const sim = { model, g, push, active, dt: opt.dt || 1e-3, t: 0, q: (opt.q0 || new Array(model.links.length).fill(0)).slice(),
    qd: new Array(model.links.length).fill(0), fell: false };
  const n = model.links.length, free = [0, ...active.filter(j => j > 0 && j < n).sort((a, b) => a - b)], S = UB.selection(n, free), St = T(S), allFree = free.length === n;
  const accel = (t, qq, qqd, tau) => {
    const k = UB.core(model, qq, qqd, { momentum: false }), stop = UB.stopTorque(model, qq, qqd);
    let rhs = tau.map((v, i) => v + stop[i] - k.cvec[i] - k.g[i]);
    if (t >= push.t0 && t < push.t0 + push.duration && push.force) { const J = UB.pointJacobian(model, qq, push.point); rhs = vadd(rhs, J[0].map(v => v * push.force)); }
    if (allFree) return solve(k.M, rhs);
    return mv(S, solve(mul(mul(St, k.M), S), mv(St, rhs)));
  };
  sim.step = () => {
    const { q, qd, dt, t } = sim, tau = UB.controlStep(model, q, qd, g, active);
    sim.tau = tau;
    const k1v = accel(t, q, qd, tau), k1x = qd;
    const k2v = accel(t + dt / 2, vadd(q, vscl(k1x, dt / 2)), vadd(qd, vscl(k1v, dt / 2)), tau), k2x = vadd(qd, vscl(k1v, dt / 2));
    const k3v = accel(t + dt / 2, vadd(q, vscl(k2x, dt / 2)), vadd(qd, vscl(k2v, dt / 2)), tau), k3x = vadd(qd, vscl(k2v, dt / 2));
    const k4v = accel(t + dt, vadd(q, vscl(k3x, dt)), vadd(qd, vscl(k3v, dt)), tau), k4x = vadd(qd, vscl(k3v, dt));
    sim.q = q.map((v, j) => v + dt / 6 * (k1x[j] + 2 * k2x[j] + 2 * k3x[j] + k4x[j]));
    sim.qd = qd.map((v, j) => v + dt / 6 * (k1v[j] + 2 * k2v[j] + 2 * k3v[j] + k4v[j]));
    sim.t += dt;
    if (Math.abs(sim.q[0]) > Math.PI / 6) sim.fell = true;
    return sim;
  };
  return sim;
};

root.UB = UB;
if (typeof module !== 'undefined') module.exports = UB;
})(typeof window !== 'undefined' ? window : globalThis);
