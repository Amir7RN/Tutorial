/* Recursive Newton–Euler in the book's 6-D notation (Modern Robotics 8.3),
   for a planar nR arm of uniform rods moving in the x–y plane, gravity −y.

   Frames: {0} at the base, {i} at the centre of mass of link i, {n+1} at the tip.
   M_{i,i-1}: pose of {i-1} in {i} at θ = 0.  A_i: joint i's screw axis in {i}.
   G_i = diag(I_x, I_y, I_z, m, m, m).  Twists and wrenches are (ω, v) and (m, f).
   Needs mr.js. */
(function (root) {
const MR = root.MR, R6 = {};
const I3 = MR.eye(3);

R6.build = (L, m) => {
  const n = L.length, r = L.map(x => x / 2), M = [], A = [], G = [], xj = [];
  let x = 0;
  for (let i = 0; i < n; i++) { xj.push(x); M.push(MR.makeT(I3, [x + r[i], 0, 0])); x += L[i]; }
  M.push(MR.makeT(I3, [x, 0, 0]));                                   // {n+1}: the tip
  const Mrel = M.map((Mi, i) => MR.mul(MR.invT(Mi), i ? M[i - 1] : MR.eye(4)));   // M_{i,i-1}
  for (let i = 0; i < n; i++) {
    const S = MR.screw([0, 0, 1], [xj[i], 0, 0]);                    // space screw axis of joint i
    A.push(MR.mv(MR.adj(MR.invT(M[i])), S));                         // A_i = Ad_{M_i^-1} S_i
    const Iz = m[i] * L[i] * L[i] / 12;
    G.push([[1e-4 * m[i], 0, 0, 0, 0, 0], [0, Iz, 0, 0, 0, 0], [0, 0, Iz, 0, 0, 0],
            [0, 0, 0, m[i], 0, 0], [0, 0, 0, 0, m[i], 0], [0, 0, 0, 0, 0, m[i]]]);
  }
  return { n, L, m, r, M, Mrel, A, G, g: 9.81 };
};

/* One RNEA call with every intermediate quantity.
   o.g: gravity (default 9.81, 0 to switch off); o.ftipWorld: [fx, fy] the tip pushes on the world. */
R6.rnea = (R, th, thd, thdd, o = {}) => {
  const n = R.n, g = o.g === undefined ? R.g : o.g, z6 = [0, 0, 0, 0, 0, 0];
  const T = [], AdT = [], V = [z6], Vd = [[0, 0, 0, 0, g, 0]], Twd = [MR.eye(4)];
  const fw = { VAd: [], Ath: [], VdAd: [], adTerm: [], Athdd: [] };
  for (let i = 0; i < n; i++) {
    T.push(MR.mul(MR.expTwist(R.A[i], -th[i]), R.Mrel[i]));          // T_{i,i-1} = e^{-[A_i]θ_i} M_{i,i-1}
    AdT.push(MR.adj(T[i]));
    const VAd = MR.mv(AdT[i], V[i]), Ath = MR.scl(R.A[i], thd[i]);
    V.push(MR.add(VAd, Ath));
    const VdAd = MR.mv(AdT[i], Vd[i]), adTerm = MR.scl(MR.mv(MR.adSmall(V[i + 1]), R.A[i]), thd[i]), Athdd = MR.scl(R.A[i], thdd[i]);
    Vd.push(MR.add(MR.add(VdAd, adTerm), Athdd));
    Twd.push(MR.mul(Twd[i], MR.invT(T[i])));                         // T_{0,i}
    Object.entries({ VAd, Ath, VdAd, adTerm, Athdd }).forEach(([k, v]) => fw[k].push(v));
  }
  const Ttip = R.Mrel[n], Rtip = MR.Rof(MR.mul(Twd[n], MR.invT(Ttip)));
  const fwld = o.ftipWorld || [0, 0], fb = MR.mv(MR.T(Rtip), [fwld[0], fwld[1], 0]);
  const F = new Array(n + 1); F[n] = [0, 0, 0, ...fb];
  const bw = { pass: [], GVd: [], cor: [] }, tau = new Array(n);
  for (let i = n - 1; i >= 0; i--) {
    const Tn = i === n - 1 ? Ttip : T[i + 1];                        // T_{i+1,i}
    const pass = MR.mv(MR.T(MR.adj(Tn)), F[i + 1]);
    const GVd = MR.mv(R.G[i], Vd[i + 1]);
    const cor = MR.scl(MR.mv(MR.T(MR.adSmall(V[i + 1])), MR.mv(R.G[i], V[i + 1])), -1);
    F[i] = MR.add(MR.add(pass, GVd), cor);
    tau[i] = MR.dot(F[i], R.A[i]);
    bw.pass[i] = pass; bw.GVd[i] = GVd; bw.cor[i] = cor;
  }
  return { tau, T, AdT, V: V.slice(1), Vd: Vd.slice(1), Vd0: Vd[0], F: F.slice(0, n), Ftip: F[n], Twd: Twd.slice(1), fw, bw };
};

/* world geometry for drawing: joint points, COM points, link angles */
R6.geom = (R, th) => {
  const P = [[0, 0]], C = [], ang = []; let a = 0;
  for (let i = 0; i < R.n; i++) { a += th[i]; ang.push(a); const p = P[i], u = [Math.cos(a), Math.sin(a)];
    C.push([p[0] + R.r[i] * u[0], p[1] + R.r[i] * u[1]]); P.push([p[0] + R.L[i] * u[0], p[1] + R.L[i] * u[1]]); }
  return { P, C, ang };
};
R6.massMatrix = (R, th) => { const z = th.map(() => 0);
  return MR.fromCols(th.map((_, j) => { const e = z.slice(); e[j] = 1; return R6.rnea(R, th, z, e, { g: 0 }).tau; })); };
R6.energy = (R, th, thd) => {
  const K = .5 * MR.dot(thd, MR.mv(R6.massMatrix(R, th), thd)), C = R6.geom(R, th).C;
  return { K, P: C.reduce((s, c, i) => s + R.m[i] * R.g * c[1], 0) };
};
/* 6-vector as (ω | v) text */
R6.v6 = (v, d = 2) => '(' + v.slice(0, 3).map(x => root.SL.f(x, d)).join(', ') + ' | ' + v.slice(3).map(x => root.SL.f(x, d)).join(', ') + ')';
root.R6 = R6;
})(window);
