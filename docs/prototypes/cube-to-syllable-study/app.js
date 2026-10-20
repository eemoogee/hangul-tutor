const scene = document.querySelector('#scene');
const openButton = document.querySelector('#open-button');
const motionButton = document.querySelector('#motion-button');
const resetButton = document.querySelector('#reset-button');
const badge = document.querySelector('#state-badge');
const hint = document.querySelector('#stage-hint');
const variantButtons = [...document.querySelectorAll('[data-variant]')].filter((el) => el.tagName === 'BUTTON');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

let isOpen = false;
let playing = false;
let viewX = 0;
let viewY = 0;
let pointer = null;

// Parallel copies of the glyph create a thin visible edge in the panel-free version.
for (const glyph of document.querySelectorAll('.glyph')) {
  const character = glyph.dataset.glyph;
  glyph.textContent = '';
  for (let layer = 14; layer >= 1; layer -= 1) {
    const copy = document.createElement('span');
    copy.className = 'extrusion';
    copy.style.setProperty('--layer', layer);
    copy.textContent = character;
    copy.setAttribute('aria-hidden', 'true');
    glyph.append(copy);
  }
  const front = document.createElement('span');
  front.className = 'front';
  front.textContent = character;
  glyph.append(front);
}

function setView(x, y) {
  viewX = Math.max(-65, Math.min(65, x));
  viewY = y;
  scene.style.setProperty('--view-x', `${viewX}deg`);
  scene.style.setProperty('--view-y', `${viewY}deg`);
}

function render() {
  scene.dataset.open = String(isOpen);
  scene.dataset.playing = String(playing && !reducedMotion.matches);
  openButton.textContent = isOpen ? 'Reassemble 나' : 'Open the syllable';
  openButton.setAttribute('aria-expanded', String(isOpen));
  motionButton.disabled = !isOpen || reducedMotion.matches;
  motionButton.textContent = playing ? 'Pause rotation' : 'Resume rotation';
  resetButton.disabled = !isOpen;
  badge.textContent = isOpen ? 'Open for inspection' : 'Assembled';
  hint.textContent = isOpen ? 'Drag to turn · arrow keys also turn the view' : 'Open to inspect · then drag the object or use ← →';
}

openButton.addEventListener('click', () => {
  isOpen = !isOpen;
  playing = isOpen && !reducedMotion.matches;
  if (!isOpen) setView(0, 0);
  render();
});

motionButton.addEventListener('click', () => { playing = !playing; render(); });
resetButton.addEventListener('click', () => {
  setView(0, 0);
  playing = false;
  const cube = document.querySelector('#cube');
  cube.style.animation = 'none';
  void cube.offsetWidth;
  cube.style.animation = '';
  render();
});
reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) playing = false; render(); });

for (const button of variantButtons) {
  button.addEventListener('click', () => {
    scene.dataset.variant = button.dataset.variant;
    for (const other of variantButtons) {
      const active = other === button;
      other.classList.toggle('active', active);
      other.setAttribute('aria-pressed', String(active));
    }
  });
}

scene.addEventListener('pointerdown', (event) => {
  if (!isOpen) return;
  pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, startX: viewX, startY: viewY };
  scene.setPointerCapture(event.pointerId);
  playing = false;
  render();
});
scene.addEventListener('pointermove', (event) => {
  if (!pointer || pointer.id !== event.pointerId) return;
  setView(pointer.startX - (event.clientY - pointer.y) * .4, pointer.startY + (event.clientX - pointer.x) * .55);
});
for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) {
  scene.addEventListener(name, () => { pointer = null; });
}
scene.addEventListener('keydown', (event) => {
  if (!isOpen) return;
  const moves = { ArrowLeft: [0, -15], ArrowRight: [0, 15], ArrowUp: [-12, 0], ArrowDown: [12, 0] };
  if (!moves[event.key]) return;
  event.preventDefault();
  playing = false;
  setView(viewX + moves[event.key][0], viewY + moves[event.key][1]);
  render();
});

render();
