/* Small linear-algebra and robotics library shared by the step labs.
   Mirrors ctrlcore/robokin.py and ctrlcore/robodyn.py (tests/test_steplabs.py
   runs it under node and compares). Twists are (ω, v), as in Modern Robotics. */
(function (root) {
const MR = {};

/* ---------- vectors ---------- */
MR.add = (a, b) => a.map((x, i) => x + b[i]);
MR.sub = (a, b) => a.map((x, i) => x - b[i]);
MR.scl = (a, k) => a.map(x => x * k);
MR.dot = (a, b) => a.reduce((s, x, i) => s + x * b[i], 0);
MR.norm = a => Math.sqrt(MR.dot(a, a));
MR.unit = a => { const n = MR.norm(a); return n < 1e-12 ? a.slice() : MR.scl(a, 1 / n); };
MR.cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
MR.cross2 = (a, b) => a[0] * b[1] - a[1] * b[0];
MR.perp = a => [-a[1], a[0]];                       // ẑ × a in the plane
MR.rot2 = (v, t) => [Math.cos(t) * v[0] - Math.sin(t) * v[1], Math.sin(t) * v[0] + Math.cos(t) * v[1]];

/* ---------- matrices (arrays of rows) ---------- */
MR.zeros = (n, m) => Array.from({ length: n }, () => new Array(m === undefined ? n : m).fill(0));
MR.eye = n => MR.zeros(n).map((r, i) => (r[i] = 1, r));
MR.T = A => A[0].map((_, j) => A.map(r => r[j]));
MR.mul = (A, B) => A.map(r => B[0].map((_, j) => r.reduce((s, x, k) => s + x * B[k][j], 0)));
MR.mv = (A, x) => A.map(r => MR.dot(r, x));
MR.madd = (A, B) => A.map((r, i) => r.map((x, j) => x + B[i][j]));
MR.msub = (A, B) => A.map((r, i) => r.map((x, j) => x - B[i][j]));
MR.mscl = (A, k) => A.map(r => r.map(x => x * k));
MR.outer = (a, b) => a.map(x => b.map(y => x * y));
MR.col = (A, j) => A.map(r => r[j]);
MR.fromCols = cols => cols[0].map((_, i) => cols.map(c => c[i]));
MR.trace = A => A.reduce((s, r, i) => s + r[i], 0);

/* Gaussian elimination with partial pivoting: solve A x = b (b vector or matrix). */
MR.solve = (A, b) => {
  const n = A.length, vec = !Array.isArray(b[0]);
  const B = vec ? b.map(x => [x]) : b.map(r => r.slice());
  const M = A.map((r, i) => r.concat(B[i]));
  const w = M[0].length;
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]];
    const d = M[c][c];
    if (Math.abs(d) < 1e-14) throw new Error('singular matrix');
    for (let j = c; j < w; j++) M[c][j] /= d;
    for (let r = 0; r < n; r++) if (r !== c) {
      const k = M[r][c];
      if (k) for (let j = c; j < w; j++) M[r][j] -= k * M[c][j];
    }
  }
  const X = M.map(r => r.slice(n));
  return vec ? X.map(r => r[0]) : X;
};
MR.inv = A => MR.solve(A, MR.eye(A.length));
MR.det = A => {
  const n = A.length, M = A.map(r => r.slice());
  let d = 1;
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-15) return 0;
    if (p !== c) { [M[c], M[p]] = [M[p], M[c]]; d = -d; }
    d *= M[c][c];
    for (let r = c + 1; r < n; r++) {
      const k = M[r][c] / M[c][c];
      for (let j = c; j < n; j++) M[r][j] -= k * M[c][j];
    }
  }
  return d;
};

/* Symmetric eigen-decomposition by cyclic Jacobi. Values sorted largest first;
   vecs[k] is the unit eigenvector of vals[k]. */
MR.eigSym = A => {
  const n = A.length, a = A.map(r => r.slice()), V = MR.eye(n);
  for (let sweep = 0; sweep < 60; sweep++) {
    let off = 0;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) off += a[p][q] * a[p][q];
    if (off < 1e-26) break;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) {
      if (Math.abs(a[p][q]) < 1e-300) continue;
      const th = 0.5 * Math.atan2(2 * a[p][q], a[q][q] - a[p][p]);
      const c = Math.cos(th), s = Math.sin(th);
      for (let k = 0; k < n; k++) {
        const akp = a[k][p], akq = a[k][q];
        a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq;
      }
      for (let k = 0; k < n; k++) {
        const apk = a[p][k], aqk = a[q][k];
        a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk;
      }
      for (let k = 0; k < n; k++) {
        const vkp = V[k][p], vkq = V[k][q];
        V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq;
      }
    }
  }
  const idx = [...Array(n).keys()].sort((i, j) => a[j][j] - a[i][i]);
  return { vals: idx.map(i => a[i][i]), vecs: idx.map(i => V.map(r => r[i])) };
};

