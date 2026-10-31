/* Page 94 toy: a fixed non-diagonal coupling from two PC weights to five landmark errors,
   optimum at w = (0, 0), plus stride noise. A real DDPG with replay and target networks learns it. */
window.KNEE = {
  C: [[.8, .3], [.2, .9], [-.5, .4], [1.2, -.6], [.4, .7]], lrc: 1e-3, lra: 2e-4, gam: .9, alpha: [.1, .1, .1, .4, .3], lam: .02, beta: 2, step: .15, clamp: w => w.map(x => Math.max(-2, Math.min(2, x))),
  errs: (w, noise, r) => KNEE.C.map(c => c[0] * w[0] + c[1] * w[1] + noise * NN.gauss(r)),
  reward: (e, a) => -e.reduce((s, x, i) => s + KNEE.alpha[i] * Math.abs(x), 0) - KNEE.lam * (Math.abs(a[0]) + Math.abs(a[1])) - (Math.abs(e[3]) > 1.8 ? KNEE.beta : 0),
  train(sessions, noise, sig, strides = 30) {
    const r = NN.rng(11), A = { actor: NN.net([5, 24, 24, 2], ['tanh', 'tanh', 'tanh'], 3, 3e-3), critic: NN.net([7, 32, 32, 1], ['tanh', 'tanh', 'linear'], 4, 3e-3), sa: {}, sc: {}, buf: [], curve: [] };
    A.at = NN.clone(A.actor); A.ct = NN.clone(A.critic);
    const mu = (net, s) => NN.forward(net, s).a[3]; const soft = (T, N, tau) => T.forEach((l, k) => { l.W.forEach((row, i) => row.forEach((_, j) => row[j] += tau * (N[k].W[i][j] - row[j]))); l.b.forEach((_, j) => l.b[j] += tau * (N[k].b[j] - l.b[j])); });
    for (let ss = 0; ss < sessions; ss++) {
      let w = [2.4 * r() - 1.2, 2.4 * r() - 1.2], e = KNEE.errs(w, noise, r), tot = 0;
      for (let t = 0; t < strides; t++) {
        const m = mu(A.actor, e), a = m.map(x => Math.max(-1, Math.min(1, x + sig * NN.gauss(r))));
        w = KNEE.clamp([w[0] + KNEE.step * a[0], w[1] + KNEE.step * a[1]]); const e2 = KNEE.errs(w, noise, r), rew = KNEE.reward(e2, a); tot += rew;
        A.buf.push([e, a, rew, e2]); if (A.buf.length > 20000) A.buf.shift(); e = e2;
        if (A.buf.length < 64) continue;
        const B = [...Array(32)].map(() => A.buf[Math.floor(r() * A.buf.length)]), gc = NN.acc(A.critic), ga = NN.acc(A.actor);
        B.forEach(([s, a2, rw, s2]) => { const y = rw + KNEE.gam * NN.forward(A.ct, [...s2, ...mu(A.at, s2)]).a[3][0], c = NN.forward(A.critic, [...s, ...a2]); gc.add(NN.backward(A.critic, c, [2 * (c.a[3][0] - y)]), 1 / 32); });
        NN.adam(A.critic, gc, KNEE.lrc, A.sc);
        B.forEach(([s]) => { const ca = NN.forward(A.actor, s), cc = NN.forward(A.critic, [...s, ...ca.a[3]]), dx = NN.backward(A.critic, cc, [1]).dx; ga.add(NN.backward(A.actor, ca, [-dx[5], -dx[6]]), 1 / 32); });
        NN.adam(A.actor, ga, KNEE.lra, A.sa); soft(A.at, A.actor, .01); soft(A.ct, A.critic, .01);
      }
      A.curve.push(tot / strides);
    }
    /* one greedy episode from a deliberately bad start */
    const rg = NN.rng(99); let w = [1, -1]; const path = [w.slice()], e0 = KNEE.errs(w, noise, rg); let e = e0;
    for (let t = 0; t < strides; t++) { const a = mu(A.actor, e); w = KNEE.clamp([w[0] + KNEE.step * a[0], w[1] + KNEE.step * a[1]]); path.push(w.slice()); e = KNEE.errs(w, noise, rg); }
    A.path = path; A.e0 = e0; A.e1 = e; A.strides = sessions * strides; return A;
  },
};
