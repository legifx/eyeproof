// Tiny WebGL game for eyeproof tests. Rectangles are drawn with scissor + clear (no shaders needed).
// ?bug=freeze stops the loop after 1 s, ?bug=blank never draws, ?bug=deaf ignores input.
import { coins as level } from './level.js';

const bug = new URLSearchParams(location.search).get('bug');
const cv = document.getElementById('game');
const gl = cv.getContext('webgl2', { preserveDrawingBuffer: false });
const dpr = window.devicePixelRatio || 1;
const keys = new Set();
const g = (window.__game = { player: { x: 120, y: 0, vy: 0 }, score: 0, frame: 0, ready: false, coins: level.map(c => ({ ...c })) });
addEventListener('keydown', e => bug !== 'deaf' && keys.add(e.key));
addEventListener('keyup', e => keys.delete(e.key));

function rect(x, y, w, h, [r, gg, b]) {
  gl.scissor(Math.round(x * dpr), Math.round((cv.height / dpr - y - h) * dpr), Math.round(w * dpr), Math.round(h * dpr));
  gl.clearColor(r, gg, b, 1); gl.clear(gl.COLOR_BUFFER_BIT);
}

function tick(t) {
  cv.width = innerWidth * dpr; cv.height = innerHeight * dpr;
  gl.viewport(0, 0, cv.width, cv.height);
  const W = innerWidth, H = innerHeight, floor = H - 120, p = g.player;
  if (keys.has('ArrowRight')) p.x += 6;
  if (keys.has('ArrowLeft')) p.x -= 6;
  if ((keys.has(' ') || keys.has('ArrowUp')) && p.y === 0) p.vy = 14;
  p.vy -= 0.8; p.y = Math.max(0, p.y + p.vy); if (p.y === 0) p.vy = 0;
  for (const c of g.coins) if (!c.taken && Math.abs(c.x - p.x) < 40 && Math.abs(c.y - p.y) < 50) { c.taken = true; g.score++; }
  document.getElementById('hud').textContent = `Score ${g.score}`;
  if (bug !== 'blank') {
    gl.disable(gl.SCISSOR_TEST); gl.clearColor(0.42, 0.68, 0.93, 1); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.SCISSOR_TEST);
    const cloud = (t / 40) % (W + 200) - 200;
    rect(cloud, 80, 180, 50, [1, 1, 1]);
    rect(0, floor, W, H - floor, [0.3, 0.6, 0.25]);
    for (const c of g.coins) if (!c.taken) rect(c.x - 12, floor - 60 - c.y + Math.sin(t / 200 + c.x) * 8, 24, 24, [1, 0.8, 0.1]);
    rect(p.x - 25, floor - 50 - p.y, 50, 50, [0.85, 0.2, 0.25]);
  }
  g.frame++; g.ready = true;
  if (!(bug === 'freeze' && t > 1000)) requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