/* Thin SVD of an m×n matrix via the eigenvectors of JᵀJ.
   Returns sigma (largest first, length min(m,n)), u[k] (m-vectors), v[k] (n-vectors, all n). */
MR.svd = J => {
  const m = J.length, n = J[0].length, k = Math.min(m, n);
  const E = MR.eigSym(MR.mul(MR.T(J), J));
  const sigma = [], u = [];
  for (let i = 0; i < k; i++) {
    const s = Math.sqrt(Math.max(E.vals[i], 0));
    sigma.push(s);
    const Jv = MR.mv(J, E.vecs[i]);
    u.push(s > 1e-10 ? MR.scl(Jv, 1 / s) : null);
  }
  /* fill missing u's with an orthonormal completion */
  for (let i = 0; i < k; i++) if (!u[i]) {
    for (let e = 0; e < m; e++) {
      let c = new Array(m).fill(0); c[e] = 1;
      for (const w of u) if (w) c = MR.sub(c, MR.scl(w, MR.dot(w, c)));
      if (MR.norm(c) > 1e-6) { u[i] = MR.unit(c); break; }
    }
  }
  return { sigma, u, v: E.vecs };
};
/* Damped pseudoinverse  V diag(σ/(σ²+λ²)) Uᵀ  (λ = 0: plain J⁺, tiny σ dropped). */
MR.pinv = (J, lam = 0) => {
  const m = J.length, n = J[0].length, { sigma, u, v } = MR.svd(J);
  let P = MR.zeros(n, m);
  sigma.forEach((s, i) => {
    const k = lam ? s / (s * s + lam * lam) : (s > 1e-9 ? 1 / s : 0);
    if (k) P = MR.madd(P, MR.mscl(MR.outer(v[i], u[i]), k));
  });
  return P;
};

/* ---------- SO(3) / SE(3) ---------- */
MR.skew = w => [[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]];
MR.unskew = W => [W[2][1], W[0][2], W[1][0]];
MR.expRot = (w, th) => {                        // w a unit axis
  const W = MR.skew(w), W2 = MR.mul(W, W);
  return MR.madd(MR.madd(MR.eye(3), MR.mscl(W, Math.sin(th))), MR.mscl(W2, 1 - Math.cos(th)));
};
MR.makeT = (R, p) => [[...R[0], p[0]], [...R[1], p[1]], [...R[2], p[2]], [0, 0, 0, 1]];
MR.Rof = T => T.slice(0, 3).map(r => r.slice(0, 3));
MR.pof = T => [T[0][3], T[1][3], T[2][3]];
MR.invT = T => { const R = MR.Rof(T), Rt = MR.T(R); return MR.makeT(Rt, MR.scl(MR.mv(Rt, MR.pof(T)), -1)); };
MR.adj = T => {                                 // [R 0; [p]R R]
  const R = MR.Rof(T), pR = MR.mul(MR.skew(MR.pof(T)), R), A = MR.zeros(6);
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
    A[i][j] = R[i][j]; A[i + 3][j + 3] = R[i][j]; A[i + 3][j] = pR[i][j];
  }
  return A;
};
MR.adSmall = V => {                             // [ad_V] = [[ω] 0; [v] [ω]]
  const W = MR.skew(V.slice(0, 3)), Vv = MR.skew(V.slice(3)), A = MR.zeros(6);
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
    A[i][j] = W[i][j]; A[i + 3][j + 3] = W[i][j]; A[i + 3][j] = Vv[i][j];
  }
  return A;
};
MR.expTwist = (S, th) => {                      // e^[S]θ, S a screw axis
  const w = S.slice(0, 3), v = S.slice(3);
  if (MR.norm(w) < 1e-12) return MR.makeT(MR.eye(3), MR.scl(v, th));
  const W = MR.skew(w), W2 = MR.mul(W, W);
  const G = MR.madd(MR.madd(MR.mscl(MR.eye(3), th), MR.mscl(W, 1 - Math.cos(th))), MR.mscl(W2, th - Math.sin(th)));
  return MR.makeT(MR.expRot(w, th), MR.mv(G, v));
};
MR.logRot = R => {
  const c = Math.max(-1, Math.min(1, (MR.trace(R) - 1) / 2)), th = Math.acos(c);
  if (th < 1e-9) return [0, 0, 0];
  if (Math.PI - th < 1e-6) {
    let k = 0; for (let i = 1; i < 3; i++) if (R[i][i] > R[k][k]) k = i;
    const w = [0, 0, 0].map((_, i) => (R[i][k] + (i === k ? 1 : 0)) / Math.sqrt(2 * (1 + R[k][k])));
    return MR.scl(w, th);
  }
  return MR.scl([R[2][1] - R[1][2], R[0][2] - R[2][0], R[1][0] - R[0][1]], th / (2 * Math.sin(th)));
};
MR.logT = T => {                                // returns the 6-vector S·θ
  const R = MR.Rof(T), p = MR.pof(T), wt = MR.logRot(R), th = MR.norm(wt);
  if (th < 1e-9) return [0, 0, 0, ...p];
  const W = MR.skew(MR.scl(wt, 1 / th)), W2 = MR.mul(W, W);
  const Gi = MR.madd(MR.madd(MR.mscl(MR.eye(3), 1 / th), MR.mscl(W, -0.5)),
    MR.mscl(W2, 1 / th - 0.5 / Math.tan(th / 2)));
  return [...wt, ...MR.scl(MR.mv(Gi, p), th)];
};
MR.screw = (w, q, h = 0) => [...w, ...MR.add(MR.scl(MR.cross(w, q), -1), MR.scl(w, h))];   // v = −ω×q + hω
MR.fkSpace = (M, S, th) => S.reduceRight((T, s, i) => MR.mul(MR.expTwist(s, th[i]), T), M);
MR.fkBody = (M, B, th) => B.reduce((T, b, i) => MR.mul(T, MR.expTwist(b, th[i])), M);
MR.jacSpace = (S, th) => {                      // returns columns
  let T = MR.eye(4); const cols = [];
  S.forEach((s, i) => { cols.push(MR.mv(MR.adj(T), s)); T = MR.mul(T, MR.expTwist(s, th[i])); });
  return cols;
};
MR.jacBody = (B, th) => {
  let T = MR.eye(4); const cols = new Array(B.length);
  for (let i = B.length - 1; i >= 0; i--) { cols[i] = MR.mv(MR.adj(T), B[i]); T = MR.mul(T, MR.expTwist(B[i], -th[i])); }
  return cols;
};

