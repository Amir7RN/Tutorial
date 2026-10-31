/* Time-optimal time scaling along a path q(s) of the planar 2R arm (Modern Robotics 9.4).
   Path dynamics τ = m(s)s̈ + c(s)ṡ² + g(s), per-joint bounds L_i, U_i, the velocity limit
   curve, and the integrate-forward / integrate-backward / tangent-point algorithm. */
(function () {
const TO = window.TOPT = {};
TO.ARM = MR.arm({ L: [1, .8], m: [2, 1.5], r: [.5, .4], I: [.17, .08] });
/* path: straight joint line plus an optional bulge b·sin(πs) on (1, −1) */
TO.path = P => ({
  q: s => [P.q0[0] + s * (P.q1[0] - P.q0[0]) + P.b * Math.sin(Math.PI * s), P.q0[1] + s * (P.q1[1] - P.q0[1]) - P.b * Math.sin(Math.PI * s)],
  dq: s => [P.q1[0] - P.q0[0] + P.b * Math.PI * Math.cos(Math.PI * s), P.q1[1] - P.q0[1] - P.b * Math.PI * Math.cos(Math.PI * s)],
  ddq: s => [-P.b * Math.PI * Math.PI * Math.sin(Math.PI * s), P.b * Math.PI * Math.PI * Math.sin(Math.PI * s)],
});
/* m(s) = M θ', c(s) = M θ'' + θ'ᵀΓθ' (RNEA with q̇ = θ', no gravity), g(s) = gravity */
TO.dyn = (P, s) => { const pa = TO.path(P), q = pa.q(s), d1 = pa.dq(s), d2 = pa.ddq(s), A = TO.ARM, M = MR.massMatrix(A, q);
  const m = MR.mv(M, d1), c = MR.add(MR.mv(M, d2), MR.rnea(A, q, d1, [0, 0], { gravity: false })), g = MR.gravityVec(A, q);
  return { q, d1, d2, M, m, c, g }; };
/* per-joint bounds on s̈ at (s, ṡ) */
TO.bounds = (P, s, sd, D) => { D = D || TO.dyn(P, s); const per = [];
  for (let i = 0; i < 2; i++) { const lo = -P.tau[i] - D.c[i] * sd * sd - D.g[i], hi = P.tau[i] - D.c[i] * sd * sd - D.g[i], m = D.m[i];
    if (Math.abs(m) < 1e-9) per.push({ L: -Infinity, U: Infinity, lo, hi, m, zero: true }); else per.push(m > 0 ? { L: lo / m, U: hi / m, lo, hi, m } : { L: hi / m, U: lo / m, lo, hi, m }); }
  return { per, L: Math.max(per[0].L, per[1].L), U: Math.min(per[0].U, per[1].U), D }; };
TO.feasible = (P, s, sd) => { const b = TO.bounds(P, s, sd); return b.L <= b.U; };
/* velocity limit curve: largest ṡ with L ≤ U (bisection) */
TO.vlc = (P, s, top = 12) => { if (TO.feasible(P, s, top)) return top; let lo = 0, hi = top; for (let k = 0; k < 40; k++) { const m = (lo + hi) / 2; TO.feasible(P, s, m) ? lo = m : hi = m; } return lo; };
TO.vlcCurve = (P, n = 200) => [...Array(n + 1)].map((_, i) => [i / n, TO.vlc(P, i / n)]);
/* integrate the phase plane: dir +1 forward with U, −1 backward with L; stop on VLC / ṡ ≤ 0 / s out of [0,1] / stopFn */
TO.integ = (P, s0, sd0, dir, useU, stopFn, ds = 1 / 800) => {
  const out = [[s0, sd0]]; let s = s0, x = sd0 * sd0, why = 'end';
  for (let k = 0; k < 4000; k++) { const sd = Math.sqrt(Math.max(0, x)), b = TO.bounds(P, s, sd);
    if (b.L > b.U + 1e-9) { why = 'vlc'; break; }
    const acc = useU ? b.U : b.L; x += 2 * acc * ds * dir; s += ds * dir;
    if (x <= 0) { out.push([s, 0]); why = 'zero'; break; }
    if (s > 1 || s < 0) { why = 'end'; break; }
    out.push([s, Math.sqrt(x)]); if (stopFn && stopFn(s, Math.sqrt(x))) { why = 'stop'; break; } }
  return { pts: out, why };
};
const interp = (pts, s) => { /* ṡ of a curve (sorted or not) at s, or null */ for (let i = 1; i < pts.length; i++) { const a = pts[i - 1], b = pts[i]; if ((a[0] - s) * (b[0] - s) <= 0 && a[0] !== b[0]) return a[1] + (b[1] - a[1]) * (s - a[0]) / (b[0] - a[0]); } return null; };
TO.interp = interp;
/* full algorithm (MR 9.4.2): returns segments, switch points, profile, T, and the tangent-search guesses */
TO.solve = P => {
  const F = TO.integ(P, 1, 0, -1, false), segs = [], switches = [], guesses = [];
  const hitsF = (s, sd) => { const f = interp(F.pts, s); return f !== null && sd >= f; };
  let s = 0, sd = 0, iter = 0, lim = null;
  while (iter++ < 6) {
    const A = TO.integ(P, s, sd, 1, true, hitsF); segs.push({ kind: 'U', pts: A.pts });
    if (A.why === 'stop' || A.why === 'end') { const last = A.pts[A.pts.length - 1]; switches.push({ s: last[0], sd: last[1], to: 'L (final)' }); break; }
    if (A.why !== 'vlc') break;
    const hit = A.pts[A.pts.length - 1]; if (!lim) lim = hit;
    /* tangent search: lower ṡ at s_lim, integrate L forward; binary search between "hits ṡ = 0" and "hits VLC" */
    let lo = 0, hi = hit[1], tan = null, tanPts = null;
    for (let k = 0; k < 30; k++) { const g = (lo + hi) / 2, R = TO.integ(P, hit[0], g, 1, false); if (guesses.length < 4 && segs.length === 1) guesses.push({ sd: g, pts: R.pts, why: R.why });
      if (R.why === 'vlc') { hi = g; tan = R.pts[R.pts.length - 1]; tanPts = R.pts; } else lo = g; }
    if (!tan) break;
    /* back from the tangent point with L until it meets the U segment */
    const Useg = segs[segs.length - 1].pts, B = TO.integ(P, tan[0] - 2e-3, tan[1] * .97, -1, false, (ss, sdd) => { const u = interp(Useg, ss); return u !== null && sdd >= u; });
    const s1 = B.pts[B.pts.length - 1]; switches.push({ s: s1[0], sd: s1[1], to: 'L' }); switches.push({ s: tan[0], sd: tan[1], to: 'U' });
    segs[segs.length - 1].pts = Useg.filter(p => p[0] <= s1[0]); segs.push({ kind: 'L', pts: B.pts.slice().reverse() });
    s = tan[0] + 1e-3; sd = tan[1] * .995;
  }
  segs.push({ kind: 'L', pts: F.pts.slice().reverse().filter(p => p[0] >= (switches.length ? switches[switches.length - 1].s : 0)) });
  const prof = [...Array(401)].map((_, i) => { const x = i / 400; let v = null; for (const sg of segs) { const y = interp(sg.pts, x); if (y !== null) v = v === null ? y : Math.min(v, y); } return [x, v]; });
  for (let i = 0; i < prof.length; i++) if (prof[i][1] === null) { let a = i, b = i; while (a > 0 && prof[a][1] === null) a--; while (b < prof.length - 1 && prof[b][1] === null) b++; prof[i][1] = ((prof[a][1] ?? 0) + (prof[b][1] ?? 0)) / 2; }
  let T = 0; for (let i = 1; i < prof.length; i++) { const v = (prof[i][1] + prof[i - 1][1]) / 2; T += (prof[i][0] - prof[i - 1][0]) / Math.max(v, 1e-3); }
  return { F, segs, switches, prof, T, lim, guesses };
};
/* torques along a profile ṡ(s): s̈ = ½ d(ṡ²)/ds */
TO.torques = (P, prof) => prof.map((p, i) => { const j = Math.min(prof.length - 1, i + 1), k = Math.max(0, i - 1), sdd = (prof[j][1] ** 2 - prof[k][1] ** 2) / (2 * (prof[j][0] - prof[k][0])), D = TO.dyn(P, p[0]);
  return [p[0], ...[0, 1].map(n => D.m[n] * sdd + D.c[n] * p[1] * p[1] + D.g[n])]; });
})();
