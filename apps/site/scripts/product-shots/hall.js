/*
 * The hall as a drawing (steps «Filmen» and «Prüfen», U1 and U3): a handball court of 40 x 20 m
 * with its goal areas, 9 m lines and goals, in a hall, seen through a camera in true perspective.
 * Calm and sharp in the site's colours (cream, the club's green, ink), no people, no words.
 * step-film looks at it from behind and above the filming phone; step-check from the phone
 * itself, as the picture the app asks about.
 *
 * Metres: x along the court (0 to 40), y across it from the far sideline (0) to the near one
 * (20), z up. `HALL.view({ eye, look, focal, cx, cy })` returns the projection and the drawing
 * helpers; everything it draws is an SVG string in pixels.
 */
(function () {
  const C = {
    paper: "#f7f6f2",
    ground: "#eceae5",
    wall: "#e3dfd6",
    wall2: "#d3cfc6",
    floor: "#dcd6c9",
    court: "#f3ecdc",
    zone: "#10684a",
    ink: "#16171a",
    ink2: "#53565b",
    attn: "#ffd23c",
  };

  const sub = (a, b) => a.map((v, i) => v - b[i]);
  const norm = (a) => a.map((v) => v / Math.hypot(...a));
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
  const f1 = (v) => v.toFixed(1);
  /** a curve: points of f(t) for t from a to b */
  const curve = (f, a, b, n = 40) => Array.from({ length: n + 1 }, (_, i) => f(a + ((b - a) * i) / n));

  function view({ eye, look, focal, cx, cy, line = 1 }) {
    const fwd = norm(sub(look, eye));
    const right = norm(cross(fwd, [0, 0, 1]));
    const up = cross(right, fwd);
    /** a point in metres to px (points behind the camera are pushed just in front of it) */
    function P(p) {
      const d = sub(p, eye);
      const zc = Math.max(0.05, dot(d, fwd));
      return [cx + (focal * dot(d, right)) / zc, cy - (focal * dot(d, up)) / zc];
    }
    /** a point in metres ([x, y, z]) or already in px ([x, y]) */
    const px = (p) => (p.length === 2 ? p : P(p));
    const pts = (list) => list.map((p) => px(p).map(f1).join(" ")).join(" L");
    const poly = (list, attrs) => `<path d="M${pts(list)} Z" ${attrs}/>`;
    const path = (list, attrs) => `<path d="M${pts(list)}" fill="none" ${attrs}/>`;
    const w = (v) => f1(v * line);

    // the goal area of one goal: 6 m quarter circles around the posts and the line between
    function zone(side) {
      const gx = side < 0 ? 0 : 40;
      const s = side < 0 ? 1 : -1;
      return [
        [gx, 2.5, 0],
        ...curve((t) => [gx + s * 6 * Math.cos(t), 8.5 - 6 * Math.sin(t), 0], Math.PI / 2, 0),
        ...curve((t) => [gx + s * 6 * Math.cos(t), 11.5 + 6 * Math.sin(t), 0], 0, Math.PI / 2),
        [gx, 17.5, 0],
      ];
    }
    // the free throw line: 9 m, inside the court
    function nine(side) {
      const gx = side < 0 ? 0 : 40;
      const s = side < 0 ? 1 : -1;
      const a = Math.acos(Math.min(1, 8.5 / 9));
      return [
        ...curve((t) => [gx + s * 9 * Math.cos(t), 8.5 - 9 * Math.sin(t), 0], a, 0),
        ...curve((t) => [gx + s * 9 * Math.cos(t), 11.5 + 9 * Math.sin(t), 0], 0, a),
      ];
    }
    // a goal: 3 x 2 m, posts and bar in ink, the net behind in light lines
    function goal(side) {
      const gx = side < 0 ? 0 : 40;
      const back = side < 0 ? -1 : 41;
      const net = `fill="${C.paper}" fill-opacity=".6" stroke="${C.ink2}" stroke-width="${w(0.8)}"`;
      const bar = `stroke="${C.ink}" stroke-width="${w(3.2)}" stroke-linecap="square"`;
      return [
        poly([[gx, 8.5, 2], [gx, 11.5, 2], [back, 11.5, 1.4], [back, 8.5, 1.4]], net),
        poly([[back, 8.5, 0], [back, 11.5, 0], [back, 11.5, 1.4], [back, 8.5, 1.4]], net),
        poly([[gx, 8.5, 0], [back, 8.5, 0], [back, 8.5, 1.4], [gx, 8.5, 2]], net),
        poly([[gx, 11.5, 0], [back, 11.5, 0], [back, 11.5, 1.4], [gx, 11.5, 2]], net),
        path([[gx, 8.5, 0], [gx, 8.5, 2], [gx, 11.5, 2], [gx, 11.5, 0]], `${bar} stroke-linejoin="miter"`),
      ].join("");
    }

    /**
     * The hall: the far wall (with a gallery rail and a row of high windows), the floor, the
     * court with its lines and the goals. `wallTop` is the wall's height in metres.
     */
    function hall({ wallTop = 9, from = -40, to = 80, near = 40 } = {}) {
      const lineAttr = `stroke="${C.ink}" stroke-width="${w(1.7)}" stroke-linejoin="round"`;
      const out = [];
      out.push(poly([[from, -5, 0], [to, -5, 0], [to, -5, wallTop], [from, -5, wallTop]], `fill="${C.wall}"`));
      // the high windows: a light band under the roof
      for (let x = from; x < to; x += 6) out.push(poly([[x + 0.6, -5, 6.2], [x + 5.4, -5, 6.2], [x + 5.4, -5, 7.8], [x + 0.6, -5, 7.8]], `fill="${C.paper}" fill-opacity=".7"`));
      out.push(path([[from, -5, 3.2], [to, -5, 3.2]], `stroke="${C.wall2}" stroke-width="${w(3)}"`));
      out.push(poly([[from, -5, 0], [to, -5, 0], [to, near, 0], [from, near, 0]], `fill="${C.floor}"`));
      out.push(path([[from, -5, 0], [to, -5, 0]], `stroke="${C.wall2}" stroke-width="${w(2)}"`));
      out.push(poly([[0, 0, 0], [40, 0, 0], [40, 20, 0], [0, 20, 0]], `fill="${C.court}"`));
      for (const s of [-1, 1]) {
        out.push(poly(zone(s), `fill="${C.zone}" stroke="${C.ink}" stroke-width="${w(1.7)}"`));
        out.push(path(nine(s), `stroke="${C.ink}" stroke-width="${w(1.4)}" stroke-dasharray="${w(5)} ${w(4)}"`));
        const gx = s < 0 ? 0 : 40;
        const k = s < 0 ? 1 : -1;
        out.push(path([[gx + k * 7, 9.5, 0], [gx + k * 7, 10.5, 0]], lineAttr));
      }
      out.push(poly([[0, 0, 0], [40, 0, 0], [40, 20, 0], [0, 20, 0]], `fill="none" ${lineAttr}`));
      out.push(path([[20, 0, 0], [20, 20, 0]], lineAttr));
      return out.join("");
    }

    return { P, px, poly, path, curve, zone, nine, goal, hall, C };
  }

  window.HALL = { view, C, curve };
})();