/* The RRPR arm of the C++ workshops (ctrlcore/rrpr_check.py). */
MR.RRPR = {
  S: [[0, 0, 1, 0, 0, 0], [0, -1, 0, 1, 0, 0], [0, 0, 0, 1, 0, 0], [1, 0, 0, 0, 1, 0]],
  M: MR.makeT([[1, 0, 0], [0, -1, 0], [0, 0, -1]], [1.5, 0, 0.8]),
};

/* ---------- planar serial arms (ctrlcore/robodyn.PlanarArm) ---------- */
MR.arm = (o = {}) => {
  const L = o.L || [1, 1], n = L.length, m = o.m || L.map(() => 1);
  return { L, m, n, r: o.r || L.map(x => x / 2), I: o.I || m.map((mi, i) => mi * L[i] * L[i] / 12),
    g: o.g === undefined ? 9.81 : o.g, rotor: o.rotor || L.map(() => 0) };
};
MR.points = (L, q) => {
  const P = [[0, 0]]; let a = 0;
  for (let i = 0; i < L.length; i++) { a += q[i]; const p = P[i]; P.push([p[0] + L[i] * Math.cos(a), p[1] + L[i] * Math.sin(a)]); }
  return P;
};
MR.coms = (arm, q) => {
  const P = MR.points(arm.L, q); let a = 0;
  return arm.r.map((r, i) => { a += q[i]; return [P[i][0] + r * Math.cos(a), P[i][1] + r * Math.sin(a)]; });
};
/* 2×n Jacobian of a point p attached to link k (joints after k get zero columns). */
MR.pointJac = (L, q, p, k) => {
  const P = MR.points(L, q), J = MR.zeros(2, L.length);
  for (let i = 0; i <= k; i++) { J[0][i] = -(p[1] - P[i][1]); J[1][i] = p[0] - P[i][0]; }
  return J;
};
MR.tipJac = (L, q) => { const P = MR.points(L, q); return MR.pointJac(L, q, P[L.length], L.length - 1); };
MR.rnea = (arm, q, qd, qdd, o = {}) => {
  const n = arm.n, grav = o.gravity === undefined ? true : o.gravity;
  let ang = 0, w = 0, al = 0; const ux = [], uy = [], W = [], AL = [];
  for (let i = 0; i < n; i++) { ang += q[i]; w += qd[i]; al += qdd[i]; ux.push(Math.cos(ang)); uy.push(Math.sin(ang)); W.push(w); AL.push(al); }
  let ax = 0, ay = grav ? arm.g : 0; const acx = [], acy = [], ajx = [ax], ajy = [ay];
  for (let i = 0; i < n; i++) {
    const r = arm.r[i], L = arm.L[i], w2 = W[i] * W[i];
    acx.push(ax - AL[i] * r * uy[i] - w2 * r * ux[i]);
    acy.push(ay + AL[i] * r * ux[i] - w2 * r * uy[i]);
    ax = ax - AL[i] * L * uy[i] - w2 * L * ux[i];
    ay = ay + AL[i] * L * ux[i] - w2 * L * uy[i];
    ajx.push(ax); ajy.push(ay);
  }
  let fx = o.ftip ? o.ftip[0] : 0, fy = o.ftip ? o.ftip[1] : 0, mom = 0;
  const tau = new Array(n).fill(0), F = new Array(n), Mo = new Array(n);
  for (let i = n - 1; i >= 0; i--) {
    const m = arm.m[i], r = arm.r[i], L = arm.L[i], mx = m * acx[i], my = m * acy[i];
    mom = mom + L * (ux[i] * fy - uy[i] * fx) + r * (ux[i] * my - uy[i] * mx) + arm.I[i] * AL[i];
    fx += mx; fy += my;
    tau[i] = mom + arm.rotor[i] * qdd[i]; F[i] = [fx, fy]; Mo[i] = mom;
  }
  if (o.trace) return { tau, omega: W, alpha: AL, accC: acx.map((x, i) => [x, acy[i]]), accJ: ajx.map((x, i) => [x, ajy[i]]), force: F, moment: Mo, u: ux.map((x, i) => [x, uy[i]]) };
  return tau;
};
MR.massMatrix = (arm, q) => {
  const n = arm.n, z = new Array(n).fill(0), cols = [];
  for (let i = 0; i < n; i++) { const e = z.slice(); e[i] = 1; cols.push(MR.rnea(arm, q, z, e, { gravity: false })); }
  return MR.fromCols(cols);
};
MR.gravityVec = (arm, q) => { const z = new Array(arm.n).fill(0); return MR.rnea(arm, q, z, z); };
MR.hVec = (arm, q, qd, ftip) => MR.rnea(arm, q, qd, new Array(arm.n).fill(0), { ftip });
MR.cVec = (arm, q, qd) => MR.sub(MR.hVec(arm, q, qd), MR.gravityVec(arm, q));
MR.dM = (arm, q, eps = 1e-6) => q.map((_, k) => {
  const a = q.slice(), b = q.slice(); a[k] += eps; b[k] -= eps;
  return MR.mscl(MR.msub(MR.massMatrix(arm, a), MR.massMatrix(arm, b)), 1 / (2 * eps));
});
MR.christoffel = (arm, q) => {                  // G[i][j][k]
  const D = MR.dM(arm, q), n = arm.n;
  return [...Array(n)].map((_, i) => [...Array(n)].map((_, j) => [...Array(n)].map((_, k) =>
    0.5 * (D[k][i][j] + D[j][i][k] - D[i][j][k]))));
};
MR.coriolis = (arm, q, qd) => {
  const G = MR.christoffel(arm, q);
  return G.map(Gi => Gi.map(Gij => MR.dot(Gij, qd)));
};
MR.Mdot = (arm, q, qd) => MR.dM(arm, q).reduce((S, Dk, k) => MR.madd(S, MR.mscl(Dk, qd[k])), MR.zeros(arm.n));
MR.forwardDyn = (arm, q, qd, tau, ftip) => MR.solve(MR.massMatrix(arm, q), MR.sub(tau, MR.hVec(arm, q, qd, ftip)));
MR.energy = (arm, q, qd) => {
  const K = 0.5 * MR.dot(qd, MR.mv(MR.massMatrix(arm, q), qd));
  const C = MR.coms(arm, q);
  return { K, P: C.reduce((s, c, i) => s + arm.m[i] * arm.g * c[1], 0) };
};
MR.JdotQd = (L, q, qd, eps = 1e-6) => {
  const a = MR.tipJac(L, MR.add(q, MR.scl(qd, eps))), b = MR.tipJac(L, MR.sub(q, MR.scl(qd, eps)));
  return MR.mv(MR.mscl(MR.msub(a, b), 1 / (2 * eps)), qd);
};
MR.quintic = (t, T) => {
  const x = Math.max(0, Math.min(1, t / T));
  return [10 * x ** 3 - 15 * x ** 4 + 6 * x ** 5, (30 * x ** 2 - 60 * x ** 3 + 30 * x ** 4) / T, (60 * x - 180 * x ** 2 + 120 * x ** 3) / (T * T)];
};

root.MR = MR;
if (typeof module !== 'undefined') module.exports = MR;
})(typeof window !== 'undefined' ? window : globalThis);
