/* Fault-tolerant knee prosthesis teaching model for the step labs (pages 105-113).
   A JS port of ctrlcore/faulttol.py. RES and the parameter sets are as in that module;
   simulated strides are a single-joint teaching model, not the experiment. */
(function () {
const F = window.FAULT = {};
F.RES = { sens: 100, far: 10.8, farSd: 10, det: 54.4, detSd: 28.7, detOk: 43.1, detOkSd: 11.5, detLate: 103.5, mom: 47, momOther: 27.6,
  momConds: [['0.4 m/s', 30.6, 8.3], ['0.8 m/s', 17.3, 2.1], ['4.6° ramp', 35.9, 1.1]], impTrue: .099, impFalse: .021, impP: .0034,
  rail: 15, railZ: 2.41, railP: .016, railD: 1.12, critWithout: [87, 9], critWith: [15, 11], nrmse: { normal: .14, with: .38, without: 1.61 },
  mos: 46, mosWithP: .062, mosWithD: .74, mosWithoutD: 1.72, railPctWithout: 50, railPctWith: 10, falseMosP: .95 };
F.PARAMS = { nominal: { SF: [180, 4, .12], SE: [95, 3, .05] }, 'ramp ascent': { SF: [250, 5, .26], SE: [150, 3.5, .16] }, 'ramp descent': { SF: [120, 6.5, .30], SE: [70, 5, .22] },
  'stair ascent': { SF: [300, 5.5, .40], SE: [190, 4, .30] }, 'stair descent': { SF: [90, 8, .45], SE: [60, 6, .35] } };
/* teaching-model constants (not from the paper): deviation gain and relaxation, sensor-noise default, compensation gain */
F.TEACH = { gain: .25, tauD: .08, noise: .1, comp: 1 };
F.MODES = ['ramp ascent', 'ramp descent', 'stair ascent', 'stair descent'];
F.blend = (mode, a) => { const n = F.PARAMS.nominal, o = F.PARAMS[mode], out = {}; for (const s in n) out[s] = n[s].map((p, i) => p + a * (o[s][i] - p)); return out; };
F.knee = (m = 75, h = 1.75) => { const K = { m, h, msh: .061 * m, lsh: .285 * h, mth: .1 * m, lth: .245 * h }; K.J = K.msh * K.lsh ** 2 / 3; K.Ith = K.mth * K.lth ** 2 / 3; K.H = (wth, wsh) => K.Ith * wth + K.J * wsh; return K; };
F.load = (t, T = 1.25, bw = 735) => { const ph = (t / T) % 1; if (ph >= .62) return 0; const x = ph / .62; return bw * Math.pow(Math.sin(Math.PI * x), .6) * (1 + .18 * Math.cos(2 * Math.PI * x)); };
F.nominal = (t, T = 1.25) => { const ph = (t / T) % 1; return [.55 * Math.sin(2 * Math.PI * ph) + 1.9 * Math.exp(-(((ph - .72) / .06) ** 2)) - 1.5 * Math.exp(-(((ph - .88) / .07) ** 2)), .16 + .1 * Math.exp(-(((ph - .72) / .1) ** 2))]; };
F.state = ph => ph < .3 ? 'SF' : ph < .62 ? 'SE' : ph < .85 ? 'SwF' : 'SwE';
F.tau = (P, s, th, w) => P[s] ? -P[s][0] * (th - P[s][2]) - P[s][1] * w : 0;
/* one stride: o = {mode, alpha, fstate, ftm, k, nc, falseAlarm, seed, noise, faultMs} */
F.trial = (o = {}) => {
  const kn = F.knee(), dt = 1e-3, T = 1.25, n = Math.round(T / dt), r = NN.rng(500 + (o.seed ?? 3));
  const nom = F.PARAMS.nominal, bad = F.blend(o.mode || 'ramp ascent', o.alpha ?? 1), k = o.k ?? 1, nc = o.nc ?? 10, noise = o.noise ?? F.TEACH.noise;
  const out = { t: [], th: [], w: [], mu: [], sg: [], res: [], thr: [], tb: [], tf: [], H: [], Hn: [], st: [] };
  let th = 0, run = 0, active = false, aState = null, det = null, anyHit = null, fy = 0, fyd = 0, dv = 0, nz = 0; const G = o.gain ?? F.TEACH.gain, tauD = F.TEACH.tauD, rho = .97; const wn = 2 * Math.PI * 15, a1 = Math.SQRT2 * wn, a0 = wn * wn;
  const k0 = Math.round(({ SF: .12, SE: .4 }[o.fstate || 'SE']) * n), k1 = k0 + Math.round((o.faultMs ?? 200) / 1e3 / dt), fa0 = Math.round(.22 * n), fa1 = fa0 + 40;
  for (let i = 0; i < n; i++) {
    const t = i * dt, ph = t / T, s = F.state(ph), [mu, sg] = F.nominal(t), P = i >= k0 && i < k1 ? bad : nom;
    const prevW = i ? out.w[i - 1] : mu, tb = F.tau(P, s, th, prevW), tn = F.tau(nom, s, th, prevW), tfPrev = i ? out.tf[i - 1] : 0;
    /* teaching dynamics: the torque error (minus whatever the FTM adds back) drives a velocity deviation that
       builds up and relaxes with time constant tauD, so detection time depends on severity and threshold */
    dv += dt * ((tb + tfPrev - tn) / kn.J * G - dv / tauD); nz = rho * nz + noise * Math.sqrt(1 - rho * rho) * NN.gauss(r);
    const w = mu + dv + nz, H = kn.H(.35 * w, w), Hn = kn.H(.35 * mu, mu), res = w - mu, thr = Math.abs(mu) + k * sg;
    run = Math.abs(res) > thr ? run + 1 : 0; let hit = run >= nc; if (o.falseAlarm && i >= fa0 && i < fa1) hit = true;
    if (hit && anyHit === null) anyHit = i;
    if (hit && !active && (s === 'SF' || s === 'SE')) { active = true; aState = s; if (det === null && i >= k0 && !o.falseAlarm) det = i; }
    if (active && s !== aState) { if (Math.abs(res) < thr) active = false; else aState = s; }
    let raw = 0; if (o.ftm !== false && active) raw = F.TEACH.comp * (F.tau(nom, s, th, mu) - F.tau(nom, s, th, w) + 28 * (Hn - H));
    const ydd = a0 * (raw - fy) - a1 * fyd; fyd += ydd * dt; fy += fyd * dt; const tf = o.ftm !== false ? fy : 0;
    th += w * dt + .5 * ((tb + tf - tn) / kn.J) * dt * dt;
    out.t.push(t); out.th.push(th); out.w.push(w); out.mu.push(mu); out.sg.push(sg); out.res.push(res); out.thr.push(thr); out.tb.push(tb); out.tf.push(tf); out.H.push(H); out.Hn.push(Hn); out.st.push(s);
  }
  let dev = 0, hmin = Infinity, hmax = -Infinity, imp = 0; for (let i = 0; i < n; i++) { dev += (out.H[i] - out.Hn[i]) ** 2; hmin = Math.min(hmin, out.Hn[i]); hmax = Math.max(hmax, out.Hn[i]); imp += Math.abs(out.tf[i]) * dt; }
  out.nrmse = Math.sqrt(dev / n) / ((hmax - hmin) || 1); out.impulse = imp / kn.m; out.detMs = det === null ? null : (det - k0); out.anyHit = anyHit; out.win = [k0 * dt, k1 * dt]; out.k0 = k0; out.k1 = k1; out.det = det;
  return out;
};
F.roc = (ks, strides = 12, o = {}) => ks.map(k => { let hits = 0, fps = 0; const times = [];
  for (let s = 0; s < strides; s++) { const a = F.trial({ ...o, k, ftm: false, seed: s }); if (a.detMs !== null) { hits++; times.push(a.detMs); } if (F.trial({ ...o, k, ftm: false, alpha: 0, seed: 100 + s }).anyHit !== null) fps++; }
  return { k, sens: 100 * hits / strides, far: 100 * fps / strides, det: times.length ? times.reduce((a, b) => a + b, 0) / times.length : NaN }; });
/* margin of stability under a 200 ms CoM-acceleration pulse, compensated after detection */
F.mos = (detMs = 54, comp = true, faultMs = 200) => { const dt = 1e-3, n = 1000, k0 = 200, k1 = k0 + faultMs, kd = k0 + detMs; let v = 0, x = 0; const out = [];
  for (let i = 0; i < n; i++) { let a = i >= k0 && i < k1 ? 1.35 : 0; if (comp && i >= kd) a *= .15; v += a * dt; x += v * dt; out.push([i * dt, .11 - (x + v / Math.sqrt(9.81 / .95))]); } return out; };
})();
