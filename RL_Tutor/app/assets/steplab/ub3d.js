/* The G1 figure for the Humanoid Balance labs, posed from the planar model in ub.js.
   With g1mesh.js loaded it is the real Unitree G1 surface (split into feet, legs + pelvis,
   torso + head, upper arms, forearms + hands); without it, a stick figure.
   World axes: x forward, y up, z to the robot's left.
   Pitch = rotation about z (forward lean positive), roll = about x, yaw = about y.
   Needs three.min.js and ub.js loaded first (and g1mesh.js, optional, before this file). */
(function (root) {
const UB3D = {};
const G = {   // stick-figure geometry, metres (G1-like proportions, see ub.js for masses)
  hip: 0.72, torso: 0.36, head: 0.12, shoulderZ: 0.16, footZ: 0.09, footL: 0.2,
  upperArm: 0.22, foreArm: 0.26, legR: 0.045, armR: 0.03,
};
UB3D.G = G;
const mat = (c, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color: new THREE.Color(c), roughness: .55, metalness: .1 }, o));
function rod(len, r, m, dir = 1) {   // a cylinder from the group origin along +y (dir 1) or -y (dir -1)
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 18), m);
  mesh.position.y = dir * len / 2;
  return mesh;
}
/* one part of g1mesh.js -> BufferGeometry (Int16 positions x 1/20000 m, relative to the part's pivot) */
function meshGeom(part) {
  const b = s => Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer;
  const q = new Int16Array(b(part.v)), pos = new Float32Array(q.length);
  for (let i = 0; i < q.length; i++) pos[i] = q[i] / 20000;
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setIndex(new THREE.BufferAttribute(part.i32 ? new Uint32Array(b(part.i)) : new Uint16Array(b(part.i)), 1));
  g.computeVertexNormals();
  return g;
}
UB3D.figure = function (scene, colors) {
  const C = Object.assign({ leg: '#3b4656', torso: '#2a4fd6', arm: '#1f8a4c', head: '#d9b45c', com: '#d9661f', lock: '#8a93a1' }, colors || {});
  const mats = { leg: mat(C.leg), torso: mat(C.torso), arm: mat(C.arm), head: mat(C.head), com: mat(C.com, { emissive: new THREE.Color(C.com), emissiveIntensity: .25 }) };
  const F = {}, M = root.G1MESH;
  F.mesh = !!M;
  // P: joint pivots in the world at rest (left side for the arms); len: joint-to-joint lengths of the figure
  const v3 = a => new THREE.Vector3(a[0], a[1], a[2]);
  const P = M
    ? { ankle: v3(M.pivots.ankle), waist: v3(M.pivots.waist), shoulder: v3(M.pivots.shoulderL), elbow: v3(M.pivots.elbowL) }
    : { ankle: v3([0, 0, 0]), waist: v3([0, G.hip, 0]), shoulder: v3([0, G.hip + G.torso, G.shoulderZ]), elbow: v3([0, G.hip + G.torso - G.upperArm, G.shoulderZ]) };
  const len = { legs: P.waist.y - P.ankle.y, torso: P.shoulder.y - P.waist.y, uarm: P.shoulder.y - P.elbow.y, farm: M ? 0.25 : G.foreArm };
  len.arm = len.uarm + len.farm;
  F.P = P; F.len = len;
  F.ankle = new THREE.Group(); F.ankle.position.copy(P.ankle); scene.add(F.ankle);                        // joint 0: the whole robot pivots here
  F.waist = new THREE.Group(); F.waist.position.set(0, P.waist.y - P.ankle.y, 0); F.ankle.add(F.waist);   // joint 1
  F.shoulders = []; F.elbows = [];
  for (const s of [-1, 1]) {
    const sh = new THREE.Group(); sh.position.set(P.shoulder.x, P.shoulder.y - P.waist.y, s * P.shoulder.z); F.waist.add(sh);   // joint 2
    const el = new THREE.Group(); el.position.set(P.elbow.x - P.shoulder.x, P.elbow.y - P.shoulder.y, 0); sh.add(el);           // joint 3
    F.shoulders.push(sh); F.elbows.push(el);
  }
  if (M) {
    const metal = c => new THREE.MeshStandardMaterial({ color: new THREE.Color(c), roughness: .5, metalness: .25, flatShading: true });
    const mm = { feet: metal('#4a515c'), legs: metal('#5d6776'), torso: metal('#4a6286'), arm: metal('#57806a') };
    const add = (parent, key, m) => parent.add(new THREE.Mesh(meshGeom(M.parts[key]), m));
    const feet = new THREE.Group(); scene.add(feet); add(feet, 'feet', mm.feet);   // the soles stay on the floor
    add(F.ankle, 'legs', mm.legs); add(F.waist, 'torso', mm.torso);
    add(F.shoulders[0], 'uarmR', mm.arm); add(F.shoulders[1], 'uarmL', mm.arm);
    add(F.elbows[0], 'farmR', mm.arm); add(F.elbows[1], 'farmL', mm.arm);
  } else {
    for (const s of [-1, 1]) {
      const leg = rod(G.hip, G.legR, mats.leg); leg.position.z = s * G.footZ; F.ankle.add(leg);
      const foot = new THREE.Mesh(new THREE.BoxGeometry(G.footL, .025, .07), mats.leg); foot.position.set(G.footL * .2, .012, s * G.footZ); F.ankle.add(foot);
    }
    F.pelvis = new THREE.Mesh(new THREE.BoxGeometry(.12, .08, 2 * G.footZ + .06), mats.leg); F.pelvis.position.y = G.hip; F.ankle.add(F.pelvis);
    F.waist.add(rod(G.torso, .05, mats.torso));
    const chest = new THREE.Mesh(new THREE.BoxGeometry(.14, .16, 2 * G.shoulderZ), mats.torso); chest.position.y = G.torso - .08; F.waist.add(chest);
    const head = new THREE.Mesh(new THREE.SphereGeometry(G.head * .6, 20, 14), mats.head); head.position.y = G.torso + G.head; F.waist.add(head);
    F.shoulders.forEach((sh, k) => {
      sh.add(rod(G.upperArm, G.armR, mats.arm, -1));
      sh.add(new THREE.Mesh(new THREE.SphereGeometry(.04, 14, 10), mats.arm));
      const el = F.elbows[k];
      el.add(rod(G.foreArm, G.armR * .9, mats.arm, -1));
      const hand = new THREE.Mesh(new THREE.BoxGeometry(.03, .08, .05), mats.arm); hand.position.y = -G.foreArm - .03; el.add(hand);
    });
  }
  // joint axes: a short bar through each joint, coloured per plane, grey when locked
  F.axes = {};
  const axisMats = { pitch: mat('#c0398a'), roll: mat('#7a4fd0'), yaw: mat('#0f8a86'), lock: mat(C.lock) };
  F.axisMats = axisMats;
  function axis(parent) {
    const g = new THREE.Group(); parent.add(g);
    const bar = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, .5, 10), axisMats.pitch); g.add(bar); g.bar = bar;
    const ring = new THREE.Mesh(new THREE.TorusGeometry(.055, .008, 8, 24), axisMats.lock); ring.visible = false; g.add(ring); g.ring = ring;
    return g;
  }
  F.axes.ankle = axis(F.ankle);
  F.axes.waist = axis(F.waist);
  F.axes.shoulder = F.shoulders.map(axis);
  F.axes.elbow = F.elbows.map(axis);
  // centre-of-mass markers: one per planar link, one for the whole body
  F.comLinks = [0, 1, 2, 3].map(() => { const s = new THREE.Mesh(new THREE.SphereGeometry(.03, 14, 10), mats.com.clone()); scene.add(s); return s; });
  F.com = new THREE.Mesh(new THREE.SphereGeometry(.05, 16, 12), mat('#c23b3b', { emissive: new THREE.Color('#c23b3b'), emissiveIntensity: .35 })); scene.add(F.com);
  F.comDrop = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineDashedMaterial({ color: 0xc23b3b, dashSize: .04, gapSize: .03 })); scene.add(F.comDrop);
  // the markers sit inside the solid robot: draw them on top of it
  [...F.comLinks, F.com, F.comDrop].forEach(o => { o.material.depthTest = false; o.renderOrder = 10; });

  /* pose(plane, q, locks): q = planar joint angles of that plane's chain (ub.js order), locks = booleans per joint */
  F.pose = function (plane, q, locks = []) {
    const rot = (grp, a) => { grp.rotation.set(0, 0, 0); if (plane === 'sagittal') grp.rotation.z = -a; else if (plane === 'frontal') grp.rotation.x = a; else grp.rotation.y = a; };
    const bar = (ax, on) => { ax.bar.rotation.set(0, 0, 0); if (plane === 'sagittal') ax.bar.rotation.x = Math.PI / 2; else if (plane === 'frontal') ax.bar.rotation.z = Math.PI / 2; ax.bar.material = on ? axisMats[plane === 'sagittal' ? 'pitch' : plane === 'frontal' ? 'roll' : 'yaw'] : axisMats.lock; };
    rot(F.ankle, q[0]); rot(F.waist, q[1]);
    if (plane === 'transverse') {
      // the feet twist on the floor (q0), the waist yaws (q1); the arms are held out
      // forward (a 90 degree raise at the shoulder) and then yawed by q2
      F.shoulders.forEach(s => { s.rotation.order = 'YZX'; s.rotation.set(0, q[2] || 0, Math.PI / 2); });
      F.elbows.forEach(e => rot(e, 0));
    } else {
      F.shoulders.forEach(s => { s.rotation.order = 'XYZ'; rot(s, q[2] || 0); }); F.elbows.forEach(e => rot(e, q[3] || 0));
    }
    const names = plane === 'sagittal' ? ['ankle', 'waist', 'shoulder', 'elbow'] : ['ankle', 'waist', 'shoulder'];
    ['ankle', 'waist', 'shoulder', 'elbow'].forEach(nm => {
      const idx = names.indexOf(nm), on = idx >= 0 && !locks[idx], inPlane = idx >= 0;
      (Array.isArray(F.axes[nm]) ? F.axes[nm] : [F.axes[nm]]).forEach(ax => { ax.visible = inPlane; bar(ax, on); ax.ring.visible = inPlane && !on; ax.scale.setScalar(inPlane ? 1 : .001); });
    });
    F.ankle.updateMatrixWorld(true);
  };
  /* planar point (x_p, y_p) of this plane -> world; the sagittal plane is x-y, the frontal plane is z-y, the transverse plane is the floor seen from above */
  F.toWorld = function (plane, p, height) {
    if (plane === 'sagittal') return new THREE.Vector3(p[0], p[1], 0);
    if (plane === 'frontal') return new THREE.Vector3(0, p[1], p[0]);
    return new THREE.Vector3(-p[0], height == null ? P.shoulder.y : height, p[1]);
  };
  /* a point on planar link k, t metres from its joint along the model link, placed on the figure's own
     link (scaled by figure length / model length) so the markers sit on the robot whatever its proportions.
     The model lumps both arms into one link: the point is the mean of the left and right arm.
     Transverse plane (seen from above): the feet and waist points sit on their vertical yaw axis,
     lifted to shoulder height so the arms drawn to them stay level. */
  const chain = { sagittal: [['legs', [F.ankle], 1], ['torso', [F.waist], 1], ['uarm', F.shoulders, -1], ['farm', F.elbows, -1]],
                  frontal: [['legs', [F.ankle], 1], ['torso', [F.waist], 1], ['arm', F.shoulders, -1]] };
  chain.transverse = chain.frontal;
  F.linkPoint = function (plane, links, k, t) {
    const c = chain[plane][k], out = new THREE.Vector3();
    if (plane === 'transverse' && k < 2) return c[1][0].localToWorld(out).setY(P.shoulder.y);
    const s = links[k].L ? t * len[c[0]] / links[k].L : 0;
    c[1].forEach(g => out.add(g.localToWorld(new THREE.Vector3(0, c[2] * s, 0))));
    return out.divideScalar(c[1].length);
  };
  F.jointW = (plane, core, links, i) => F.linkPoint(plane, links, i, 0);
  F.comW = (plane, core, links, k) => F.linkPoint(plane, links, k, links[k].r);
  F.markCom = function (plane, core, links) {
    const mt = links.reduce((s, l) => s + l.m, 0), body = new THREE.Vector3();
    F.comLinks.forEach((s, i) => {
      if (i < core.c.length) { s.visible = true; s.position.copy(F.comW(plane, core, links, i)); body.addScaledVector(s.position, links[i].m / mt); const r = .02 + .012 * Math.cbrt(links[i].m); s.scale.setScalar(r / .03); }
      else s.visible = false;
    });
    if (core.xc) {
      F.com.visible = true; F.com.position.copy(body);
      const pos = F.comDrop.geometry.attributes.position, a = F.com.position, b = plane === 'transverse' ? a.clone() : new THREE.Vector3(a.x, 0, a.z);
      pos.setXYZ(0, a.x, a.y, a.z); pos.setXYZ(1, b.x, b.y, b.z); pos.needsUpdate = true; F.comDrop.computeLineDistances(); F.comDrop.visible = plane !== 'transverse';
    } else { F.com.visible = false; F.comDrop.visible = false; }
  };
  return F;
};

