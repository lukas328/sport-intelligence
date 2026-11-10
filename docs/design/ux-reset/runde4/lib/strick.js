/* Strick: letters, numbers and patterns made of stitches, like the jacquard of a club scarf.
   One pixel is one stitch: a small V of two loops. Two yarns per piece: a (ground) and b (motif). */
var STRICK = (function () {
  var F = {
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00110 01000 10000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    ":": "0 0 1 0 1 0 0", " ": "00 00 00 00 00 00 00", ".": "0 0 0 0 0 0 1", "-": "000 000 000 111 000 000 000", "+": "000 000 010 111 010 000 000",
    "/": "001 001 010 010 010 100 100", "%": "11001 11010 00010 00100 01000 01011 10011",
    "*": "00000 01110 11011 10101 11011 01110 00000",
    A: "01110 10001 10001 11111 10001 10001 10001", B: "11110 10001 10001 11110 10001 10001 11110", C: "01110 10001 10000 10000 10000 10001 01110",
    D: "11110 10001 10001 10001 10001 10001 11110", E: "11111 10000 10000 11110 10000 10000 11111", F: "11111 10000 10000 11110 10000 10000 10000",
    G: "01110 10001 10000 10111 10001 10001 01111", H: "10001 10001 10001 11111 10001 10001 10001", I: "111 010 010 010 010 010 111",
    J: "00111 00010 00010 00010 00010 10010 01100", K: "10001 10010 10100 11000 10100 10010 10001", L: "10000 10000 10000 10000 10000 10000 11111",
    M: "10001 11011 10101 10101 10001 10001 10001", N: "10001 10001 11001 10101 10011 10001 10001", O: "01110 10001 10001 10001 10001 10001 01110",
    P: "11110 10001 10001 11110 10000 10000 10000", R: "11110 10001 10001 11110 10100 10010 10001", S: "01111 10000 10000 01110 00001 00001 11110",
    T: "11111 00100 00100 00100 00100 00100 00100", U: "10001 10001 10001 10001 10001 10001 01110", V: "10001 10001 10001 10001 10001 01010 00100",
    W: "10001 10001 10001 10101 10101 10101 01010", Z: "11111 00001 00010 00100 01000 10000 11111", Y: "10001 10001 01010 00100 00100 00100 00100",
    "Ü": "01010 00000 10001 10001 10001 10001 01110", "Ä": "01010 00000 01110 10001 11111 10001 10001", "Ö": "01010 00000 01110 10001 10001 10001 01110"
  };
  function grid(text, gap) {
    var rows = [[], [], [], [], [], [], []], chars = String(text).toUpperCase().split("");
    chars.forEach(function (ch, i) {
      var g = (F[ch] || F[" "]).split(" ");
      for (var r = 0; r < 7; r++) { for (var c = 0; c < g[r].length; c++) rows[r].push(g[r][c] === "1"); if (i < chars.length - 1) for (var k = 0; k < (gap == null ? 1 : gap); k++) rows[r].push(false); }
    });
    return rows;
  }
  function st(x, y, col) {
    return '<path d="M' + (x + 1) + " " + (y + 0.6) + "c1.3 0 4 3.8 4 9c-2.7-.5-4.7-4.2-4-9Z" + "M" + (x + 9) + " " + (y + 0.6) + "c-1.3 0-4 3.8-4 9c2.7-.5 4.7-4.2 4-9Z" + '" fill="' + col + '"/>';
  }
  function piece(w, h, cell, o, label) {
    var s = '<svg class="knit" viewBox="0 0 ' + w * 10 + " " + h * 10 + '" ' + (label ? 'role="img" aria-label="' + label + '"' : 'aria-hidden="true"') + ' preserveAspectRatio="' + (o.stretch ? "none" : "xMidYMid meet") + '"' + (o.cell ? ' style="width:' + w * o.cell + 'px"' : "") + ">";
    s += '<rect width="' + w * 10 + '" height="' + h * 10 + '" fill="' + (o.a || "var(--yarn-a)") + '"/><rect width="' + w * 10 + '" height="' + h * 10 + '" fill="#000" opacity="' + (o.shade == null ? 0.22 : o.shade) + '"/>';
    for (var r = 0; r < h; r++) for (var c = 0; c < w; c++) s += st(c * 10, r * 10, cell(r, c) ? (o.b || "var(--yarn-b)") : (o.a || "var(--yarn-a)"));
    return s + "</svg>";
  }
  /* knitted text on its own ground */
  function knit(text, o) {
    o = o || {};
    var g = grid(text, o.gap), px = o.padx == null ? 2 : o.padx, py = o.pady == null ? 2 : o.pady, w = g[0].length + px * 2, h = 7 + py * 2;
    return piece(w, h, function (r, c) { return r >= py && r < py + 7 && c >= px && c < px + g[0].length && g[r - py][c - px]; }, o, o.label || text);
  }
  /* a band: one pattern letter per row. a = ground, b = motif, x = checker, k = chevron top, v = chevron bottom, d = dots */
  var ROW = {
    a: function () { return 0; }, b: function () { return 1; }, x: function (c, r) { return (c + r) % 2; },
    k: function (c) { return c % 4 === 0; }, v: function (c) { return c % 4 === 1 || c % 4 === 3; }, d: function (c) { return c % 6 === 3; }
  };
  function band(rows, n, o) { o = o || {}; return piece(n, rows.length, function (r, c) { return ROW[rows[r]](c, r); }, o); }
  /* a band with a repeated name, the way scarves carry it: NAME * NAME * NAME */
  function nameBand(text, n, o) {
    o = o || {}; var unit = grid(text + " * ", 1), L = unit[0].length;
    return piece(n, 11, function (r, c) { if (r < 2 || r > 8) return r === 0 || r === 10; return unit[r - 2][(c + (o.offset || 0)) % L]; }, o, o.label || text);
  }
  /* counting in stitches: n stitches of yarn b, then m of a muted yarn, one row */
  function count(n, m, o) {
    o = o || {}; var s = '<svg class="knit count" viewBox="0 0 ' + (n + m) * 10 + ' 10" aria-hidden="true">';
    for (var i = 0; i < n + m; i++) s += st(i * 10, 0, i < n ? (o.b || "var(--yarn-a)") : (o.m || "#cfcbd2"));
    return s + "</svg>";
  }
  return { knit: knit, band: band, nameBand: nameBand, count: count, grid: grid, st: st, piece: piece };
})();
