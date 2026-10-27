/* The RRPR workshop arm drawn with Scene3D primitives (port of app/pages/rrpr_render.py).
   drawRRPR(sc, q, {ghost, focus, frames, alpha}) */
(function () {
const JC = ['--b', '--d', '--f', '--e'];          // waist, shoulder, slide, roll
window.RRPR_JC = JC;
window.rrprGeometry = q => {
  const S = MR.RRPR.S, E = S.map((s, i) => MR.expTwist(s, q[i]));
  const T1 = E[0], T2 = MR.mul(T1, E[1]), T3 = MR.mul(T2, E[2]), T = MR.fkSpace(MR.RRPR.M, S, q);
  const shoulder = [0, 0, 1], arm = MR.mv(MR.Rof(T2), [1, 0, 0]);
  const wrist = MR.add(MR.mv(MR.Rof(T3), [1, 0, 1]), MR.pof(T3));
  return { T1, T2, T3, T, shoulder, arm, wrist, ax1: [0, 0, 1], ax2: MR.mv(MR.Rof(T1), [0, -1, 0]) };
};
window.drawRRPR = (sc, q, o = {}) => {
  const g = rrprGeometry(q), gh = o.ghost, op = gh ? { opacity: .22 } : (o.alpha ? { opacity: o.alpha } : undefined);
  const LINK = gh ? '--grey' : '--link', HAND = gh ? '--grey' : '--ink', jc = i => gh ? '--grey' : JC[i];
  const cylC = (c, ax, r, h, col) => sc.cyl(MR.add(c, MR.scl(ax, -h / 2)), MR.add(c, MR.scl(ax, h / 2)), r, col, op);
  if (!gh) cylC([0, 0, -.14], [0, 0, 1], .26, .24, '--grey');
  cylC([0, 0, .03], [0, 0, 1], .22, .06, jc(0));
  sc.cyl([0, 0, .06], [0, 0, .9], .07, LINK, op);
  cylC(g.shoulder, g.ax2, .11, .32, jc(1));
  const sh = g.shoulder, arm = g.arm, wr = g.wrist;
  sc.cyl(sh, MR.add(sh, MR.scl(arm, .8)), .075, LINK, op);
  sc.cyl(MR.add(sh, MR.scl(arm, .6)), wr, .045, jc(2), op);
  cylC(MR.add(wr, MR.scl(arm, .07)), arm, .1, .14, jc(3));
  const T = g.T, R = MR.Rof(T), B = p => MR.add(MR.mv(R, p), MR.pof(T)), ex = MR.col(R, 0);
  cylC(B([-.27, 0, -.2]), ex, .045, .46, HAND);
  sc.cyl(B([0, 0, -.24]), B([0, 0, -.02]), .035, HAND, op);
  sc.cyl(B([-.02, -.09, -.02]), B([-.02, .09, -.02]), .025, HAND, op);
  [-1, 1].forEach(s => sc.cyl(B([0, .075 * s, -.02]), B([0, .075 * s, .12]), .018, HAND, op));
  if (o.frames !== false && !gh) sc.frame(T, .3);
  return g;
};
/* current screw axis of joint i drawn as a long dashed line (revolute) or arrow (prismatic) */
window.drawAxis = (sc, Si, col, label) => {
  const w = Si.slice(0, 3), v = Si.slice(3);
  if (MR.norm(w) < 1e-9) { const p0 = [0, 0, 0]; return { prismatic: true, dir: v }; }
  const q = MR.cross(w, v);                     // point on the axis closest to the origin (|ω| = 1)
  sc.line([MR.add(q, MR.scl(w, -1.2)), MR.add(q, MR.scl(w, 1.4))], col, true);
  sc.arrow(MR.add(q, MR.scl(w, .9)), MR.scl(w, .4), col, 1, .12);
  if (label) sc.label(MR.add(q, MR.scl(w, 1.45)), label, col);
  return { q, w };
};
})();