/* a scene with lights, floor grid, orbit by dragging, zoom by wheel; returns {scene, cam, renderer, draw, orbit} */
UB3D.stage = function (canvas, view, opts = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(38, 1.3, .05, 60);
  scene.add(new THREE.AmbientLight(0xffffff, .65));
  const dl = new THREE.DirectionalLight(0xffffff, .8); dl.position.set(2, 5, 3); scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0xffffff, .3); dl2.position.set(-3, 2, -2); scene.add(dl2);
  let grid = null;
  const orbit = Object.assign({ az: .9, el: .35, r: 3.2, tgt: new THREE.Vector3(0, .7, 0) }, opts.orbit || {});
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function colorize() {
    scene.background = new THREE.Color(css('--panel'));
    if (grid) scene.remove(grid);
    grid = new THREE.GridHelper(4, 16, new THREE.Color(css('--line')), new THREE.Color(css('--line'))); scene.add(grid);
  }
  function placeCam() {
    cam.position.set(orbit.tgt.x + orbit.r * Math.cos(orbit.el) * Math.sin(orbit.az), orbit.tgt.y + orbit.r * Math.sin(orbit.el), orbit.tgt.z + orbit.r * Math.cos(orbit.el) * Math.cos(orbit.az));
    cam.lookAt(orbit.tgt);
  }
  function resize() {
    const r = canvas.getBoundingClientRect(), w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (canvas.width !== w * devicePixelRatio || canvas.height !== h * devicePixelRatio) { renderer.setPixelRatio(devicePixelRatio); renderer.setSize(w, h, false); }
    cam.aspect = w / h; cam.updateProjectionMatrix();
  }
  let drag = null;
  canvas.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY]; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => { if (!drag) return; orbit.az -= (e.clientX - drag[0]) * .008; orbit.el = Math.max(-.2, Math.min(1.5, orbit.el + (e.clientY - drag[1]) * .006)); drag = [e.clientX, e.clientY]; S.draw(); });
  ['pointerup', 'pointercancel'].forEach(t => canvas.addEventListener(t, () => drag = null));
  canvas.addEventListener('wheel', e => { e.preventDefault(); orbit.r = Math.max(1.2, Math.min(9, orbit.r * (1 + Math.sign(e.deltaY) * .08))); S.draw(); }, { passive: false });
  const S = { scene, cam, renderer, orbit, colorize, resize, placeCam };
  S.draw = () => { resize(); placeCam(); if (opts.before) opts.before(); renderer.render(scene, cam); if (opts.after) opts.after(); };
  // the camera sits at az = 0 on the +z axis (the robot's left): a side view with forward to the right
  S.view = (name) => { const v = { side: { az: 0, el: .05 }, front: { az: Math.PI / 2, el: .05 }, top: { az: .001, el: 1.5 }, iso: { az: .9, el: .35 } }[name]; Object.assign(orbit, v); S.draw(); };
  S.label = (div, v3, html, color) => {   // an HTML label pinned to a 3-D point
    const p = v3.clone().project(cam); if (p.z > 1 || !html) { div.hidden = true; return; }
    const r = canvas.getBoundingClientRect(), vr = view.getBoundingClientRect();
    div.hidden = false; div.innerHTML = html; div.style.color = color || '';
    div.style.left = (r.left - vr.left + (p.x + 1) / 2 * r.width) + 'px'; div.style.top = (r.top - vr.top + (1 - p.y) / 2 * r.height) + 'px';
  };
  colorize();
  new MutationObserver(() => { colorize(); S.draw(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  window.addEventListener('resize', () => S.draw());
  return S;
};
root.UB3D = UB3D;
})(window);
