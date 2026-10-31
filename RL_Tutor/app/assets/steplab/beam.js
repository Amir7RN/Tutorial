/* Hip-exo beam-walking teaching model for the step labs (pages 96-104).
   A JS port of ctrlcore/beamexo.py. HW, CTRL and RESULTS are quoted from the papers;
   everything simulated is a teaching model of the published control law, not data. */
(function () {
const B = window.BEAM = {};
B.HW = { velBW: 5, delayMs: 2, mass: 6, peak: 72, maxK: 95, Ktested: [12, 48, 95.04], zetaTested: [.6, .8, 1, 1.2], volitional: 200, N: 100 };
B.CTRL = { dz: .08, stance: .2, swing: .05, filtHz: 2, filtZ: .707, M: 1e-3, Bd: 1e-2, K: 5e-2 };
B.RES = { baseline: 80.9, noAssist: 70.1, active: 79.5, p_an: .049, d_an: .89, p_nb: .048, p_ab: .965, gain: 9.4, ci: [1.83, 17.16], extra: 8.5,
  speed_p: .0386, speed_d: .76, com_p: .019, com_d: -.9, wbam_p: .0169, wbam_d: -1.395, help: [1.57, .58], detect: [4.2, .8] };
B.subject = (h = 1.75, m = 75) => {
  const S = { h, m, mT: .578 * m, mL: .161 * m, lL: .53 * h, lT: .288 * h };
  S.dT = .626 * S.lT; S.dL = .447 * S.lL; S.IT = S.mT * S.lT ** 2 / 12; S.IL = S.mL * S.lL ** 2 / 12;
  S.arm = th => Math.sqrt(S.lL ** 2 + S.dT ** 2 - 2 * S.lL * S.dT * Math.cos(Math.PI - th));
  S.Iwb = (th = 0) => S.IT + S.mT * S.arm(th) ** 2 + 2 * (S.IL + S.mL * S.dL ** 2);
  S.comX = (tT, tL, tR) => (S.mT * S.dT * Math.sin(tT) + S.mL * S.dL * (Math.sin(tL) + Math.sin(tR))) / m;
  S.comV = (tT, tL, tR, wT, wL, wR) => (S.mT * S.dT * wT * Math.cos(tT) + S.mL * S.dL * (wL * Math.cos(tL) + wR * Math.cos(tR))) / m;
  S.wbam = (tT, tL, tR, wT, wL, wR) => (S.IT + S.mT * S.arm(tT) ** 2) * wT + (S.IL + S.mL * S.dL ** 2) * (wL + wR);
  S.torsoH = (tT, wT, frac = 1) => (S.IT + S.mT * S.arm(tT) * S.dT * frac) * wT;
  S.desired = (tL, tR, wL, wR, frac = 1) => { const den = S.mT * S.dT * frac, s = Math.max(-.999, Math.min(.999, -S.mL * S.dL * (Math.sin(tL) + Math.sin(tR)) / den)), th = Math.asin(s);
    return [th, -S.mL * S.dL * (wL * Math.cos(tL) + wR * Math.cos(tR)) / (den * Math.cos(th))]; };
  return S;
};
/* Teaching parameters for the trial model. The human PD must exceed mgl (≈ 700 N·m/rad) to stand at
   all, the step-off margin must lie outside the 0.08 rad dead zone for the exo ever to act, and the exo
   scale is enlarged so its effect is visible. Mechanism only — never compare these numbers with data. */
B.TEACH = { kp: 1000, kd: 200, tmax: 45, margin: .2, exoK: 80, kick: 8 };
B.dist = th => Math.abs(th) <= B.CTRL.dz ? [0, 0] : [B.CTRL.stance, B.CTRL.swing];
/* frequency response of the assistance path: velocity loop × delay × (optional) 2 Hz Butterworth */
B.resp = (fHz, bw = 5, delayMs = 2, filt = true) => {
  const w = 2 * Math.PI * fHz, lagV = Math.atan(fHz / bw), magV = 1 / Math.hypot(1, fHz / bw), lagD = w * delayMs * 1e-3;
  const wn = 2 * Math.PI * B.CTRL.filtHz, re = wn * wn - w * w, im = 2 * B.CTRL.filtZ * wn * w, magF = filt ? wn * wn / Math.hypot(re, im) : 1, lagF = filt ? Math.atan2(im, re) : 0;
  return { mag: magV * magF, db: 20 * Math.log10(magV * magF), lagV: lagV * 180 / Math.PI, lagD: lagD * 180 / Math.PI, lagF: lagF * 180 / Math.PI, total: (lagV + lagD + lagF) * 180 / Math.PI };
};
/* one beam trial (frontal plane, inverted pendulum + published law). o: assist, gain, kick, seed, extra, delayH, bias, noise, comErr */
B.sim = (o = {}) => {
  const S = B.subject(o.h || 1.75, o.m || 75), dt = 1e-3, n = Math.round((o.dur || 12) / dt), r = NN.rng(1000 + (o.seed || 0));
  const extra = o.extra ?? 0, I = S.Iwb() + extra * (.55 * S.h) ** 2, mE = S.m + extra, l = .55 * S.h, g = 9.81;
  const T = B.TEACH, kp = o.kp ?? T.kp, kd = o.kd ?? T.kd, tmax = o.tmax ?? T.tmax, nh = Math.round((o.delayH ?? .12) / dt), nc = 2, gain = o.gain ?? 1, kick0 = o.kick ?? T.kick, assist = !!o.assist;
  const th = new Float64Array(n), w = new Float64Array(n), tA = new Float64Array(n), tH = new Float64Array(n), Hm = new Float64Array(n), He = new Float64Array(n);
  let next = .35, sgn = 1, fy = 0, fyd = 0, act = 0, Hprev = 0, fail = n - 1; const half = .02 + (o.margin ?? T.margin), wn = 2 * Math.PI * 2, a1 = 2 * .707 * wn, a0 = wn * wn, p = 2 * Math.PI * (o.bw || 5);
  for (let k = 1; k < n; k++) {
    const t = k * dt;
    if (t >= next) { next += (1 / 1.15) * (1 + .06 * NN.gauss(r)); sgn = -sgn; w[k - 1] += -sgn * kick0 * (1 + .22 * NN.gauss(r)) / I; }
    const ph = 2 * Math.PI * 1.15 * t, tL = .1 * Math.sin(ph), tR = -tL, wL = .1 * 2 * Math.PI * 1.15 * Math.cos(ph), wR = -wL;
    const wMeas = w[k - 1] + (o.bias || 0) + (o.noise || 0) * NN.gauss(r);
    Hm[k] = S.torsoH(th[k - 1], w[k - 1]); He[k] = S.torsoH(th[k - 1], wMeas, 1 + (o.comErr || 0));
    const dH = (He[k] - Hprev) / dt; Hprev = He[k];
    const [thd, wd] = S.desired(tL, tR, wL, wR, 1 + (o.comErr || 0)), Hd = S.torsoH(thd, wd, 1 + (o.comErr || 0));
    const j = Math.max(0, k - 1 - nh); tH[k] = Math.max(-tmax, Math.min(tmax, -(kp * th[j] + kd * w[j])));
    if (assist) { const jj = Math.max(0, k - 1 - nc), [st, sw] = B.dist(th[jj]); let raw = 0;
      if (st) raw = -Math.sign(th[jj]) * gain * (st + sw) * (o.exoK ?? T.exoK) * (Math.abs(He[k] - Hd) + .02 * Math.abs(dH));
      const ydd = a0 * (raw - fy) - a1 * fyd; fyd += ydd * dt; fy += fyd * dt; act += dt * p * (fy - act); tA[k] = Math.max(-72, Math.min(72, act)); }
    const acc = (mE * g * l * Math.sin(th[k - 1]) + tH[k] + tA[k]) / I; w[k] = w[k - 1] + acc * dt; th[k] = th[k - 1] + w[k] * dt;
    if (Math.abs(l * Math.sin(th[k])) > half) { fail = k; break; }
  }
  const Tend = fail * dt; let pk = 0, duty = 0; for (let k = 0; k <= fail; k++) { pk = Math.max(pk, Math.abs(tA[k])); if (Math.abs(tA[k]) > .5) duty++; }
  return { n: fail + 1, dt, th, w, tA, tH, Hm, He, fell: fail < n - 1, dist: Math.min(5, Tend * .62), pk, duty: duty / (fail + 1), l };
};
B.survival = (o = {}, trials = 18) => {
  const out = {}; [['no assist', false, 6], ['active assist', true, 6], ['baseline', false, 0]].forEach(([lab, assist, extra]) => {
    const d = [...Array(trials)].map((_, i) => B.sim({ ...o, assist, extra, seed: i }).dist);
    out[lab] = { d, pct: 100 * d.reduce((a, b) => a + b, 0) / (trials * 5), curve: [...Array(61)].map((_, k) => [k * 5 / 60, d.filter(x => x >= k * 5 / 60).length / trials]) }; });
  return out;
};
/* draw the three-link frontal-plane figure about the stance foot */
B.figure = (P, S, tT, tL, tR, o = {}) => {
  const foot = [0, 0], hip = [S.lL * Math.sin(tL), S.lL * Math.cos(tL)], head = [hip[0] + S.lT * Math.sin(tT), hip[1] + S.lT * Math.cos(tT)];
  const foot2 = [hip[0] - S.lL * Math.sin(tR), hip[1] - S.lL * Math.cos(tR)];
  P.line([-.6, 0], [.6, 0], '--grey', 2); P.poly([[-.02, 0], [.02, 0], [.02, -.05], [-.02, -.05]], '--b', 1, null, '--b', true);
  P.line(foot, hip, '--e', 7); P.line(hip, foot2, '--d', 6); P.line(hip, head, '--a', 9); P.dot(head, 9, '--a'); P.dot(hip, 6, '--ink', true);
  const com = [S.comX(tT, tL, tR), .55 * S.h]; if (o.com !== false) { P.dot([com[0], com[1] * .6], 6, '--c'); P.line([com[0], 0], [com[0], com[1] * .6], '--c', 1, [3, 3]); }
  return { hip, head, foot2 };
};
})();
