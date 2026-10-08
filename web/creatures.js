// Procedural creature scenes, one per creature type: bird, marine, reptile, mammal.
// All shapes are drawn with canvas paths; nothing is loaded from outside the repo.
(function () {
  const TAU = Math.PI * 2;
  const C = { abyss: "#0B1C26", ink: "#12303B", ink2: "#1B4352", tide: "#2C8C99", salt: "#E8EDEB", buoy: "#F4B63F" };

  function vgrad(ctx, h, stops) {
    const g = ctx.createLinearGradient(0, 0, 0, h);
    stops.forEach(([o, c]) => g.addColorStop(o, c));
    return g;
  }

  const scenes = {
    bird(ctx, w, h, t) {
      ctx.fillStyle = vgrad(ctx, h, [[0, "#1B4352"], [1, "#3B7F8C"]]);
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "rgba(232,237,235,.16)"; ctx.lineWidth = 6; ctx.lineCap = "round";
      for (let i = 0; i < 4; i++) {
        const y = h * (0.2 + i * 0.17), x = ((t * 14 * (1 + i * 0.3) + i * 190) % (w + 300)) - 150;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 120 + i * 20, y); ctx.stroke();
      }
      const cx = w / 2, cy = h * 0.5 + Math.sin(t * 0.9) * 10;
      const flap = Math.sin(t * 2.2) * 0.55 + Math.sin(t * 0.55) * 0.2; // slow beats with gliding
      ctx.save(); ctx.translate(cx, cy); ctx.rotate(Math.sin(t * 0.6) * 0.05);
      ctx.fillStyle = C.salt;
      for (const s of [-1, 1]) { // wings
        ctx.save(); ctx.scale(s, 1); ctx.rotate(-flap);
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(70, -34, 190, -8 + flap * 20);
        ctx.quadraticCurveTo(110, 8, 0, 14); ctx.closePath(); ctx.fill();
        ctx.fillStyle = "#c4d0cd"; ctx.beginPath(); ctx.moveTo(60, -6); ctx.quadraticCurveTo(120, -10, 190, -8 + flap * 20); ctx.quadraticCurveTo(120, 2, 60, 6); ctx.fill();
        ctx.fillStyle = C.salt; ctx.restore();
      }
      ctx.beginPath(); ctx.ellipse(0, 6, 22, 11, 0, 0, TAU); ctx.fill(); // body
      ctx.beginPath(); ctx.ellipse(26, 0, 9, 7, 0, 0, TAU); ctx.fill(); // head
      ctx.fillStyle = C.buoy; ctx.beginPath(); ctx.moveTo(33, -1); ctx.lineTo(48, 3); ctx.lineTo(33, 5); ctx.fill(); // beak
      ctx.fillStyle = C.abyss; ctx.beginPath(); ctx.arc(29, -2, 1.8, 0, TAU); ctx.fill();
      ctx.fillStyle = "#c4d0cd"; ctx.beginPath(); ctx.moveTo(-20, 8); ctx.lineTo(-48, 2); ctx.lineTo(-46, 14); ctx.fill(); // tail
      ctx.restore();
    },

    marine(ctx, w, h, t) {
      ctx.fillStyle = vgrad(ctx, h, [[0, "#2C8C99"], [0.55, "#12303B"], [1, "#0B1C26"]]);
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "rgba(232,237,235,.06)";
      for (let i = 0; i < 4; i++) {
        const x = w * (0.1 + i * 0.27) + Math.sin(t * 0.3 + i) * 24;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + 70, 0); ctx.lineTo(x + 190, h); ctx.lineTo(x + 20, h); ctx.fill();
      }
      for (let i = 0; i < 12; i++) { // bubbles
        const k = (t * 0.12 + i * 0.173) % 1, x = (i * 97) % w + Math.sin(t + i) * 8, y = h - k * (h + 20);
        ctx.strokeStyle = "rgba(232,237,235,.4)"; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(x, y, 2 + (i % 3), 0, TAU); ctx.stroke();
      }
      const n = 26, len = 330, x0 = w / 2 - len / 2 + Math.sin(t * 0.5) * 24, y0 = h * 0.5 + Math.cos(t * 0.4) * 14;
      const spine = [];
      for (let i = 0; i < n; i++) { // head at i=0 (right), tail at the end; wave grows toward tail
        const u = i / (n - 1);
        spine.push([x0 + len * (1 - u), y0 + Math.sin(t * 3 - u * 4.2) * (4 + u * u * 38)]);
      }
      const half = (u) => 30 * Math.sin(Math.PI * Math.min(1, u * 1.15 + 0.08)) ** 0.8 * (1 - u * 0.55) + 2;
      const top = [], bot = [];
      for (let i = 0; i < n; i++) {
        const u = i / (n - 1), [x, y] = spine[i];
        const a = spine[Math.min(i + 1, n - 1)], b = spine[Math.max(i - 1, 0)];
        const ang = Math.atan2(a[1] - b[1], a[0] - b[0]) + Math.PI / 2, r = half(u);
        top.push([x + Math.cos(ang) * r, y + Math.sin(ang) * r]); bot.push([x - Math.cos(ang) * r, y - Math.sin(ang) * r]);
      }
      const tail = spine[n - 1], sw = Math.sin(t * 3 - 4.2) * 14;
      ctx.fillStyle = "#6f8f9b";
      ctx.beginPath(); ctx.moveTo(tail[0], tail[1]); ctx.lineTo(tail[0] - 40, tail[1] - 34 + sw); ctx.lineTo(tail[0] - 30, tail[1] + sw * .3); ctx.lineTo(tail[0] - 40, tail[1] + 34 + sw); ctx.fill(); // tail fin
      ctx.fillStyle = "#9fb8bf"; ctx.beginPath();
      top.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      bot.reverse().forEach(([x, y]) => ctx.lineTo(x, y)); ctx.closePath(); ctx.fill();
      const m = spine[Math.floor(n * 0.4)];
      ctx.fillStyle = "#6f8f9b"; ctx.beginPath(); ctx.moveTo(m[0] + 18, m[1] - 24); ctx.lineTo(m[0] - 22, m[1] - 60 + Math.sin(t * 3) * 3); ctx.lineTo(m[0] - 34, m[1] - 22); ctx.fill(); // dorsal
      ctx.beginPath(); ctx.moveTo(m[0] + 22, m[1] + 22); ctx.lineTo(m[0] - 10, m[1] + 56 + Math.sin(t * 3 + 1) * 6); ctx.lineTo(m[0] - 24, m[1] + 22); ctx.fill(); // pectoral
      const hd = spine[1];
      ctx.fillStyle = C.abyss; ctx.beginPath(); ctx.arc(hd[0] - 22, hd[1] - 8, 3.4, 0, TAU); ctx.fill();
      ctx.strokeStyle = "rgba(11,28,38,.5)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(hd[0] - 46, hd[1] + 6); ctx.lineTo(hd[0] - 30, hd[1] + 9); ctx.stroke();
    },

    reptile(ctx, w, h, t) {
      ctx.fillStyle = vgrad(ctx, h, [[0, "#3B7F8C"], [0.62, "#9BB7B3"], [0.62, "#2b4a45"], [1, "#12303B"]]);
      ctx.fillRect(0, 0, w, h);
      const gy = h * 0.74;
      ctx.fillStyle = "rgba(11,28,38,.35)";
      for (let i = 0; i < 9; i++) { const x = ((i * 91 - t * 20) % (w + 80) + w + 80) % (w + 80) - 40; ctx.beginPath(); ctx.ellipse(x, gy + 18 + (i % 3) * 14, 14 + (i % 4) * 4, 3, 0, 0, TAU); ctx.fill(); } // ground scrolls under the walker
      const cx = w / 2, bob = Math.sin(t * 1.6) * 2, step = t * 1.6;
      ctx.save(); ctx.translate(cx, gy + bob);
      const leg = (x, ph) => { const s = Math.sin(step + ph); ctx.fillStyle = "#5c6b57"; ctx.beginPath(); ctx.roundRect(x + s * 9 - 11, -4, 22, 36 - Math.max(0, -s) * 6, 8); ctx.fill(); };
      leg(-72, Math.PI); leg(54, 0);
      const hx = 96 + Math.sin(step * .5) * 6, hy = -22 + Math.sin(step) * 3; // head and neck
      ctx.strokeStyle = "#6c7b61"; ctx.lineWidth = 17; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(78, -18); ctx.quadraticCurveTo(100, -28, hx, hy - 26); ctx.stroke();
      ctx.fillStyle = "#6c7b61"; ctx.beginPath(); ctx.ellipse(hx + 6, hy - 28, 17, 12, -0.2, 0, TAU); ctx.fill();
      ctx.fillStyle = C.abyss; ctx.beginPath(); ctx.arc(hx + 12, hy - 32, 2.4, 0, TAU); ctx.fill();
      ctx.fillStyle = "#4d5b45"; // shell: saddle-backed dome
      ctx.beginPath(); ctx.moveTo(-110, 6); ctx.bezierCurveTo(-112, -92, -30, -96, 10, -86); ctx.bezierCurveTo(54, -96, 100, -70, 104, 6); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "rgba(232,237,235,.22)"; ctx.lineWidth = 2;
      [-70, -30, 12, 52].forEach((x) => { ctx.beginPath(); ctx.moveTo(x, 4); ctx.quadraticCurveTo(x + 8, -50, x + 4, -84); ctx.stroke(); });
      ctx.beginPath(); ctx.moveTo(-108, -30); ctx.quadraticCurveTo(0, -44, 100, -30); ctx.stroke();
      leg(-40, 0); leg(84, Math.PI);
      ctx.restore();
    },

    mammal(ctx, w, h, t) {
      ctx.fillStyle = vgrad(ctx, h, [[0, "#3B7F8C"], [0.55, "#2C8C99"], [0.55, "#1B4352"], [1, "#12303B"]]);
      ctx.fillRect(0, 0, w, h);
      const wy = h * 0.58;
      ctx.strokeStyle = "rgba(232,237,235,.35)"; ctx.lineWidth = 2;
      for (let r = 0; r < 4; r++) { ctx.beginPath(); for (let x = 0; x <= w; x += 8) { const y = wy + 14 + r * 22 + Math.sin(x * 0.03 + t * 1.2 + r) * 4; x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke(); }
      ctx.fillStyle = "#3a4a4d"; // basalt ledge
      ctx.beginPath(); ctx.moveTo(w * .18, h); ctx.lineTo(w * .22, h * .66); ctx.quadraticCurveTo(w * .5, h * .58, w * .8, h * .68); ctx.lineTo(w * .86, h); ctx.fill();
      const breathe = Math.sin(t * 1.4) * 2, nod = Math.sin(t * 0.8) * 0.07;
      ctx.save(); ctx.translate(w * .5, h * .66);
      ctx.fillStyle = "#6b5442"; // body
      ctx.beginPath(); ctx.moveTo(-120, 6); ctx.bezierCurveTo(-100, -56 - breathe, -10, -66 - breathe, 40, -52); ctx.bezierCurveTo(60, -40, 64, -10, 50, 6); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(-120, 6); ctx.lineTo(-168, 2); ctx.lineTo(-150, 16); ctx.lineTo(-166, 26); ctx.lineTo(-114, 10); ctx.fill(); // rear flippers
      ctx.save(); ctx.translate(36, -48); ctx.rotate(nod); // neck + head
      ctx.beginPath(); ctx.moveTo(-18, 10); ctx.quadraticCurveTo(-14, -42, 12, -52); ctx.lineTo(30, -40); ctx.quadraticCurveTo(26, -10, 22, 14); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.ellipse(26, -52, 24, 14, -0.18, 0, TAU); ctx.fill();
      ctx.fillStyle = "#4e3d30"; ctx.beginPath(); ctx.ellipse(48, -50, 8, 6, 0, 0, TAU); ctx.fill(); // muzzle
      ctx.fillStyle = C.abyss; ctx.beginPath(); ctx.arc(30, -58, 3, 0, TAU); ctx.fill();
      ctx.strokeStyle = "rgba(232,237,235,.7)"; ctx.lineWidth = 1.1;
      for (let i = -1; i <= 1; i++) { ctx.beginPath(); ctx.moveTo(50, -49); ctx.lineTo(74, -49 + i * 7 + Math.sin(t * 2) * 1); ctx.stroke(); }
      ctx.restore();
      ctx.save(); ctx.translate(-4, -10); ctx.rotate(0.35 + Math.sin(t * 1.1) * 0.12); // front flipper
      ctx.fillStyle = "#58443a"; ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(24, 20, 14, 52); ctx.quadraticCurveTo(-6, 34, -14, 6); ctx.fill();
      ctx.restore(); ctx.restore();
    },
  };

  let raf = 0, state = null;

  function frame(now) {
    if (!state) return;
    const { canvas, ctx, type } = state;
    if (!state.paused) state.t += (now - (state.last || now)) / 1000;
    state.last = now;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    (scenes[type] || scenes.bird)(ctx, canvas.width, canvas.height, state.t);
    if (state.paused && state.once) { state.once = false; }
    raf = requestAnimationFrame(frame);
  }

  window.Creatures = {
    types: Object.keys(scenes),
    start(canvas, type, paused) {
      this.stop();
      state = { canvas, ctx: canvas.getContext("2d"), type, t: 3, last: 0, paused: !!paused };
      raf = requestAnimationFrame(frame);
    },
    setPaused(p) { if (state) { state.paused = p; state.last = 0; } },
    stop() { cancelAnimationFrame(raf); state = null; },
    draw(ctx, type, w, h, t) { (scenes[type] || scenes.bird)(ctx, w, h, t); },
  };
})();
