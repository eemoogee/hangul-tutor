(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const $ = id => document.getElementById(id);
  const clamp = (value, low = 0, high = 1) => Math.min(high, Math.max(low, value));
  const lerp = (a, b, t) => a + (b - a) * t;
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const pair = (a, b, t) => a.map((line, i) => line.map((point, j) => [
    lerp(point[0], b[i][j][0], t), lerp(point[1], b[i][j][1], t)
  ]));
  const shift = (shape, x, y) => shape.map(line => line.map(point => [point[0] + x, point[1] + y]));
  const path = shape => shape.map(line => line.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ')).join(' ');
  const svg = (tag, attrs = {}) => {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };

  // Exact endpoint geometry from Exploding Syllable v2; only final.free is moved
  // 16 units downward here to make its release position distinguishable from its slot.
  const GEOMETRY = {
    initial: {
      letter: 'ㄴ', role: 'initial consonant',
      na: [[[136, 76], [136, 221], [183, 221]]],
      nan: [[[136, 59], [136, 150], [181, 150]]],
      free: [[[48, 92], [48, 205], [126, 205]]]
    },
    medial: {
      letter: 'ㅏ', role: 'vowel at the right',
      na: [[[212, 65], [212, 230]], [[212, 145], [255, 145]]],
      nan: [[[211, 57], [211, 159]], [[211, 110], [254, 110]]],
      free: [[[270, 83], [270, 215]], [[270, 148], [328, 148]]]
    },
    final: {
      letter: 'ㄴ', role: 'final consonant below',
      nan: [[[143, 187], [143, 241], [236, 241]]],
      free: [[[141, 242], [141, 310], [263, 310]]]
    }
  };
  const TASKS = [
    {id: 'make-na', title: 'ㄴ + ㅏ → 나', label: 'BUILD 1', prompt: 'Lift ㄴ and ㅏ, then give each its place. Either order works.',
      start: {initial: false, medial: false, final: false}, goal: {initial: true, medial: true, final: false},
      parts: ['initial', 'medial'], slots: ['initial', 'medial']},
    {id: 'make-nan', title: '나 + ㄴ → 난', label: 'BUILD 2', prompt: 'Lift the second ㄴ and place it below. Watch the upper parts make room.',
      start: {initial: true, medial: true, final: false}, goal: {initial: true, medial: true, final: true},
      parts: ['initial', 'medial', 'final'], slots: ['final']},
    {id: 'open-nan', title: '난 → 나 + ㄴ', label: 'OPEN 3', prompt: 'Lift the lower ㄴ and set it aside. The upper block returns to 나.',
      start: {initial: true, medial: true, final: true}, goal: {initial: true, medial: true, final: false},
      parts: ['initial', 'medial', 'final'], slots: ['release']}
  ];
  const SLOTS = {
    initial: {x: 102, y: 58, width: 92, height: 179, cx: 149, cy: 151, text: 'START'},
    medial: {x: 190, y: 55, width: 88, height: 184, cx: 233, cy: 151, text: 'SIDE'},
    final: {x: 114, y: 169, width: 146, height: 88, cx: 186, cy: 222, text: 'BELOW'},
    release: {x: 105, y: 257, width: 162, height: 59, cx: 188, cy: 287, text: 'SET ASIDE'}
  };
  const slotFor = (id, task = TASKS[state.task]) => id === 'final' && task.id === 'open-nan' ? 'release' : id;
  const eligible = (id, task = TASKS[state.task]) => task.parts.includes(id) && task.goal[id] !== state.placed[id];
  const finished = () => Object.keys(TASKS[state.task].goal).every(id => TASKS[state.task].goal[id] === state.placed[id]);
  const pieceNodes = new Map();
  const bench = $('bench');
  const build = {
    taskCounter: $('task-counter'), taskLabel: $('task-label'), taskTitle: $('task-title'), taskPrompt: $('task-prompt'),
    state: $('build-state'), feedback: $('build-feedback'), pieceButtons: $('piece-buttons'), slotButtons: $('slot-buttons'),
    targets: $('targets'), pieces: $('pieces'), next: $('next-task'), back: $('back-task'), undo: $('undo-action'),
    reset: $('reset-task'), description: $('bench-desc')
  };
  const state = {
    area: 'build', treatment: 'transformative', task: 0,
    placed: {...TASKS[0].start}, progress: {initial: 0, medial: 0, final: 0},
    selected: null, drag: null, flying: null, reflowCarry: null, approach: 0,
    history: [], animation: null, message: 'Choose a piece to begin.', settled: null
  };

  for (const id of Object.keys(GEOMETRY)) {
    const group = svg('g', {class: 'piece', 'data-id': id, role: 'button', tabindex: '0'});
    const stroke = svg('path', {class: 'stroke'});
    const hit = svg('path', {class: 'hit'});
    group.append(stroke, hit);
    build.pieces.append(group);
    pieceNodes.set(id, {group, stroke, hit});
    group.addEventListener('pointerdown', event => startDrag(event, id));
    group.addEventListener('keydown', event => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      selectPiece(id);
    });
  }

  function activeReflow() {
    if (state.task === 0) return 0;
    if (state.reflowCarry) return lerp(state.reflowCarry.from, state.reflowCarry.to, state.reflowCarry.p);
    let value = state.progress.final;
    if (state.treatment === 'transformative' && state.drag?.id === 'final') {
      value = state.task === 1 ? Math.max(value, state.approach * .72) : Math.min(value, 1 - state.approach * .72);
    }
    return clamp(value, 0, 1.08);
  }

  function baseGeometry(id) {
    const part = GEOMETRY[id];
    if (id === 'final') return pair(part.free, part.nan, state.progress.final);
    const upper = pair(part.na, part.nan, activeReflow());
    return pair(part.free, upper, state.progress[id]);
  }

  function currentGeometry(id) {
    if (state.flying?.id === id) return pair(state.flying.from, state.flying.to, state.flying.p);
    const base = baseGeometry(id);
    if (state.drag?.id === id) {
      const dragged = shift(base, state.drag.dx, state.drag.dy - (state.treatment === 'basic' ? 0 : 8));
      const attraction = state.treatment === 'basic' ? 0 : state.approach * .38;
      const part = GEOMETRY[id];
      const destination = id === 'final' ? (state.task === 2 ? part.free : part.nan) : part.na;
      return pair(dragged, destination, attraction);
    }
    if (state.selected === id && state.treatment !== 'basic') return shift(base, 0, -8);
    return base;
  }

  function renderGeometry() {
    for (const [id, nodes] of pieceNodes) {
      const visible = TASKS[state.task].parts.includes(id);
      nodes.group.style.display = visible ? '' : 'none';
      if (!visible) continue;
      const geometry = currentGeometry(id);
      nodes.stroke.setAttribute('d', path(geometry));
      nodes.hit.setAttribute('d', path(geometry));
      nodes.group.classList.toggle('selected', state.selected === id);
      nodes.group.classList.toggle('dragging', state.drag?.id === id && state.drag.moved);
      nodes.group.classList.toggle('settled', state.settled === id);
      nodes.group.setAttribute('aria-label', `${GEOMETRY[id].role} ${GEOMETRY[id].letter}, ${state.placed[id] ? 'in the block' : 'outside the block'}. Press Enter or Space to lift.`);
    }
    for (const zone of build.targets.children) {
      const slot = zone.dataset.slot;
      const wanted = slot === 'release' ? 'final' : slot;
      zone.style.opacity = eligible(wanted) ? '1' : '.15';
      zone.classList.toggle('active', state.selected === wanted);
      zone.classList.toggle('near', state.treatment !== 'basic' && state.drag?.id === wanted && state.approach > .45);
    }
  }

  function stateText() {
    if (state.animation && finished()) return state.task === 2 ? 'Opening…' : 'Coming together…';
    if (finished()) return ['You made 나', 'You made 난', 'Back to 나 + ㄴ'][state.task];
    if (state.task === 0) return state.placed.initial || state.placed.medial ? 'Incomplete block' : 'Pieces apart';
    return state.task === 1 ? 'Waiting for lower ㄴ' : 'Three-part block';
  }

  function render() {
    const task = TASKS[state.task];
    build.taskCounter.textContent = `${state.task + 1} / 3`;
    build.taskLabel.textContent = task.label;
    build.taskTitle.textContent = task.title;
    build.taskPrompt.textContent = task.prompt;
    build.state.textContent = stateText();
    build.feedback.textContent = state.message;
    build.next.disabled = !finished() || Boolean(state.animation) || state.task === 2;
    build.next.textContent = state.task === 2 ? 'Complete' : 'Next';
    build.back.disabled = state.task === 0;
    build.undo.disabled = state.history.length === 0 || Boolean(state.animation);
    build.description.textContent = `${stateText()}. ${task.title}. ${state.selected ? `${GEOMETRY[state.selected].letter} lifted.` : ''}`;
    renderGeometry();
    for (const button of build.pieceButtons.querySelectorAll('button')) {
      button.classList.toggle('selected', state.selected === button.dataset.pick);
      button.disabled = !eligible(button.dataset.pick);
    }
    for (const button of build.slotButtons.querySelectorAll('button')) {
      const wanted = button.dataset.land === 'release' ? 'final' : button.dataset.land;
      button.disabled = !eligible(wanted);
    }
    document.querySelectorAll('[data-treatment]').forEach(button => {
      const selected = button.dataset.treatment === state.treatment;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  }

  function rebuildControls() {
    build.pieceButtons.replaceChildren();
    for (const id of TASKS[state.task].parts) {
      if (state.task > 0 && id !== 'final') continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.pick = id;
      button.textContent = `${GEOMETRY[id].letter} · ${id === 'initial' ? 'start' : id === 'medial' ? 'vowel' : 'lower'}`;
      button.addEventListener('click', () => selectPiece(id));
      build.pieceButtons.append(button);
    }
    build.slotButtons.replaceChildren();
    build.targets.replaceChildren();
    for (const slot of TASKS[state.task].slots) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.land = slot;
      button.textContent = slot === 'release' ? 'Set aside' : slot === 'initial' ? 'Start position' : slot === 'medial' ? 'Right position' : 'Lower position';
      button.addEventListener('click', () => placeAt(slot));
      build.slotButtons.append(button);
      const box = SLOTS[slot];
      const zone = svg('g', {class: 'target-zone', 'data-slot': slot, role: 'button', tabindex: '0',
        'aria-label': button.textContent});
      zone.append(svg('rect', {x: box.x, y: box.y, width: box.width, height: box.height, rx: 13}),
        svg('text', {x: box.cx, y: box.y + 15}));
      zone.querySelector('text').textContent = box.text;
      zone.addEventListener('click', () => placeAt(slot));
      zone.addEventListener('keydown', event => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        placeAt(slot);
      });
      build.targets.append(zone);
    }
  }

  function stopAnimation() {
    if (state.animation) cancelAnimationFrame(state.animation);
    state.animation = null;
    state.flying = null;
    state.reflowCarry = null;
  }

  function setTask(index) {
    stopAnimation();
    state.task = index;
    state.placed = {...TASKS[index].start};
    state.progress = Object.fromEntries(Object.entries(state.placed).map(([id, placed]) => [id, Number(placed)]));
    state.selected = null;
    state.drag = null;
    state.approach = 0;
    state.history = [];
    state.settled = null;
    state.message = ['Lift and place both pieces. An incomplete block stays visible.',
      'The upper two pieces stay present while you add the final ㄴ.',
      'Lift the lower ㄴ, then set it aside. Undo puts it back.'][index];
    rebuildControls();
    render();
  }

  function selectPiece(id) {
    if (state.animation || !eligible(id)) return;
    state.selected = state.selected === id ? null : id;
    state.message = state.selected ? `${GEOMETRY[id].letter} lifted. Place it in the outlined position, or drag it there.` : 'Piece returned to its starting position.';
    render();
  }

  function spring(t) { return t >= 1 ? 1 : 1 - Math.exp(-5 * t) * Math.cos(5.2 * t); }
  function animatePlacement(id, target, fromShape, fromReflow, doneMessage = null) {
    stopAnimation();
    const start = state.progress[id];
    const endShape = id === 'final' ? (target ? GEOMETRY.final.nan : GEOMETRY.final.free) : GEOMETRY[id].na;
    if (reduced()) {
      state.progress[id] = Number(target);
      if (doneMessage) state.message = doneMessage;
      render();
      return;
    }
    const duration = state.treatment === 'basic' ? 190 : 550;
    const started = performance.now();
    state.flying = {id, from: fromShape, to: endShape, p: 0};
    if (id === 'final' && state.treatment === 'transformative') {
      state.reflowCarry = {from: fromReflow, to: Number(target), p: 0};
    }
    const frame = now => {
      const t = clamp((now - started) / duration);
      const eased = state.treatment === 'basic' ? 1 - (1 - t) ** 3 : spring(t);
      state.progress[id] = lerp(start, Number(target), eased);
      state.flying.p = eased;
      if (state.reflowCarry) state.reflowCarry.p = eased;
      if (t >= 1) {
        state.progress[id] = Number(target);
        state.flying = null;
        state.reflowCarry = null;
        state.animation = null;
        state.settled = id;
        if (doneMessage) state.message = doneMessage;
        render();
        setTimeout(() => { if (state.settled === id) { state.settled = null; renderGeometry(); } }, 620);
      } else {
        renderGeometry();
        state.animation = requestAnimationFrame(frame);
      }
    };
    state.animation = requestAnimationFrame(frame);
  }

  function placeAt(slot) {
    const id = state.selected;
    if (!id) { state.message = 'Lift a piece first.'; render(); return false; }
    if (slotFor(id) !== slot) {
      state.message = `That position is for ${slot === 'initial' ? 'the starting ㄴ' : slot === 'medial' ? 'ㅏ' : 'the lower ㄴ'}. Try the outlined place for ${GEOMETRY[id].letter}.`;
      render();
      return false;
    }
    if (!eligible(id)) return false;
    const fromShape = currentGeometry(id);
    const fromReflow = activeReflow();
    state.history.push({...state.placed});
    state.placed[id] = TASKS[state.task].goal[id];
    state.drag = null;
    state.approach = 0;
    state.selected = null;
    const done = finished();
    const doneMessage = done ? ['You made 나. Both letters share one block.',
      'You made 난. The lower ㄴ has its own space.',
      'You opened 난 into 나 and a separate ㄴ.'][state.task]
      : null;
    state.message = doneMessage ? 'The pieces are settling into their new shape.'
      : `${GEOMETRY[id].letter} is moving into place. The unfinished block stays visible.`;
    animatePlacement(id, state.placed[id], fromShape, fromReflow, doneMessage);
    render();
    return true;
  }

  function undo() {
    if (!state.history.length || state.animation) return;
    const previous = state.history.pop();
    const changed = Object.keys(previous).find(id => previous[id] !== state.placed[id]);
    if (!changed) return;
    const fromShape = currentGeometry(changed);
    const fromReflow = activeReflow();
    state.placed = previous;
    state.selected = null;
    state.message = `${GEOMETRY[changed].letter} returned. You can try again.`;
    animatePlacement(changed, previous[changed], fromShape, fromReflow);
    render();
  }

  function pointInBench(event) {
    const point = bench.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    return point.matrixTransform(bench.getScreenCTM().inverse());
  }

  function startDrag(event, id) {
    if (state.animation || !eligible(id)) return;
    event.preventDefault();
    const point = pointInBench(event);
    state.selected = id;
    state.drag = {id, pointerId: event.pointerId, x: point.x, y: point.y, dx: 0, dy: 0, moved: false,
      currentX: point.x, currentY: point.y};
    bench.setPointerCapture(event.pointerId);
    state.message = `${GEOMETRY[id].letter} lifted. Move toward the outlined place, or tap its labeled button.`;
    render();
  }

  bench.addEventListener('pointermove', event => {
    const drag = state.drag;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const point = pointInBench(event);
    drag.dx = point.x - drag.x;
    drag.dy = point.y - drag.y;
    drag.currentX = point.x;
    drag.currentY = point.y;
    drag.moved ||= Math.hypot(drag.dx, drag.dy) > 7;
    const slot = SLOTS[slotFor(drag.id)];
    const distance = Math.hypot(point.x - slot.cx, point.y - slot.cy);
    state.approach = clamp(1 - distance / 105);
    renderGeometry();
  });

  bench.addEventListener('pointerup', event => {
    const drag = state.drag;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const slot = SLOTS[slotFor(drag.id)];
    const closeEnough = Math.hypot(drag.currentX - slot.cx, drag.currentY - slot.cy) <= 48;
    if (drag.moved && closeEnough) {
      placeAt(slotFor(drag.id));
    } else {
      state.drag = null;
      state.approach = 0;
      state.message = drag.moved ? 'The piece stayed with you. Bring it nearer the outlined place, or tap the place button.'
        : `${GEOMETRY[drag.id].letter} lifted. Tap its outlined place.`;
      render();
    }
  });
  bench.addEventListener('pointercancel', () => { state.drag = null; state.approach = 0; render(); });

  document.querySelectorAll('[data-treatment]').forEach(button => button.addEventListener('click', () => {
    if (state.treatment === button.dataset.treatment) return;
    state.treatment = button.dataset.treatment;
    setTask(state.task);
  }));
  build.next.addEventListener('click', () => { if (finished() && !state.animation && state.task < 2) setTask(state.task + 1); });
  build.back.addEventListener('click', () => { if (state.task > 0) setTask(state.task - 1); });
  build.reset.addEventListener('click', () => setTask(state.task));
  build.undo.addEventListener('click', undo);

  // The depth view uses only two jamo-sized objects. No blank cube faces are present.
  const depth = {progress: 0, spatial: 'panes', angle: 0, animation: null};
  const depthUi = {scene: $('spatial-scene'), rig: $('spatial-rig'), slider: $('depth-progress'), output: $('depth-output'),
    state: $('depth-state'), feedback: $('depth-feedback'), toggle: $('depth-toggle'), left: $('turn-left'),
    right: $('turn-right'), reset: $('depth-reset')};
  const depthPieces = new Map();
  const spatialDefinitions = {
    initial: {x: 105, y: 47, width: 120, height: 206, shape: shift(GEOMETRY.initial.na, -105, -47)},
    medial: {x: 185, y: 47, width: 100, height: 206, shape: shift(GEOMETRY.medial.na, -185, -47)}
  };
  for (const [id, definition] of Object.entries(spatialDefinitions)) {
    const piece = document.createElement('div');
    piece.className = 'spatial-piece';
    piece.dataset.part = id;
    piece.setAttribute('aria-hidden', 'true');
    const sheet = document.createElement('div');
    sheet.className = 'sheet';
    piece.append(sheet);
    for (let i = 12; i >= 1; i -= 1) {
      const layer = svg('svg', {class: 'depth-layer', viewBox: `0 0 ${definition.width} ${definition.height}`});
      layer.append(svg('path', {d: path(definition.shape)}));
      layer.dataset.layer = String(i);
      piece.append(layer);
    }
    const front = svg('svg', {class: 'front-layer', viewBox: `0 0 ${definition.width} ${definition.height}`});
    front.append(svg('path', {d: path(definition.shape)}));
    piece.append(front);
    depthUi.rig.append(piece);
    depthPieces.set(id, {piece, sheet});
  }

  function renderDepth() {
    const p = depth.progress;
    const u = depthUi.scene.clientWidth / 360 || .9;
    depthUi.scene.dataset.spatial = depth.spatial;
    depthUi.rig.style.transform = `rotateX(${-19 * p}deg) rotateY(${(-26 + depth.angle) * p}deg)`;
    const initial = depthPieces.get('initial').piece;
    const medial = depthPieces.get('medial').piece;
    initial.style.transform = `translate3d(${-55 * u * p}px,${-16 * u * p}px,${95 * u * p}px) rotateY(${-25 * p}deg) rotateX(${12 * p}deg)`;
    medial.style.transform = `translate3d(${27 * u * p}px,${18 * u * p}px,${-95 * u * p}px) rotateY(${31 * p}deg) rotateX(${-11 * p}deg)`;
    for (const {piece, sheet} of depthPieces.values()) {
      sheet.style.setProperty('--sheet-alpha', String(p * .24));
      sheet.style.setProperty('--edge-alpha', String(p * .88));
      sheet.style.setProperty('--shadow-alpha', String(p * .55));
      for (const layer of piece.querySelectorAll('.depth-layer')) {
        layer.style.transform = `translateZ(${-Number(layer.dataset.layer) * 2.4 * u * p}px)`;
      }
    }
    depthUi.slider.value = String(Math.round(p * 100));
    depthUi.output.textContent = `${Math.round(p * 100)}%`;
    depthUi.state.textContent = p < .02 ? 'Flat' : p > .98 ? 'Open' : 'Opening';
    depthUi.state.setAttribute('aria-label', p < .02 ? 'Assembled, readable syllable' : p > .98 ? 'Open for inspection' : 'Opening in depth');
    depthUi.toggle.textContent = p > .5 ? 'Assemble' : 'Open';
    depthUi.left.disabled = p < .5;
    depthUi.right.disabled = p < .5;
    document.querySelectorAll('[data-spatial]').forEach(button => {
      const selected = button.dataset.spatial === depth.spatial;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  }

  function stopDepth() { if (depth.animation) cancelAnimationFrame(depth.animation); depth.animation = null; }
  function animateDepth(target) {
    stopDepth();
    if (reduced()) { depth.progress = target; renderDepth(); return; }
    const from = depth.progress;
    const started = performance.now();
    const frame = now => {
      const t = clamp((now - started) / 760);
      depth.progress = lerp(from, target, 1 - (1 - t) ** 3);
      renderDepth();
      if (t < 1) depth.animation = requestAnimationFrame(frame);
      else { depth.progress = target; depth.animation = null; renderDepth(); }
    };
    depth.animation = requestAnimationFrame(frame);
  }
  depthUi.toggle.addEventListener('click', () => {
    const target = depth.progress > .5 ? 0 : 1;
    depthUi.feedback.textContent = target ? 'Two jamo objects separate in X, Y, and Z. The view stops when they open.'
      : 'The objects return to a readable flat 나.';
    animateDepth(target);
  });
  depthUi.slider.addEventListener('input', () => {
    stopDepth();
    depth.progress = Number(depthUi.slider.value) / 100;
    depthUi.feedback.textContent = 'You control the intermediate view. Scrub back to reassemble.';
    renderDepth();
  });
  depthUi.left.addEventListener('click', () => { depth.angle = clamp(depth.angle - 15, -60, 60); renderDepth(); });
  depthUi.right.addEventListener('click', () => { depth.angle = clamp(depth.angle + 15, -60, 60); renderDepth(); });
  depthUi.reset.addEventListener('click', () => {
    stopDepth(); depth.progress = 0; depth.angle = 0;
    depthUi.feedback.textContent = 'Returned to flat 나.';
    renderDepth();
  });
  document.querySelectorAll('[data-spatial]').forEach(button => button.addEventListener('click', () => {
    depth.spatial = button.dataset.spatial;
    renderDepth();
  }));
  window.addEventListener('resize', renderDepth);

  document.querySelectorAll('[data-area]').forEach(button => button.addEventListener('click', () => {
    state.area = button.dataset.area;
    $('build-panel').hidden = state.area !== 'build';
    $('depth-panel').hidden = state.area !== 'depth';
    for (const other of document.querySelectorAll('[data-area]')) {
      const selected = other === button;
      other.classList.toggle('active', selected);
      other.setAttribute('aria-pressed', String(selected));
    }
    if (state.area === 'depth') renderDepth();
  }));

  window.__livingLab = {snapshot: () => ({area: state.area, treatment: state.treatment, task: TASKS[state.task].id,
    placed: {...state.placed}, progress: {...state.progress}, selected: state.selected, complete: finished(),
    animating: Boolean(state.animation),
    depth: {...depth, animation: Boolean(depth.animation)}})};
  setTask(0);
  renderDepth();
})();
