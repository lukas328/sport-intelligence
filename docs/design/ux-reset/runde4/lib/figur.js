/* Printed figures: handball in motion, cut like a linocut and printed in two inks
   (ink and club colour), slightly off register. One pose per situation. */
var FIGUR = (function () {
  /* joints: head, neck, hip, arms [elbow, hand] x2 (back, front), legs [knee, foot] x2 (back, front) */
  var POSE = {
    wurf:   { h: [94, 40], n: [90, 57], p: [84, 106], a: [[[70, 42], [76, 16]], [[110, 72], [128, 66]]], l: [[[70, 130], [58, 150]], [[104, 126], [100, 158]]], ball: [78, 9], air: 1 },
    abwehr: { h: [100, 42], n: [100, 58], p: [100, 112], a: [[[82, 38], [80, 12]], [[118, 38], [120, 12]]], l: [[[86, 142], [74, 182]], [[116, 142], [128, 182]]] },
    sprint: { h: [124, 46], n: [113, 61], p: [92, 104], a: [[[92, 78], [76, 92]], [[130, 82], [140, 64]]], l: [[[74, 128], [50, 136]], [[118, 132], [112, 180]]] },
    fang:   { h: [104, 44], n: [101, 60], p: [94, 112], a: [[[122, 54], [142, 42]], [[120, 64], [140, 54]]], l: [[[84, 146], [78, 182]], [[110, 146], [124, 182]]], ball: [152, 42] },
    parade: { h: [100, 38], n: [100, 54], p: [100, 102], a: [[[72, 42], [48, 24]], [[128, 42], [152, 24]]], l: [[[78, 132], [56, 162]], [[122, 132], [144, 162]]], air: 1 },
    jubel:  { h: [100, 40], n: [100, 56], p: [98, 106], a: [[[80, 32], [72, 8]], [[122, 32], [130, 8]]], l: [[[92, 144], [90, 184]], [[118, 132], [136, 150]]], air: 0 },
    lauf:   { h: [108, 42], n: [102, 58], p: [92, 106], a: [[[86, 78], [74, 96]], [[120, 76], [132, 60]]], l: [[[80, 140], [62, 174]], [[112, 136], [120, 180]]], ball: [140, 52] }
  };
  var uid = 0;
  function limb(a, b, c, w) { return '<path d="M' + a + "L" + b + "L" + c + '" fill="none" stroke-width="' + w + '" stroke-linecap="round" stroke-linejoin="round"/>'; }
  function draw(name, o) {
    o = o || {};
    var P = POSE[name], id = "fg" + (++uid), num = o.no || "", rough = o.rough !== false;
    var n = P.n, p = P.p, dx = p[0] - n[0], dy = p[1] - n[1], L = Math.hypot(dx, dy), ux = -dy / L, uy = dx / L;
    var sh = 19, hw = 14;
    var torso = [[n[0] + ux * sh, n[1] + uy * sh], [n[0] - ux * sh, n[1] - uy * sh], [p[0] - ux * hw, p[1] - uy * hw], [p[0] + ux * hw, p[1] + uy * hw]];
    var tp = "M" + torso.map(function (q) { return q[0].toFixed(1) + " " + q[1].toFixed(1); }).join("L") + "Z";
    var s = '<svg class="fig" viewBox="0 0 200 200" aria-hidden="true">';
    if (rough) s += '<defs><filter id="' + id + '" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="' + (uid * 7) + '" result="t"/><feDisplacementMap in="SourceGraphic" in2="t" scale="3.2" result="d"/><feTurbulence type="fractalNoise" baseFrequency="2.2" numOctaves="1" seed="' + (uid * 3) + '" result="g"/><feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -14 9.6" result="m"/><feComposite in="d" in2="m" operator="in"/></filter></defs>';
    var f = rough ? ' filter="url(#' + id + ')"' : "";
    s += '<ellipse cx="' + p[0] + '" cy="' + (P.air ? 192 : 188) + '" rx="' + (P.air ? 26 : 40) + '" ry="5" fill="var(--ink)" opacity="' + (P.air ? 0.35 : 0.9) + '"' + f + "/>";
    /* ink plate */
    s += '<g stroke="var(--ink)" fill="var(--ink)"' + f + ">";
    s += limb(p, P.l[0][0], P.l[0][1], 15) + limb(n, P.a[0][0], P.a[0][1], 12);
    s += '<path d="' + tp + '" stroke-width="5" stroke-linejoin="round"/>';
    s += limb(p, P.l[1][0], P.l[1][1], 15) + limb(n, P.a[1][0], P.a[1][1], 12);
    s += '<circle cx="' + P.h[0] + '" cy="' + P.h[1] + '" r="15"/>';
    s += '<path d="M' + (p[0] - ux * 17) + " " + (p[1] - uy * 17) + "L" + (p[0] + ux * 17) + " " + (p[1] + uy * 17) + '" stroke-width="18" stroke-linecap="round"/>';
    s += "</g>";
    /* club plate, off register */
    s += '<g transform="translate(2.5 -2)"' + f + '><path d="' + tp + '" fill="var(--club)" transform="translate(' + (ux * -1).toFixed(1) + " " + (uy * -1).toFixed(1) + ') "/>';
    if (num) { var cx = (n[0] + p[0]) / 2, cy = (n[1] + p[1]) / 2 + 2, ang = Math.atan2(dy, dx) * 180 / Math.PI - 90; s += '<text x="' + cx + '" y="' + (cy + 8) + '" text-anchor="middle" transform="rotate(' + ang.toFixed(0) + " " + cx + " " + cy + ')" style="font:900 22px var(--disp,sans-serif);fill:var(--club-ink)">' + num + "</text>"; }
    s += "</g>";
    if (P.ball) s += '<g' + f + '><circle cx="' + P.ball[0] + '" cy="' + P.ball[1] + '" r="10" fill="var(--paper)" stroke="var(--ink)" stroke-width="3.5"/><path d="M' + (P.ball[0] - 9) + " " + P.ball[1] + "Q" + P.ball[0] + " " + (P.ball[1] - 6) + " " + (P.ball[0] + 9) + " " + P.ball[1] + "M" + P.ball[0] + " " + (P.ball[1] - 9) + "Q" + (P.ball[0] + 5) + " " + P.ball[1] + " " + P.ball[0] + " " + (P.ball[1] + 9) + '" fill="none" stroke="var(--ink)" stroke-width="2.4"/></g>';
    return s + "</svg>";
  }
  return { draw: draw, POSE: POSE };
})();
