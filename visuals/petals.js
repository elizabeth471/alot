/* Petals: the projector's Flower look, drawn in 2D on its own layer.
   Four whorls of translucent petals (7, 9, 11, 13 a day, never evenly spaced),
   each with a soft body and a fine rose-gold to aqua edge, everything added as
   light. A new flower each day. The host calls backdrop(ctx, state) each frame
   and passes the projector's own fade as `exposure`. */
(function () {
  "use strict";
  var TAU = Math.PI * 2;
  var PEARL = [236, 226, 236];
  var ROSE  = [255, 200, 172];
  var AQUA  = [172, 236, 228];
  var HEART = "255,214,176";
  var DIST = 4.2;
  var LEAN = 0.56;
  var WHORLS = 4;
  var COUNTS = [7, 9, 11, 13];
  var C = 0, R = 0, CX = 0, CY = 0;
  function seeded(n) {
    var a = Math.imul(n | 0, 2654435761) >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hash(i) {
    return (Math.imul(i ^ 0x9e3779b9, 2246822507) >>> 8) / 16777216;
  }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function gentle(x) { x = clamp(x, 0, 1); return x * x * x * (x * (x * 6 - 15) + 10); }
  function steady(x) {
    x = clamp(x, 0, 1);
    var e = 0.12, v = 1 / (1 - e);
    if (x < e) return v * x * x / (2 * e);
    if (x > 1 - e) return 1 - v * (1 - x) * (1 - x) / (2 * e);
    return v * (x - e / 2);
  }
  function easeOut(x) { x = clamp(x, 0, 1); return 1 - Math.pow(1 - x, 3); }
  var petals = [], rings = [], grownFor = null, REACH = 3, NALL = 196;
  function grow(dayIdx) {
    var rnd = seeded(dayIdx * 7919 + 17);
    var counts = COUNTS.slice();
    for (var i = counts.length - 1; i > 0; i--) {
      var j = Math.floor(rnd() * (i + 1));
      var tmp = counts[i]; counts[i] = counts[j]; counts[j] = tmp;
    }
    petals = [];
    for (var w = 0; w < WHORLS; w++) {
      var n = counts[w];
      var outer = w / (WHORLS - 1);
      var phase0 = rnd() * TAU;
      for (var k = 0; k < n; k++) {
        var a = phase0 + ((k + (rnd() - 0.5) * 0.76) / n) * TAU;
        petals.push({
          w: w,
          a: a,
          root: 0.075 + 0.05 * outer + rnd() * 0.03,
          len: (0.34 + 0.44 * outer) * (0.88 + rnd() * 0.22),
          wid: (0.15 + 0.17 * outer) * (0.80 + rnd() * 0.42),
          rise: (1.18 - 0.86 * outer) + (rnd() - 0.5) * 0.20,
          curl: (0.15 + 0.55 * outer) * (0.7 + rnd() * 0.6),
          ruf1: rnd() * TAU, ruf2: rnd() * TAU,
          rufA: 0.035 + rnd() * 0.05,
          ph: rnd() * TAU,
          vein: 0.6 + rnd() * 0.4,
        });
      }
    }
    petals.sort(function (p, q) { return q.w - p.w; });
    /* FILLING THE SCREEN WITH PETALS, NOT A ZOOM (Ely, 2026-11-09). Beyond the four whorls, rings of more and more
       petals wait closed; as the flower spreads they open one ring after another, from the flower outward, until
       they reach past every edge, then fold closed again from the outside in. Counts are primes past the flower's
       own (no 5, 6, 8, 12 or 16), never evenly spaced, the same jitter as the whorls. Radii are fractions of the
       reach, which the screen sets each frame. */
    rings = [];
    var RC = [17, 19, 23, 29, 31, 37];
    for (var rk = 0; rk < RC.length; rk++) {
      var rn = RC[rk], f = (rk + 1) / RC.length, ph0r = rnd() * TAU;
      for (var rq = 0; rq < rn; rq++) {
        rings.push({
          w: WHORLS - 1, ring: f, n: rn,
          a: ph0r + ((rq + (rnd() - 0.5) * 0.76) / rn) * TAU,
          lenJ: 0.88 + rnd() * 0.22, widJ: 0.80 + rnd() * 0.42, rootJ: rnd(),
          rise: 0.22 + (rnd() - 0.5) * 0.14, curl: (0.35 + 0.3 * rnd()),
          ruf1: rnd() * TAU, ruf2: rnd() * TAU, rufA: 0.035 + rnd() * 0.05,
          ph: rnd() * TAU, vein: 0.6 + rnd() * 0.4, late: rnd()
        });
      }
    }
    rings.sort(function (p, q) { return q.ring - p.ring; });
    /* every petal gets a place in each new shape: a shuffled slot and three randoms of its own */
    var all = petals.concat(rings), order = [];
    for (var oi = 0; oi < petals.length; oi++) order.push(oi);
    for (oi = order.length - 1; oi > 0; oi--) { var oj = Math.floor(rnd() * (oi + 1)); var ot = order[oi]; order[oi] = order[oj]; order[oj] = ot; }
    for (oi = 0; oi < all.length; oi++) {
      var pp = all[oi];
      pp.slot = oi < order.length ? order[oi] : -1; pp.r1 = rnd(); pp.r2 = rnd(); pp.r3 = rnd();
      if (pp.late == null) pp.late = rnd();
    }
    NALL = petals.length;
  }
  var cL = 1, sL = 0, cY = 1, sY = 0;
  function setView(lean, yaw) {
    cL = Math.cos(lean); sL = Math.sin(lean);
    cY = Math.cos(yaw);  sY = Math.sin(yaw);
  }
  var P = { x: 0, y: 0, k: 1, z: 0 };
  function project(x, y, h, rad) {
    var X = x, Y = y, Z = -h;
    var X1 = X * cY + Z * sY, Z1 = -X * sY + Z * cY;
    var Y2 = Y * cL + Z1 * sL, Z2 = -Y * sL + Z1 * cL;
    var k = DIST / (DIST + Z2);
    P.x = CX + X1 * rad * k; P.y = CY + Y2 * rad * k; P.k = k; P.z = Z2;
    return P;
  }
  var SPN = 16, spR = new Float32Array(SPN + 1), spH = new Float32Array(SPN + 1);
  function spine(pt, open, ext) {
    var r = pt.root, h = 0;
    spR[0] = r; spH[0] = 0;
    var L = pt.len * (0.32 + 0.68 * open) * (1 + (ext || 0));
    var rise = pt.rise * (1 - 0.62 * open) + 1.42 * (1 - open) * 0.62;
    for (var i = 1; i <= SPN; i++) {
      var u = i / SPN;
      var ang = rise - pt.curl * u * u * open;
      var d = L / SPN;
      r += Math.cos(ang) * d;
      h += Math.sin(ang) * d;
      spR[i] = r; spH[i] = h;
    }
  }
  function halfW(u) {
    return Math.pow(Math.sin(Math.PI * Math.min(1, u * 0.86 + 0.07)), 0.75)
         * Math.min(1, u * 3.2);
  }
  function surface(r, open) {
    return 0.05 + 0.20 * Math.max(0, 1 - r / 0.95) * (0.8 + 0.2 * open);
  }
  function mix(a, b, f) {
    return Math.round(a[0] + (b[0] - a[0]) * f) + "," +
           Math.round(a[1] + (b[1] - a[1]) * f) + "," +
           Math.round(a[2] + (b[2] - a[2]) * f);
  }
  function crowdOf(n) {
    return Math.max(0.16, Math.min(1, Math.pow(150 / Math.max(1, n), 0.40)));
  }
  var bornAt = 0, hov = 0, lastDrag = 0;
  var trail = [0, 0, 0, 0];
  var tvel = [0, 0, 0, 0];
  var turnS = 0, omega = 0, stirPh = 0;
  var UNFURL_MS = 6200;
  var FLOWER_AT = 200;
  var BUD_MS = 1100;
  var DRAW_MS = 14000, TANGLE_MS = 500, PULL_MS = 7000, LET_GO = 3000;
  var STILL_MS = 500, REST_GLOW_MS = 500;
  var SCRIBBLE = false;
  var SCRIB = SCRIBBLE ? STILL_MS + DRAW_MS + TANGLE_MS + PULL_MS : 0;
  var HALF = 0.45;
  var CALM = 0.25;
  var WAVE = 0.08;
  var SPARKS = 1;
  var COLLECT = null;
  var REST = 1.2;
  var BIG = 0;
  var BLOOM_UP = 6200, BLOOM_HOLD = 1400, BLOOM_DOWN = 6200, MORPH = 9000;
  var EX = [], EY = [];
  function smoothPath(ctx, a, b, closed) {
    ctx.moveTo(closed ? (EX[a] + EX[b - 1]) / 2 : EX[a],
               closed ? (EY[a] + EY[b - 1]) / 2 : EY[a]);
    for (var i = a; i < b - 1; i++) {
      ctx.quadraticCurveTo(EX[i], EY[i], (EX[i] + EX[i + 1]) / 2, (EY[i] + EY[i + 1]) / 2);
    }
    if (closed) ctx.quadraticCurveTo(EX[b - 1], EY[b - 1],
                                     (EX[a] + EX[b - 1]) / 2, (EY[a] + EY[b - 1]) / 2);
    else ctx.lineTo(EX[b - 1], EY[b - 1]);
  }
  var fullNext = false;
  /* THE FLOWER OPENS, CLOSES, AND BECOMES SOMETHING ELSE (Ely, 2026-11-09). Two movements, taking turns:
     · open: from the heart outward more and more petals open, the flower's own whorls moving out and ring after ring
       beyond them, until the screen is full of petals and the very centre is bare; then exactly the same, backwards.
     · become: with no warning and no fill, the flower's own forty petals drift, each on its own time, into a new
       creature (a fish, a jellyfish, a ray), swim there a while, and drift back into the flower.
     The order: open, become a fish, flower, open, a jellyfish, flower, open, a ray, flower, and round again. */
  var SCENES = ["flower", "fish", "jellyfish", "ray"];
  var STEPS = [["open", 0], ["become", 1], ["become", 0], ["open", 0], ["become", 2], ["become", 0], ["open", 0], ["become", 3], ["become", 0]];
  var scene = 0, trFrom = 0, trTo = 0, trAt = 0, trKind = "open", step = 0;
  var PA = { root: 0 }, PB = { root: 0 }, PQ = { root: 0 };
  /* WIND, IF THE WIND WERE MUSIC. The host passes s.wind = { gust, flutter, kick }: how loud the music is over seconds,
     its high notes, and the beat's swell. Loudness is how hard it blows, a beat is a gust that reaches the heart first and
     the outer whorls a moment later, high notes make the edges flutter. The wind's direction wanders slowly. */
  var windG = 0, windF = 0, wsecs = 0, windLast = 0, windDir = 0, kickHist = new Float32Array(90), kickPrev = 0, windSteps = 1;
  var F = { at: -1 }, skippedAt = 0, inhale = 0, stretchS = 0, quick = false;
  var LITE = false, lastNow = 0, frameEMA = 16, slowFor = 0, OFF = null, OFFX = null;
  function prep(s) {
    if (F.at === s.nowMs) return F;
    var size = s.size, e = Math.min(1, s.exposure == null ? 1 : s.exposure);
    var T = s.tempo, secs = T.now(s.reduceMotion);
      var off = s.myOffset != null ? s.myOffset : 0;
      var dayIdx = Math.floor((s.t + off * 60000) / 86400000);
      if (dayIdx !== grownFor) { grow(dayIdx); grownFor = dayIdx; }
      if (!bornAt) {
        bornAt = s.nowMs;
        try {
          var dayKey = String(dayIdx), seenDay = localStorage.getItem("alot.petals-day");
          if (seenDay === dayKey && !fullNext) { bornAt = s.nowMs - (FLOWER_AT + SCRIB); quick = true; }
          localStorage.setItem("alot.petals-day", dayKey);
        } catch (err) {}
        /* the entrance: the bud opens, the screen fills with petals, and they fold home into the flower */
        if (!quick && !s.reduceMotion) { scene = 0; trFrom = 0; trTo = 0; trKind = "open"; step = 1; trAt = bornAt + FLOWER_AT + SCRIB + BUD_MS * 0.6; }
        var skip = function () {
          var done = FLOWER_AT + SCRIB + LET_GO + UNFURL_MS + BLOOM_UP + BLOOM_HOLD + BLOOM_DOWN + 2000;
          if (performance.now() - bornAt < done) { bornAt = performance.now() - done; skippedAt = performance.now(); if (trFrom === 0 && trTo === 0) trAt = 0; }
          removeEventListener("pointerdown", skip, true);
          removeEventListener("keydown", skip, true);
        };
        addEventListener("pointerdown", skip, true);
        addEventListener("keydown", skip, true);
      }
      var scribT = s.nowMs - bornAt - FLOWER_AT;
      var since = scribT - SCRIB;
      var seen = s.reduceMotion ? 1 : easeOut(since / BUD_MS);
      var arrive = s.reduceMotion ? 1
                 : (SCRIBBLE ? HALF : 0) + (1 - (SCRIBBLE ? HALF : 0)) * gentle((since - BUD_MS * 0.6) / UNFURL_MS);
      hov += ((s.hover ? 1 : 0) - hov) * T.ease;
      var drag = s.dragOff || 0;
      var target = drag * 0.15;
      var prevTurn = turnS;
      turnS += (target - turnS) * (s.reduceMotion ? 1 : T.ease * 0.45);
      var dv = turnS - prevTurn;
      lastDrag = drag;
      omega += (dv - omega) * T.ease;
      var stir = clamp(Math.abs(omega) * 14, 0, 1);
      var wd = s.wind || null, wdt = windLast ? Math.min(0.1, (s.nowMs - windLast) / 1000) : 0;
      windLast = s.nowMs;
      windG += ((wd ? wd.gust : 0) - windG) * (1 - Math.exp(-wdt * 0.8));
      windF += ((wd ? wd.flutter : 0) - windF) * (1 - Math.exp(-wdt * 3));
      wsecs += wdt * (1 + 0.7 * windG + 0.25 * windF);
      windDir = 0.9 * Math.sin(wsecs * 0.013) + 0.4 * Math.sin(wsecs * 0.031 + 1.7);
      /* the beat's swell, remembered for three seconds: a gust reaches each petal when the wind has carried it there */
      var kick = wd ? wd.kick : 0;
      for (var kh = kickHist.length - 1; kh > 0; kh--) kickHist[kh] = kickHist[kh - 1];
      kickHist[0] = kick;
      var K = T.ease * 0.25, D = 1 - T.settle;
      var steps = Math.max(1, Math.round((s.frameMs || 16) / 16.7)); windSteps = steps;
      for (var w = 0; w < WHORLS; w++) {
        var hang = 0.25 + 0.95 * (w / (WHORLS - 1));
        for (var st = 0; st < steps; st++) {
          tvel[w] += -K * trail[w] - D * tvel[w] - (st ? 0 : dv * hang * 0.55);
          trail[w] += tvel[w];
        }
        if (s.reduceMotion) { trail[w] = 0; tvel[w] = 0; }
      }
      if (!s.reduceMotion) stirPh += Math.abs(omega) * 6;
      var py = 0, px = 0;
      if (s.pointer && s.pointer.seen > -1e8) {
        py = clamp((s.pointer.y - size / 2) / size * 0.5, -0.15, 0.15);
        px = clamp((s.pointer.x - size / 2) / size * 0.5, -0.15, 0.15);
      }
      var swingY = s.reduceMotion ? 0 : 0.05 * Math.sin(secs * T.hullBreath * 0.6) + 0.03 * windG * Math.sin(windDir);
      var swingL = s.reduceMotion ? 0 : 0.025 * Math.sin(secs * T.hullBreath * 0.45 + 1.3);
      var lean = LEAN + py + swingL + clamp(omega * 1.6, -0.06, 0.06);
      var yaw = -px * 0.9 + swingY + clamp(trail[WHORLS - 1] * 0.35, -0.08, 0.08);
      setView(lean, yaw);
      var breath = s.reduceMotion ? 0 : secs * T.hullBreath;
      var spin = (s.localHour(s.myOffset) / 24) * TAU + turnS
               + (s.reduceMotion ? 0 : secs * T.dayTurn);
    var tz = since - BUD_MS * 0.6;
    var zoom = REST, rest = 1, spread = 0;
    if (!s.reduceMotion) {
      var up = gentle(tz / BLOOM_UP), down = gentle((tz - BLOOM_UP - BLOOM_HOLD) / BLOOM_DOWN);
      zoom = 1 + (REST - 1) * gentle(tz / 2600);
      if (tz < 0) zoom = 1;

      rest = quick ? gentle((tz - 2600) / 900)
                   : gentle((tz - BLOOM_UP - BLOOM_HOLD - BLOOM_DOWN * 0.6) / 900);
    }
    var trOn = false, p1 = 0, p2 = 0;
    if (s.reduceMotion) { scene = 0; trAt = 0; }
    if (trAt) {
      var ta = s.nowMs - trAt, len = trKind === "open" ? BLOOM_UP + BLOOM_HOLD + BLOOM_DOWN : MORPH;
      if (ta >= len) { scene = trTo; trAt = 0; }
      else if (ta >= 0) {
        trOn = true;
        if (trKind === "open") { p1 = ta / BLOOM_UP; p2 = (ta - BLOOM_UP - BLOOM_HOLD) / BLOOM_DOWN; spread = gentle(p1) * (1 - gentle(p2)); }
        else p1 = ta / MORPH;
      }
    }
    F.trOn = trOn; F.trKind = trKind; F.p1 = p1; F.p2 = p2; F.trFrom = trFrom; F.trTo = trTo; F.scene = scene;
    F.useRings = trOn && trKind === "open";
    F.flowerW = !trOn ? (scene === 0 ? 1 : 0)
              : trKind === "open" ? 1 : (trFrom === 0 ? 1 - gentle(p1) : gentle(p1));
    F.scribT = scribT;
    if (skippedAt) e *= easeOut((s.nowMs - skippedAt) / 700);
    var BR = null, want = s.inhale || 0;
    if (BR && !s.reduceMotion) {
      var bq = clamp((s.nowMs - BR.at) / BR.dur, 0, 1);
      want = bq * bq * (3 - 2 * bq);
    }
    inhale += (want - inhale) * (want > inhale ? 0.12 : 0.035);
    F.inhale = inhale;
    if (lastNow) {
      var fdt = Math.min(250, s.nowMs - lastNow);
      frameEMA += (fdt - frameEMA) * 0.05;
      if (frameEMA > (s.frameMs || 16) * 1.6) slowFor += fdt; else slowFor = Math.max(0, slowFor - fdt * 0.5);
      if (slowFor > 1200) LITE = true;
    }
    lastNow = s.nowMs;
    F.lite = LITE || !!window.__petalsLite;
    F.at = s.nowMs; F.e = e; F.secs = secs; F.T = T; F.wsecs = wsecs; F.windG = windG; F.windF = windF; F.windDir = windDir;
    F.seen = seen; F.arrive = arrive; F.stir = stir; F.lean = lean; F.yaw = yaw;
    var sWant = s.reduceMotion ? 0 : clamp(Math.abs(drag) * 0.55, 0, 0.32);
    stretchS += (sWant - stretchS) * (sWant > stretchS ? 0.10 : 0.04);
    zoom *= 1 + stretchS;
    F.stretch = stretchS;
    F.breath = breath; F.spin = spin; F.zoom = zoom; F.rest = rest; F.spread = spread;
    return F;
  }
  /* where a petal is in a shape: its root (x, y) on the plane, the way it points, its size, how it stands, and how
     open (own) and how lit (vis) it is. Flower radii; y toward the bottom of the screen. */
  function flowerPose(o, pt, F, field, ownMain, mods) {
    var root, len, wid, own, vis;
    if (pt.ring) {
      var rc = 0.85 + (REACH - 0.85) * pt.ring, gap = (REACH - 0.85) / 6;
      len = gap * 2.3 * pt.lenJ;
      root = Math.max(0.3, rc - len * 0.5 - gap * 0.4 * pt.rootJ);
      wid = (TAU * rc / pt.n) * 0.62 * pt.widJ;
      own = field ? 1 : 0; vis = field ? 0.85 - 0.35 * pt.ring : 0;
    } else {
      var of = pt.w / (WHORLS - 1);
      root = pt.root + (field ? 0.42 + 0.30 * of : 0); len = pt.len; wid = pt.wid; own = ownMain; vis = 1;
    }
    var A = pt.a + F.spin + trail[pt.w];
    o.x = Math.cos(A) * root; o.y = Math.sin(A) * root; o.a = A;
    o.len = len; o.wid = wid; o.rise = field && !pt.ring ? pt.rise * 0.35 : pt.rise; o.curl = pt.curl; o.own = own; o.vis = vis; o.open = own * mods;
    return o;
  }
  function shapePose(o, pt, id, F, mods) {
    var ws = F.wsecs || F.secs, k = pt.slot, r1 = pt.r1, r2 = pt.r2, r3 = pt.r3;
    o.own = 1; o.vis = 0.9; o.open = mods;
    if (k < 0) { o.x = 0; o.y = 0; o.a = 0; o.len = 0.1; o.wid = 0.05; o.rise = 0.3; o.curl = 0.2; o.vis = 0; return o; }
    /* several slow rhythms that never line up, so nothing visibly repeats */
    function drift(f, p) { return Math.sin(ws * f + p) + 0.5 * Math.sin(ws * f * 2.31 + p * 1.7) + 0.25 * Math.sin(ws * f * 0.43 + p * 2.9); }
    if (id === 1) {
      /* a fish: a wave runs from the head down the body, growing toward the tail, as a fish swims */
      var om = 1.2 + 0.15 * Math.sin(ws * 0.071);
      var wave = function (x) {                 // sideways offset at body position x (0.9 head .. -1.2 tail tip)
        var fromHead = 0.95 - x, amp = 0.015 + 0.075 * fromHead * fromHead;
        return amp * Math.sin(ws * om - fromHead * 2.6) + 0.3 * amp * Math.sin(ws * om * 0.57 - fromHead * 1.9 + 1.3);
      };
      var slope = function (x) { return (wave(x - 0.04) - wave(x + 0.04)) / 0.08; };
      var bx, by, ba, bl, bw, br = 0.35, bc = 0.25;
      if (k < 24) {
        var col = k % 6, row = Math.floor(k / 6); bx = 0.62 - col * 0.23;
        var hb = 0.40 * Math.sqrt(Math.max(0.05, 1 - Math.pow((bx - 0.06) / 0.72, 2)));
        by = ((row - 1.5) / 1.5) * hb * 0.78; ba = Math.PI + (r1 - 0.5) * 0.25;
        bl = 0.30 + 0.05 * r2; bw = 0.19 + 0.05 * r3;
      } else if (k < 32) {
        var lobe = k < 28 ? -1 : 1, li = (k % 4) / 3;
        bx = -0.56 - 0.05 * li; by = lobe * 0.05; ba = Math.PI + lobe * (0.45 + 0.60 * li);
        bl = 0.66 + 0.12 * r1 - 0.10 * li; bw = 0.10 + 0.03 * r2; br = 0.2; bc = 0.45;
      } else if (k < 36) {
        var up = k < 34, fi = k % 2;
        bx = up ? 0.20 - fi * 0.22 : 0.30 - fi * 0.35; by = up ? -0.30 : 0.26;
        ba = up ? -Math.PI * 0.62 - fi * 0.25 : Math.PI * 0.68 + fi * 0.2 + 0.12 * Math.sin(ws * 0.9 + fi * 1.4);
        bl = 0.34 + 0.06 * r1; bw = 0.15; bc = 0.5;
      } else {
        var hi = (k - 36) / 3 - 0.5;
        bx = 0.86 - 0.08 * Math.abs(hi); by = hi * 0.22; ba = Math.PI + hi * 0.9; bl = 0.34; bw = 0.20; br = 0.4; bc = 0.3;
      }
      /* the body bends with the wave; each petal turns with the bend where it sits (the tail most) */
      var tipX = bx + Math.cos(ba) * bl * 0.6;
      o.x = bx; o.y = by + wave(bx); o.a = ba + Math.atan(slope(tipX)) * (k >= 24 && k < 32 ? 1.6 : 0.8);
      o.len = bl; o.wid = bw; o.rise = br; o.curl = bc;
      /* and the fish wanders the water slowly, never on a loop you can see */
      o.x += 0.20 * drift(0.041, 0.3); o.y += 0.07 * drift(0.067, 2.1);
    } else if (id === 2) {
      /* a jellyfish: the bell squeezes quickly and lets go slowly, rising a little each time; the strands answer late */
      var cyc = ws * 0.5 + 0.4 * Math.sin(ws * 0.09), ph0 = cyc / TAU - Math.floor(cyc / TAU);
      var sq = function (p) { p = p - Math.floor(p); return p < 0.28 ? gentle(p / 0.28) : 1 - gentle((p - 0.28) / 0.72); };
      var squeeze = sq(ph0), lift = -0.05 * squeeze + 0.04 * drift(0.05, 1.1);
      if (k < 18) {
        var ph = -Math.PI * (0.08 + 0.84 * ((k % 9) + 0.5) / 9) + (r1 - 0.5) * 0.08, rb = (k < 9 ? 0.34 : 0.50);
        var sqHere = sq(ph0 - (k < 9 ? 0 : 0.04));                 // the rim follows the crown a moment later
        var sc = 1 - 0.13 * sqHere;
        o.x = Math.cos(ph) * rb * 1.2 * sc; o.y = -0.25 + Math.sin(ph) * rb * 0.9 * (1 - 0.05 * sqHere) + lift;
        o.a = ph + 0.25 * sqHere * Math.sign(Math.cos(ph)); o.len = (0.34 + 0.10 * r2) * (1 - 0.06 * sqHere); o.wid = 0.22 + 0.06 * r3;
        o.rise = 1.0 + 0.4 * sqHere; o.curl = 0.6;
      } else {
        var m = k - 18, j = m % 4, t = (Math.floor(m / 4) + 0.5) / 6;
        var late = sq(ph0 - 0.10 - t * 0.25);                        // further down the strand, later
        var wv = Math.sin(t * 3.6 - ws * 0.55 + j * 1.4) + 0.4 * Math.sin(t * 6.1 - ws * 0.83 + j * 2.3);
        o.x = (-0.36 + 0.24 * j + (r1 - 0.5) * 0.04) * (1 - 0.3 * t) * (1 - 0.10 * late) + 0.12 * t * wv;
        o.y = -0.18 + t * 1.15 * (1 - 0.04 * late) + lift * (1 - 0.6 * t);
        o.a = Math.PI / 2 + 0.35 * t * (Math.cos(t * 3.6 - ws * 0.55 + j * 1.4) + 0.4 * Math.cos(t * 6.1 - ws * 0.83 + j * 2.3));
        o.len = 0.30 + 0.05 * r2; o.wid = 0.045 + 0.02 * r3; o.rise = 0.25; o.curl = 0.1; o.vis = 0.9 - 0.4 * t;
      }
      o.x += 0.10 * drift(0.037, 0.7);
    } else {
      /* a ray gliding: each wing ripples from the body out to its tip, the two sides not quite together */
      if (k < 32) {
        var side = k < 16 ? -1 : 1, q = k % 16, rowR = Math.floor(q / 4), cR = (q % 4 + 0.5) / 4;
        var span = 0.18 + 1.30 * cR * (1 - 0.15 * rowR);
        var rip = Math.sin(ws * 0.75 - cR * 2.4 - rowR * 0.3 + (side > 0 ? 0.25 : 0)) + 0.3 * Math.sin(ws * 0.43 - cR * 1.7 + 1.1);
        o.x = side * span * (1 - 0.04 * rip * cR); o.y = -0.22 + rowR * 0.13 + 0.34 * cR * cR - 0.06 * rip * cR;
        o.a = (side > 0 ? 0 : Math.PI) + side * (0.35 + 0.25 * rowR) * 0.6 - side * 0.12 * rip * cR;
        o.len = (0.36 - 0.14 * cR) + 0.05 * r1; o.wid = 0.17 + 0.04 * r2;
        o.rise = 0.22 + 0.42 * rip * cR; o.curl = 0.35;
      } else if (k < 36) {
        o.x = 0; o.y = -0.30 + (k - 32) * 0.13; o.a = Math.PI / 2; o.len = 0.26; o.wid = 0.20; o.rise = 0.6; o.curl = 0.3;
      } else {
        var tt = (k - 36) / 4, tw2 = Math.sin(ws * 0.7 - tt * 2.2) + 0.4 * Math.sin(ws * 0.41 - tt * 3.1);
        o.x = 0.06 * tt * tw2; o.y = 0.25 + tt * 0.34; o.a = Math.PI / 2 + 0.18 * tw2 * tt;
        o.len = 0.36; o.wid = 0.05; o.rise = 0.2; o.curl = 0.05;
      }
      o.y += 0.05 * drift(0.031, 0.4); o.x += 0.16 * drift(0.027, 1.9);
    }
    /* AS LIKE THE FLOWER AS IT CAN BE (Ely: "as similar to the style of the flower please"). Each petal keeps its own
       character from the flower: how upright it stands and how its tip curls back (so its rim catches the light the
       same way), its own size mixed into the part's, and full light. Only where it sits and points is the creature's. */
    o.rise = pt.rise * 0.75 + o.rise * 0.25;
    o.curl = pt.curl * 0.7 + o.curl * 0.3;
    o.len = o.len * 0.6 + pt.len * 0.4 * (o.len / 0.35);
    o.wid = o.wid * 0.6 + pt.wid * 0.4 * (o.wid / 0.2);
    o.vis = Math.min(1, o.vis / 0.9);
    return o;
  }
  function blendPose(o, A, B, m, tw) {
    var im = 1 - m;
    var x = A.x * im + B.x * m, y = A.y * im + B.y * m;
    var da = B.a - A.a; da = ((da + Math.PI) % TAU + TAU) % TAU - Math.PI;
    var t = tw * Math.sin(Math.PI * m), ct = Math.cos(t), st = Math.sin(t);
    o.x = x * ct - y * st; o.y = x * st + y * ct; o.a = A.a + da * m + t;
    o.len = A.len * im + B.len * m; o.wid = A.wid * im + B.wid * m; o.rise = A.rise * im + B.rise * m;
    o.curl = A.curl * im + B.curl * m; o.own = A.own * im + B.own * m; o.vis = A.vis * im + B.vis * m;
    o.open = A.open * im + B.open * m;
    return o;
  }
  function poseIn(o, pt, id, F, field, ownMain, mods) {
    return id === 0 || field ? flowerPose(o, pt, F, field, ownMain, mods) : shapePose(o, pt, id, F, mods);
  }
  function flowerOn(ctx, s, F, LW) {
    var e = F.e, secs = F.secs, T = F.T, seen = F.seen, arrive = F.arrive;
    var ws = F.wsecs || secs, wG = s.reduceMotion ? 0 : (F.windG || 0), wF = s.reduceMotion ? 0 : (F.windF || 0), wDir = F.windDir || 0;
    var stir = F.stir, lean = F.lean, yaw = F.yaw, breath = F.breath, spin = F.spin;
    var C = CX;
      if (!COLLECT) {
      var hg = ctx.createRadialGradient(CX, CY, 0, CX, CY, R * 0.55);
      var fw = 0.6 + 0.4 * (F.flowerW == null ? 1 : F.flowerW);
      hg.addColorStop(0, "rgba(" + HEART + "," + (0.13 * e * arrive * fw).toFixed(3) + ")");
      hg.addColorStop(0.4, "rgba(" + HEART + "," + (0.05 * e * arrive * fw).toFixed(3) + ")");
      hg.addColorStop(1, "rgba(" + HEART + ",0)");
      ctx.fillStyle = hg;
      ctx.beginPath(); ctx.arc(CX, CY, R * 0.55, 0, TAU); ctx.fill();
      }
      var sp = s.reduceMotion ? 0 : (F.spread || 0);
      var list = F.useRings && !s.reduceMotion ? rings.concat(petals) : petals;
      var crowded = list.length;
      for (var pi = 0; pi < crowded; pi++) {
        var pt = list[pi];
        var outerF = pt.w / (WHORLS - 1);
        var ownMain = s.reduceMotion ? 1 : easeOut((arrive - (1 - outerF) * 0.25) / 0.75);
        var near2 = 0, wave = 0;
        if (!COLLECT) {
          var oxv = CX - s.size / 2, oyv = CY - s.size / 2;
          var act = (s.pointer && s.pointer.seen > 0)
            ? 1 - clamp((s.nowMs - s.pointer.seen - 1500) / 1200, 0, 1) : 0;
          if (act > 0 && pt.tx != null) {
            var pdx = (oxv + s.pointer.x) - pt.tx, pdy = (oyv + s.pointer.y) - pt.ty;
            near2 = act * Math.exp(-(pdx * pdx + pdy * pdy) / (R * R * 0.10));
          }
          pt.prox = (pt.prox || 0) + (near2 - (pt.prox || 0)) * T.ease * 0.7;
          if (!s.reduceMotion && s.tap && s.tap.at > 0 && pt.tx != null) {
            var age = (s.nowMs - s.tap.at) / 1000;
            if (age >= 0 && age < 4.5) {
              var wdx = (oxv + s.tap.x) - pt.tx, wdy = (oyv + s.tap.y) - pt.ty;
              var front = age * R * 0.42;
              var dd = Math.sqrt(wdx * wdx + wdy * wdy) - front;
              wave = Math.exp(-(dd * dd) / (R * R * 0.025)) * Math.exp(-age * 0.75);
            }
          }
        }
        pt.wave = wave;
        var mods = (1 + 0.035 * Math.sin(breath + pt.ph) + 0.05 * hov
                    + stir * (0.05 + 0.03 * Math.sin(stirPh * 0.5 + pt.ph * 3))
                    + (s.reduceMotion ? 0 : 0.06 * (pt.prox || 0) + 0.08 * wave)
                    + 0.09 * (F.inhale || 0)
                    + wG * 0.01);
        /* the pose: in one shape, or on the way between two through the screen full of petals */
        var pz;
        if (!F.trOn) pz = poseIn(PQ, pt, F.scene, F, false, ownMain, mods);
        else if (F.trKind === "open") {
          /* from the heart outward, and then exactly backwards */
          var d1 = pt.ring ? 0.30 + 0.70 * pt.ring : 0.22 * outerF;
          d1 = d1 * 0.9 + pt.late * 0.1;
          var pp = F.p2 > 0 ? 1 - F.p2 : F.p1;
          var m1 = gentle((pp - d1 * 0.6) / 0.4);
          pz = blendPose(PQ, poseIn(PA, pt, 0, F, false, ownMain, mods), poseIn(PB, pt, 0, F, true, ownMain, mods), m1, 0);
        } else {
          /* becoming: each petal sets off on its own time and drifts on a gentle curve */
          var m2 = gentle((F.p1 - pt.late * 0.4) / 0.6);
          pz = blendPose(PQ, poseIn(PA, pt, F.trFrom, F, false, ownMain, mods), poseIn(PB, pt, F.trTo, F, false, ownMain, mods), m2,
                         0.25 * (pt.r3 - 0.5));
        }
        if (pz.vis < 0.005) { pt.fx = null; continue; }
        /* WEIGHT (Ely: "robotic rather than flowy"). A petal is never placed: it follows where its shape wants it, a little
           late, like something floating, easing off, drifting a touch past and settling back. Heavier petals (the flower's
           inner ones) are slower to start and to stop; light ones answer sooner. Its size and how it stands follow too. */
        if (pt.fx == null || s.reduceMotion) {
          pt.fx = pz.x; pt.fy = pz.y; pt.fa = pz.a; pt.fl = pz.len; pt.fw = pz.wid; pt.fr = pz.rise; pt.fc = pz.curl;
          pt.vx = 0; pt.vy = 0; pt.va = 0; pt.vl = 0; pt.vw = 0; pt.vr = 0;
        } else {
          var kF = 0.0032 * (0.75 + 0.5 * pt.late) * (pt.ring ? 1.3 : 1), dF = 2 * 0.62 * Math.sqrt(kF);
          var daF = pz.a - pt.fa; daF = ((daF + Math.PI) % TAU + TAU) % TAU - Math.PI;
          for (var fs = 0; fs < windSteps; fs++) {
            pt.vx += (pz.x - pt.fx) * kF - pt.vx * dF; pt.fx += pt.vx;
            pt.vy += (pz.y - pt.fy) * kF - pt.vy * dF; pt.fy += pt.vy;
            pt.va += daF * kF - pt.va * dF; pt.fa += pt.va; daF -= pt.va;
            pt.vl += (pz.len - pt.fl) * kF - pt.vl * dF; pt.fl += pt.vl;
            pt.vw += (pz.wid - pt.fw) * kF - pt.vw * dF; pt.fw += pt.vw;
            pt.vr += (pz.rise - pt.fr) * kF - pt.vr * dF; pt.fr += pt.vr;
          }
          pt.fc += (pz.curl - pt.fc) * 0.05;
        }
        pz.x = pt.fx; pz.y = pt.fy; pz.a = pt.fa; pz.len = pt.fl; pz.wid = pt.fw; pz.rise = pt.fr; pz.curl = pt.fc;
        var own = pz.own, open = pz.open, ox = pz.x, oy = pz.y;
        spine(pz, Math.min(1.12, open + 0.08 * (F.stretch || 0)), 0.30 * (F.stretch || 0) * outerF);
        var sway = s.reduceMotion ? 0
                 : 0.028 * (1 + 0.5 * wG) * Math.sin(ws * CALM * T.hullBreath * 1.7 + pt.ph * 2.3)
                 + 0.012 * (1 + 0.8 * wF) * Math.sin(ws * CALM * T.hullBreath * 3.1 + pt.ruf2)
;
        var drift = s.reduceMotion ? 0
                  : ws * CALM * T.sweep * (0.6 + 0.4 * pt.vein) + stirPh * (0.5 + 0.5 * pt.vein);
        var a = pz.a + sway * (0.6 + 0.6 * outerF);
        var ca = Math.cos(a), sa = Math.sin(a);
        /* BENT BY THE WIND, NOT TURNED. A petal is held at its root and bends along its length, the tip most (u squared).
           The wind blows across the screen from one side: a gust reaches the upwind petals first and the far side a
           moment later, at about three flower radii a second. Light petals (outer, long, the rings) give more and settle
           slower; the heavy inner ones are stiff and quick. Each petal is its own small spring, so it sways back a
           little past where it was and comes to rest. High notes add a quick flutter at the tips. */
        var wx = Math.cos(wDir), wy = Math.sin(wDir);
        var flex = (0.45 + 0.75 * Math.min(1, outerF) + (pt.ring ? 0.5 : 0)) * (0.8 + 0.4 * pt.vein);
        if (!COLLECT) {
          var along = (ox + ca * pz.len * 0.5) * wx + (oy + sa * pz.len * 0.5) * wy;   // where the petal sits along the wind
          var reachW = F.useRings ? REACH : 1.1;
          var lagF = Math.max(0, Math.min(kickHist.length - 1, Math.round((along + reachW) / 3 * 30)));
          var gustHere = kickHist[lagF];
          var flut = wF * Math.sin(ws * (2.6 + 1.4 * pt.vein) + pt.ph * 5);
          var bendT = s.reduceMotion ? 0 : flex * (0.018 * wG + 0.032 * gustHere + 0.005 * flut);
          var kS = 0.10 / flex, dS = 0.10 + 0.05 / flex;
          for (var bs = 0; bs < windSteps; bs++) {
            pt.bv = (pt.bv || 0) + (bendT - (pt.b || 0)) * kS - (pt.bv || 0) * dS;
            pt.b = (pt.b || 0) + pt.bv;
          }
        }
        var cross = Math.sin(wDir - a) * (pt.b || 0), downW = Math.cos(wDir - a) * (pt.b || 0);
        var drag2 = s.reduceMotion ? 0 : clamp(-(-sa * pt.vx + ca * pt.vy) * 28, -0.25, 0.25);   // moving, its tip trails
        cross += drag2;
        var bx = -sa * cross, by = ca * cross;                             // across the petal, so its length holds
        var W = pz.wid * (0.5 + 0.5 * own)
              * (1 + (s.reduceMotion ? 0 : 0.04 * Math.sin(ws * CALM * T.hullBreath * 1.3 + pt.ruf1)));
        var nE = 0;
        for (var side = 0; side < 2; side++) {
          for (var i = 0; i <= SPN; i++) {
            var ii = side === 0 ? i : SPN - i;
            var u = ii / SPN;
            var ruffle = 1 + pt.rufA * (1 + 0.35 * stir) * u * u *
              (Math.sin(u * 9 + pt.ruf1 + drift + (side ? 2.1 : 0)) +
               0.6 * Math.sin(u * 17 + pt.ruf2 - drift * 0.7))
              + (s.reduceMotion ? 0 : WAVE * (1 + 0.35 * wF) * u * u *
                 Math.sin(u * 6.5 - ws * CALM * T.shimmer * (1.4 + 0.8 * pt.vein)
                          + pt.ph * 3 + (side ? 1.1 : 0)));
            var hw = W * halfW(u) * ruffle * (side ? -1 : 1);
            var r0 = spR[ii] * ruffle, h0 = spH[ii];
            var hh = h0 + Math.abs(hw) * 0.35;
            var x = ox + ca * r0 - sa * hw + bx * u * u, y = oy + sa * r0 + ca * hw + by * u * u;
            hh -= downW * u * u * 0.6;                                     // blown outward it lies lower, blown back it lifts
            project(x, y, hh, R);
            EX[nE] = P.x; EY[nE] = P.y; nE++;
          }
        }
        if (COLLECT) {
          for (var cq = 0; cq < nE; cq++) COLLECT.push(EX[cq], EY[cq]);
          continue;
        }
        project(ox + ca * spR[SPN] + bx, oy + sa * spR[SPN] + by, spH[SPN] - downW * 0.6, R);
        var tipX = P.x, tipY = P.y, tipK = P.k;
        if (!COLLECT) {
          pt.tx = (tipX + EX[0]) / 2; pt.ty = (tipY + EY[0]) / 2;
        }
        project(ox + ca * spR[0], oy + sa * spR[0], spH[0], R);
        var rootX = P.x, rootY = P.y;
        var face = Math.abs(Math.sin(a + 0.4 * yaw) * sL * 0.8 +
                            Math.cos(Math.min(1.4, pz.rise * (1 - 0.6 * open))) * cL * 0.6);
        var fres = clamp(1 - face, 0.15, 1);
        var depth = clamp((tipK - 0.80) / 0.40, 0, 1);
        var film = 0.5 + 0.5 * Math.sin(a * 2 + lean * 3 + pt.w * 0.7 + yaw * 4);
        var rimC = mix(ROSE, AQUA, film);
        var quiet = 1 - 0.30 * outerF;
        var A = e * seen * (0.45 + 0.55 * own) * quiet * (0.70 + 0.30 * depth) * pz.vis;
        var g = ctx.createLinearGradient(rootX, rootY, tipX, tipY);
        g.addColorStop(0, "rgba(" + PEARL.join(",") + ",0)");
        g.addColorStop(0.35, "rgba(" + mix(PEARL, ROSE, 0.25) + "," + (0.11 * A).toFixed(4) + ")");
        g.addColorStop(0.75, "rgba(" + PEARL.join(",") + "," + (0.095 * A * (1 + 0.15 * hov)).toFixed(4) + ")");
        g.addColorStop(1, "rgba(" + mix(PEARL, AQUA, film) + "," + (0.05 * A).toFixed(4) + ")");
        ctx.fillStyle = g;
        ctx.beginPath();
        smoothPath(ctx, 0, nE, true);
        ctx.fill();
        var sweepA = (s.reduceMotion ? 0 : secs * T.sweep) + spin * 0.5;
        var near = 0.5 + 0.5 * Math.cos(a - sweepA);
        var sheen = Math.pow(near, 7);
        var wander = s.reduceMotion ? 1
          : 0.50 + 0.50 * (0.5 + 0.5 * Math.sin(secs * CALM * T.shimmer * (0.55 + 0.6 * pt.vein) + pt.ph * 5.0))
                        * (0.65 + 0.35 * Math.sin(secs * CALM * T.hullBreath * (1.7 + pt.vein) + pt.ruf1 * 2.0));
        var rimA = A * (0.07 + 0.26 * fres) * (1 + 0.25 * hov) * (1 + 1.6 * sheen) * (1 + 0.8 * stir)
                 * (0.55 + 0.9 * wander)
                 * (1 + 1.3 * (pt.prox || 0) + 1.8 * (pt.wave || 0) + 1.1 * (F.inhale || 0));
        var from = Math.floor(SPN * 0.30), to = nE - from;
        var rg = ctx.createLinearGradient(rootX, rootY, tipX, tipY);
        rg.addColorStop(0, "rgba(" + rimC + ",0)");
        rg.addColorStop(0.45, "rgba(" + rimC + ",0.45)");
        rg.addColorStop(1, "rgba(" + rimC + ",1)");
        ctx.lineJoin = "round"; ctx.lineCap = "round";
        ctx.strokeStyle = rg;
        ctx.beginPath(); smoothPath(ctx, from, to, false);
        if (!F.lite) { ctx.globalAlpha = Math.min(1, rimA * 0.10); ctx.lineWidth = 9 * LW; ctx.stroke(); }
        ctx.globalAlpha = Math.min(1, rimA * 0.28); ctx.lineWidth = 3.6 * LW; ctx.stroke();
        ctx.globalAlpha = Math.min(1, rimA * 1.10); ctx.lineWidth = 0.9 * LW; ctx.stroke();
        ctx.globalAlpha = 1;
        if (!s.reduceMotion && SPARKS > 0 && !F.lite) {
          for (var gk = 0; gk < SPARKS; gk++) {
            var gh = hash(pi * 977 + gk * 131 + 7);
            var gr = 0.30 + 0.60 * hash(pi * 613 + gk * 29 + 3);
            var tw = Math.pow(Math.max(0, Math.sin(secs * gr + gh * 40)), 28);
            if (tw < 0.03) continue;
            var gi = from + Math.floor(hash(pi * 389 + gk * 53 + 11) * (to - from));
            var gx = EX[gi], gy = EY[gi];
            var ga = tw * A * 0.55 * (0.6 + 0.4 * depth);
            var gl = (1.6 + 2.2 * tw) * LW;
            ctx.globalAlpha = 1;
            var sg = ctx.createRadialGradient(gx, gy, 0, gx, gy, gl * 1.6);
            sg.addColorStop(0, "rgba(236,248,255," + (0.9 * ga).toFixed(3) + ")");
            sg.addColorStop(1, "rgba(236,248,255,0)");
            ctx.fillStyle = sg;
            ctx.beginPath(); ctx.arc(gx, gy, gl * 1.6, 0, TAU); ctx.fill();
            ctx.strokeStyle = "rgba(236,248,255," + (0.55 * ga).toFixed(3) + ")";
            ctx.lineWidth = 0.6 * LW;
            ctx.beginPath();
            ctx.moveTo(gx - gl * 2.2, gy); ctx.lineTo(gx + gl * 2.2, gy);
            ctx.moveTo(gx, gy - gl * 2.2); ctx.lineTo(gx, gy + gl * 2.2);
            ctx.stroke();
          }
        }
        if (pt.w < WHORLS - 1 && !F.lite && !pt.ring) {
          var vA = A * 0.11 * pt.vein;
          ctx.strokeStyle = "rgba(" + mix(PEARL, ROSE, 0.4) + "," + vA.toFixed(4) + ")";
          ctx.lineWidth = 0.5 * LW;
          for (var vn = -1; vn <= 1; vn++) {
            ctx.beginPath();
            for (var vi = 2; vi <= SPN - 2; vi++) {
              var vu = vi / SPN;
              var vw = vn * W * 0.45 * halfW(vu) * Math.sin(Math.PI * vu);
              var vx = ox + ca * spR[vi] - sa * vw + bx * vu * vu, vy = oy + sa * spR[vi] + ca * vw + by * vu * vu;
              project(vx, vy, spH[vi] + Math.abs(vw) * 0.3 - downW * vu * vu * 0.6, R);
              if (vi === 2) ctx.moveTo(P.x, P.y); else ctx.lineTo(P.x, P.y);
            }
            ctx.stroke();
          }
        }
      }
  }
  function thread(ctx, s, F, LW) {
    var t = F.scribT;
    if (t < 0 || t > SCRIB + LET_GO) return;
    var bud = {};
    for (var k in F) bud[k] = F[k];
    bud.arrive = HALF; bud.seen = 1; bud.stir = 0;
    COLLECT = [];
    flowerOn(ctx, s, bud, LW);
    var raw = COLLECT; COLLECT = null;
    var N0 = raw.length / 2;
    if (N0 < 2) return;
    var UP = 4, N = N0 * UP;
    var tg = THREAD_T.length >= N * 2 ? THREAD_T : (THREAD_T = new Float32Array(N * 2));
    for (var q = 0; q < N0; q++) {
      var q2 = Math.min(N0 - 1, q + 1);
      for (var w2 = 0; w2 < UP; w2++) {
        var f = w2 / UP, o = (q * UP + w2) * 2;
        tg[o] = raw[q * 2] + (raw[q2 * 2] - raw[q * 2]) * f;
        tg[o + 1] = raw[q * 2 + 1] + (raw[q2 * 2 + 1] - raw[q * 2 + 1]) * f;
      }
    }
    var drawn = clamp((t - STILL_MS) / DRAW_MS, 0, 1);
    var pull = (t - STILL_MS - DRAW_MS - TANGLE_MS) / PULL_MS;
    var gone = clamp((t - SCRIB) / LET_GO, 0, 1);
    var secs = s.nowMs / 1000;
    var HW = Math.max(CX, (s.vw || CX * 2) - CX) * 1.08;
    var HH = Math.max(CY, (s.vh || CY * 2) - CY) * 1.08;
    var PET = (SPN + 1) * 2 * UP;
    var NP = PENS.length;
    var cnt = [], heads = [], basep = [], at = [], tipX = [], tipY = [], seenP = [];
    for (var pn = 0; pn < NP; pn++) { cnt[pn] = 0; at[pn] = 0; seenP[pn] = 0; }
    for (var i = 0; i < N; i++) cnt[Math.floor(i / PET) % NP]++;
    var run = 0, any = 0;
    for (pn = 0; pn < NP; pn++) {
      basep[pn] = run; run += cnt[pn];
      heads[pn] = Math.floor(cnt[pn] * steady(drawn)); any += heads[pn];
    }
    if (t < STILL_MS + 1600) {
      var sa = F.e * easeOut(t / REST_GLOW_MS) * (1 - gentle((t - STILL_MS) / 1400)) * 0.85;
      if (sa > 0.004) {
        var sr = 34 * LW;
        var sg0 = ctx.createRadialGradient(CX, CY, 0, CX, CY, sr);
        sg0.addColorStop(0, "rgba(255,238,226," + (0.60 * sa).toFixed(3) + ")");
        sg0.addColorStop(0.2, "rgba(255,226,214," + (0.28 * sa).toFixed(3) + ")");
        sg0.addColorStop(0.6, "rgba(255,214,200," + (0.07 * sa).toFixed(3) + ")");
        sg0.addColorStop(1, "rgba(255,214,200,0)");
        ctx.fillStyle = sg0;
        ctx.beginPath(); ctx.arc(CX, CY, sr, 0, TAU); ctx.fill();
      }
    }
    if (any < 2) return;
    var BIGS = Math.max(HW, HH) * 0.72 / (R * 0.95);
    var LOOSE = Math.min(HW, HH) * 0.030;
    var mSum = 0, mN = 0;
    if (PX.length < N) { PX = new Float32Array(N); PY = new Float32Array(N); }
    var ORD = ORDER.length >= N ? ORDER : (ORDER = new Int32Array(N));
    for (i = 0; i < N; i++) {
      var pen = Math.floor(i / PET) % NP;
      var k2 = at[pen]++;
      ORD[basep[pen] + k2] = i;
      if (k2 >= heads[pen]) continue;
      var u = k2 / Math.max(1, cnt[pen]);
      var m = gentle((pull - u * 0.30) / 0.70);
      var tx = tg[i * 2], ty = tg[i * 2 + 1];
      var sc = BIGS + (1 - BIGS) * m;
      var dir = (pen % 2 ? -1 : 1);
      var sw = (1 - m) * 0.22 * dir + 0.06 * (1 - m) * Math.sin(u * 5 + secs * 0.15 + pen);
      var cs = Math.cos(sw), sn = Math.sin(sw);
      var dx = (tx - CX) * sc, dy = (ty - CY) * sc;
      var ox = PENS[pen][0] * HW * (1 - m), oy = PENS[pen][1] * HH * (1 - m);
      var loose = (1 - m) * LOOSE;
      var x = CX + ox + dx * cs - dy * sn + loose * (Math.sin(u * 47 + 0.3 + pen * 2 + secs * 0.35) + 0.5 * Math.sin(u * 131 + 2.0 + pen));
      var y = CY + oy + dx * sn + dy * cs + loose * (Math.sin(u * 53 + 1.7 + pen * 3 + secs * 0.30) + 0.5 * Math.sin(u * 127 + 0.9 + pen));
      var fan = gentle(u / 0.14);
      fan = fan + (1 - fan) * m;
      x = CX + (x - CX) * fan; y = CY + (y - CY) * fan;
      mSum += m; mN++;
      PX[i] = x; PY[i] = y;
      if (k2 === heads[pen] - 1) { tipX[pen] = x; tipY[pen] = y; seenP[pen] = 1; }
    }
    var resolved = mN ? mSum / mN : 0;
    var A = F.e * (1 - gentle(gone)) * easeOut(t / 900) * (0.70 + 0.40 * resolved);
    var film = 0.5 + 0.5 * Math.sin(secs * 0.12);
    var col = mix(ROSE, PEARL, 0.35 + 0.35 * film);
    ctx.lineJoin = "round"; ctx.lineCap = "round";
    for (pn = 0; pn < NP; pn++) {
      var base = basep[pn], hd = heads[pn];
      var K = 4, per = Math.ceil(hd / K);
      for (var c = 0; c < K; c++) {
        var i0 = c * per, i1 = Math.min(hd, i0 + per + 1);
        if (i1 - i0 < 2) break;
        var pw = 0.70 + 0.30 * (0.5 + 0.5 * Math.sin(c * 1.7 + 0.6 + pn * 2)) + 0.1 * Math.sin(c * 0.53);
        ctx.beginPath();
        ctx.moveTo(PX[ORD[base + i0]], PY[ORD[base + i0]]);
        for (var j = i0 + 1; j < i1; j++) ctx.lineTo(PX[ORD[base + j]], PY[ORD[base + j]]);
        ctx.strokeStyle = "rgba(" + col + "," + (0.040 * A).toFixed(4) + ")";
        ctx.lineWidth = 20 * LW * pw; ctx.stroke();
        ctx.strokeStyle = "rgba(" + col + "," + (0.065 * A).toFixed(4) + ")";
        ctx.lineWidth = 6 * LW * pw; ctx.stroke();
        ctx.strokeStyle = "rgba(255,236,228," + (0.12 * A * (0.75 + 0.25 * pw)).toFixed(4) + ")";
        ctx.lineWidth = 0.6 * LW * pw; ctx.stroke();
      }
    }
    var home = gentle(clamp(pull, 0, 1));
    var penA = F.e * (1 - gentle(gone));
    if (penA > 0.004) {
      for (pn = 0; pn < NP; pn++) {
        if (!seenP[pn]) continue;
        var bend = Math.sin(home * Math.PI) * 0.18 * (pn % 2 ? 1 : -1);
        var fx = tipX[pn], fy = tipY[pn];
        var vx = CX - fx, vy = CY - fy;
        var hx = fx + vx * home - vy * bend, hy = fy + vy * home + vx * bend;
        var a2 = penA;
        if (drawn < 1) {
          var dC = Math.sqrt((hx - CX) * (hx - CX) + (hy - CY) * (hy - CY));
          a2 *= 0.14 + 0.86 * clamp(dC / (70 * LW), 0, 1);
        } else {
          a2 *= 1 - 0.86 * gentle((home - 0.82) / 0.18);
        }
        var pr = 30 * LW * (1 + 0.5 * home);
        var pg = ctx.createRadialGradient(hx, hy, 0, hx, hy, pr);
        pg.addColorStop(0, "rgba(255,238,226," + (0.55 * a2).toFixed(3) + ")");
        pg.addColorStop(0.18, "rgba(255,226,214," + (0.26 * a2).toFixed(3) + ")");
        pg.addColorStop(0.55, "rgba(255,214,200," + (0.07 * a2).toFixed(3) + ")");
        pg.addColorStop(1, "rgba(255,214,200,0)");
        ctx.fillStyle = pg;
        ctx.beginPath(); ctx.arc(hx, hy, pr, 0, TAU); ctx.fill();
      }
    }
  }
  var ORDER = new Int32Array(0);
  var PENS = [[-0.66, -0.48], [0.08, -0.70], [0.70, -0.34], [-0.74, 0.30],
              [-0.12, 0.62], [0.60, 0.56], [0.04, -0.02]];
  var THREAD_T = new Float32Array(0), PX = new Float32Array(0), PY = new Float32Array(0);
  window.ALOT_PETALS = {
    id: "petals",
    /* the whole entrance again, from the dark: a closed bud that opens and blooms past every edge */
    restart: function () { bornAt = 0; quick = false; skippedAt = 0; scene = 0; trAt = 0; step = 0; fullNext = true; },
    /* the open flower blooms out over the whole screen and comes home */
    windNow: function () { return { gust: windG, flutter: windF, dir: windDir }; },
    bloom: function (at) { if (!trAt) { var st = STEPS[step % STEPS.length]; step++; trKind = st[0]; trFrom = scene; trTo = st[1]; trAt = at || performance.now(); } },
    sceneNow: function () { return { scene: SCENES[scene], moving: !!trAt, kind: trKind, to: SCENES[trTo] }; },
    resize: function (size) { C = size / 2; R = size / 2 * 0.86; },
    backdrop: function (ctx, s) {
      var e = Math.min(1, s.exposure == null ? 1 : s.exposure);
      if (e <= 0.01) return;
      var T = s.tempo, secs = T.now(s.reduceMotion);
      var cx = s.cx, cy = s.cy, rad = s.rad;
      var far = Math.hypot(Math.max(cx, s.vw - cx), Math.max(cy, s.vh - cy));
      BIG = SCRIBBLE ? REST : Math.max(REST, far / (rad * 0.86 * 0.80));
      REACH = Math.min(3.4, Math.max(2, far / (rad * 0.86 * REST) * 1.15));
      var F = prep(s);
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      CX = cx; CY = cy; R = rad * 0.86 * F.zoom;
      setView(F.lean, F.yaw);
      var LWb = (rad * 2 / 600) * Math.sqrt(F.zoom);
      if (!s.reduceMotion && SCRIBBLE) thread(ctx, s, F, LWb);
      var q = 1 - 0.4 * (F.spread || 0);
      if (F.lite) q *= 0.75;
      q = Math.ceil(q * 8) / 8;
      if (q < 0.97) {
        var dp = s.dpr || 1, ow = Math.ceil(s.vw * q * dp), oh = Math.ceil(s.vh * q * dp);
        if (!OFF) { OFF = document.createElement("canvas"); OFFX = OFF.getContext("2d"); }
        if (OFF.width !== ow || OFF.height !== oh) { OFF.width = ow; OFF.height = oh; }
        OFFX.setTransform(1, 0, 0, 1, 0, 0);
        OFFX.clearRect(0, 0, ow, oh);
        OFFX.setTransform(q * dp, 0, 0, q * dp, 0, 0);
        OFFX.globalCompositeOperation = "lighter";
        flowerOn(OFFX, s, F, LWb);
        ctx.drawImage(OFF, 0, 0, s.vw, s.vh);
      } else {
        flowerOn(ctx, s, F, LWb);
      }
      var wash = ctx.createRadialGradient(cx, cy, rad * 0.6, cx, cy, rad * 2.6);
      wash.addColorStop(0, "rgba(236,214,226," + (0.035 * e).toFixed(4) + ")");
      wash.addColorStop(0.5, "rgba(200,226,226," + (0.012 * e).toFixed(4) + ")");
      wash.addColorStop(1, "rgba(200,226,226,0)");
      ctx.fillStyle = wash;
      ctx.fillRect(0, 0, s.vw, s.vh);
      var MOTES = 36;
      for (var m = 0; m < MOTES; m++) {
        var h1 = hash(m * 2654435761), h2 = hash(m * 40503 + 7), h3 = hash(m * 2246822519 + 13);
        var climb = s.reduceMotion ? 0 : (secs * T.climb * (0.5 + h3)) / TAU;
        var sway = s.reduceMotion ? 0 : Math.sin(secs * T.climb * 3 + h1 * TAU) * 0.012;
        var mx = (((h1 + h3 * 0.13 + sway) % 1) + 1) % 1 * s.vw;
        var my = (((h2 - climb) % 1) + 1) % 1 * s.vh;
        var dc = Math.hypot(mx - cx, my - cy) / rad;
        if (dc < 0.45) continue;
        var nearF = clamp((dc - 0.45) / 0.5, 0, 1);
        var a2 = 0.16 * e * nearF * (0.45 + 0.55 * h3);
        var col = h1 < 0.5 ? "255,216,196" : "198,240,232";
        ctx.fillStyle = "rgba(" + col + "," + a2.toFixed(4) + ")";
        ctx.beginPath(); ctx.arc(mx, my, 0.7 + h2 * 1.3, 0, TAU); ctx.fill();
      }
      ctx.restore();
      ctx.globalCompositeOperation = "source-over";
    },
  };
})();
