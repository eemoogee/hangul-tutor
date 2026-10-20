(() => {
  'use strict';

  // A deliberately small visual model. These are authored geometric strokes,
  // not extracted font outlines or instructions for handwriting stroke order.
  const SHAPES = {
    '나': {
      parts: [
        {id:'initial', glyph:'ㄴ', role:'initial consonant', assembled:[[[131,91],[131,179],[177,179]]], open:[[[49,91],[49,192],[126,192]]]},
        {id:'medial', glyph:'ㅏ', role:'vowel at the right', assembled:[[[207,81],[207,194]],[[207,135],[249,135]]], open:[[[270,76],[270,204]],[[270,143],[329,143]]]}
      ],
      insight:'In 나, ㄴ sits left of ㅏ. As they separate, both regain room to look like independent letters.',
      closed:'ㄴ and ㅏ share one block: the vertical vowel stands to the right.'
    },
    '노': {
      parts: [
        {id:'initial', glyph:'ㄴ', role:'initial consonant', assembled:[[[142,73],[142,132],[229,132]]], open:[[[68,49],[68,145],[162,145]]]},
        {id:'medial', glyph:'ㅗ', role:'vowel below', assembled:[[[186,157],[186,198]],[[127,198],[244,198]]], open:[[[261,150],[261,205]],[[199,205],[325,205]]]}
      ],
      insight:'In 노, ㅗ rests below ㄴ. Opening the block reveals the stacked arrangement, not a left-to-right string.',
      closed:'ㄴ is above ㅗ. The vowel changes the arrangement of the block.'
    },
    '난': {
      parts: [
        {id:'initial', glyph:'ㄴ', role:'initial consonant', assembled:[[[132,67],[132,136],[177,136]]], open:[[[41,45],[41,145],[121,145]]]},
        {id:'medial', glyph:'ㅏ', role:'vowel at the right', assembled:[[[207,62],[207,144]],[[207,105],[247,105]]], open:[[[271,46],[271,146]],[[271,96],[331,96]]]},
        {id:'final', glyph:'ㄴ', role:'final consonant below', assembled:[[[137,165],[137,207],[226,207]]], open:[[[111,218],[111,284],[234,284]]]}
      ],
      insight:'난 has three parts. The first ㄴ begins the block, ㅏ sits to its right, and the second ㄴ occupies the bottom as a final consonant.',
      closed:'Initial ㄴ, medial ㅏ, and final ㄴ occupy different positions.'
    }
  };

  const $ = id => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';
  const els = {
    stage:$('stage'), parts:$('parts'), unicode:$('unicode-glyph'),
    title:$('stage-title'), description:$('stage-description'), footprint:$('footprint'),
    key:$('part-key'), boardState:$('board-state'), instruction:$('instruction'),
    primary:$('primary-action'), reset:$('reset-action'), scrub:$('scrub'),
    scrubLabel:$('scrub-label'), scrubValue:$('scrub-value'), feedback:$('feedback'),
    insight:$('insight-copy')
  };
  const state = {syllable:'나', view:'structure', mode:'auto', progress:{}, selected:null,
    message:'The letters are sharing one square.', animation:null, drag:null, suppressClick:false};
  const groups = new Map();
  const clamp = value => Math.max(0, Math.min(1, value));
  const lerp = (a,b,p) => a+(b-a)*p;
  const shape = () => SHAPES[state.syllable];
  const pct = value => `${Math.round(value*100)}%`;
  const fmt = n => Math.round(n*10)/10;
  const reduceMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

  function centroid(segments) {
    const pts = segments.flat();
    return [pts.reduce((n,p)=>n+p[0],0)/pts.length, pts.reduce((n,p)=>n+p[1],0)/pts.length];
  }
  function path(segments) {
    return segments.map(line => line.map((point,i) => `${i?'L':'M'}${fmt(point[0])} ${fmt(point[1])}`).join(' ')).join(' ');
  }
  function interpolated(part,p) {
    return part.assembled.map((line,lineIndex) => line.map((point,pointIndex) => [
      lerp(point[0],part.open[lineIndex][pointIndex][0],p),
      lerp(point[1],part.open[lineIndex][pointIndex][1],p)
    ]));
  }
  function svg(tag,attrs={}) {
    const node=document.createElementNS(svgNS,tag);
    for(const [key,value] of Object.entries(attrs)) node.setAttribute(key,value);
    return node;
  }
  function buildParts() {
    els.parts.replaceChildren(); groups.clear(); state.progress={}; state.selected=null;
    for(const part of shape().parts) {
      state.progress[part.id]=0;
      const group=svg('g',{'class':'component','data-part':part.id,'data-kind':part.id,
        'role':'button','tabindex':'0','aria-label':`${part.role}, ${part.glyph}. Select or move this component.`});
      const ghost=svg('path',{'class':'ghost','d':path(part.assembled)});
      const stroke=svg('path',{'class':'stroke','d':path(part.assembled)});
      const hit=svg('path',{'class':'hit','d':path(part.assembled)});
      group.append(ghost,stroke,hit); els.parts.append(group);
      groups.set(part.id,{group,ghost,stroke,hit});
    }
    els.key.replaceChildren();
    for(const part of shape().parts) {
      const button=document.createElement('button'); button.type='button';
      button.className=`part-chip ${part.id}`; button.dataset.choose=part.id;
      button.setAttribute('aria-label',`Select ${part.role}, ${part.glyph}`);
      const shortRole=part.id==='initial'?'start':part.id==='final'?'final':'vowel';
      button.innerHTML=`<i aria-hidden="true"></i><span>${part.glyph} · ${shortRole}</span>`;
      els.key.append(button);
    }
  }
  function cancelAnimation() {
    if(state.animation) cancelAnimationFrame(state.animation);
    state.animation=null;
  }
  function update() {
    const parts=shape().parts;
    const values=parts.map(part=>state.progress[part.id]);
    const max=Math.max(...values), allOpen=values.every(n=>n>.98), anyOpen=max>.02;
    const showBlueprint=state.view==='structure'?1:clamp(Math.max(max*5,state.selected?0.68:0.04));
    els.unicode.textContent=state.syllable;
    els.unicode.style.opacity=state.view==='type'?String(1-showBlueprint):'0';
    els.unicode.style.pointerEvents='none';
    els.footprint.style.opacity=String(anyOpen?0.85:0.45);
    for(const part of parts) {
      const p=state.progress[part.id], nodes=groups.get(part.id);
      const d=path(interpolated(part,p));
      nodes.stroke.setAttribute('d',d); nodes.hit.setAttribute('d',d);
      nodes.stroke.style.opacity=String(showBlueprint);
      nodes.ghost.style.opacity=String(p>.06?Math.min(.6,p*.6):0);
      nodes.group.classList.toggle('is-selected',state.mode==='direct'&&state.selected===part.id);
      nodes.group.setAttribute('aria-label',`${part.role}, ${part.glyph}, ${pct(p)} separated. ${state.mode==='direct'?'Select or drag this component.':'Switch to Pull a letter to move it alone.'}`);
    }
    document.querySelectorAll('[data-syllable]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.syllable===state.syllable)));
    document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===state.view)));
    document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode)));
    els.boardState.textContent=allOpen?'OPEN · LETTERS APART':anyOpen?'OPENING · PARTS VISIBLE':'CLOSED · 1 BLOCK';
    const selected=parts.find(p=>p.id===state.selected);
    if(state.mode==='auto') {
      els.instruction.textContent='Open the block, or scrub slowly to watch its letters change shape.';
      els.primary.innerHTML=`${max>.5?'Close the block':'Open the block'} <span aria-hidden="true">${max>.5?'↙':'↗'}</span>`;
      els.scrubLabel.firstChild.textContent='Separation ';
      els.scrub.value=Math.round(max*100); els.scrubValue.textContent=pct(max);
    } else {
      els.instruction.textContent=selected
        ? `Move ${selected.glyph} (${selected.role}). The other ${parts.length-1} ${parts.length===2?'letter stays':'letters stay'} anchored.`
        : 'Tap a colored letter, then pull it out. Tap again or use the button to return it.';
      els.primary.innerHTML=selected
        ? `${state.progress[selected.id]>.5?'Return':'Lift'} ${selected.glyph} <span aria-hidden="true">${state.progress[selected.id]>.5?'↙':'↗'}</span>`
        : 'Select a letter <span aria-hidden="true">↗</span>';
      els.scrubLabel.firstChild.textContent=selected?`${selected.glyph} separation `:'Selected letter separation ';
      els.scrub.value=Math.round((selected?state.progress[selected.id]:0)*100);
      els.scrubValue.textContent=pct(selected?state.progress[selected.id]:0);
    }
    els.scrub.disabled=state.mode==='direct'&&!selected;
    els.feedback.textContent=state.message;
    els.insight.textContent=shape().insight;
    els.title.textContent=`${state.syllable}, composed from ${parts.map(p=>p.glyph).join(' and ')}`;
    els.description.textContent=state.mode==='direct'
      ? `${parts.length} components. ${parts.filter(p=>state.progress[p.id]>.5).length} pulled out; the others stay anchored.`
      : `${parts.length} components, ${allOpen?'separated':anyOpen?'partly separated':'sharing one block'}.`;
    els.key.querySelectorAll('[data-choose]').forEach(b=>b.setAttribute('aria-pressed',String(state.selected===b.dataset.choose)));
  }
  function animateTo(targets,message) {
    cancelAnimation();
    state.message=message;
    const start=Object.fromEntries(Object.keys(targets).map(id=>[id,state.progress[id]]));
    if(reduceMotion()) {Object.assign(state.progress,targets); update(); return;}
    const started=performance.now(), duration=520;
    const frame=now=>{
      const t=clamp((now-started)/duration), eased=1-Math.pow(1-t,3);
      for(const id of Object.keys(targets)) state.progress[id]=lerp(start[id],targets[id],eased);
      update();
      if(t<1) state.animation=requestAnimationFrame(frame); else state.animation=null;
    };
    state.animation=requestAnimationFrame(frame);
    update();
  }
  function selectPart(id) {
    if(state.mode!=='direct') return;
    state.selected=id;
    const part=shape().parts.find(p=>p.id===id);
    state.message=`${part.glyph} is the ${part.role}. Pull it away to inspect the space it leaves.`;
    update();
  }
  function togglePart(id) {
    const p=state.progress[id], part=shape().parts.find(item=>item.id===id);
    animateTo({[id]:p>.5?0:1},p>.5
      ? `${part.glyph} returned to its place. ${shape().closed}`
      : `${part.glyph} is free. Its original position remains marked; the other letters did not move.`);
  }
  function setSyllable(value) {
    if(!SHAPES[value]) return;
    cancelAnimation(); state.syllable=value;
    buildParts(); state.message=shape().closed; update();
  }
  function setMode(value) {
    if(!['auto','direct'].includes(value)) return;
    cancelAnimation(); state.mode=value;
    for(const id of Object.keys(state.progress)) state.progress[id]=0;
    state.selected=null;
    state.message=value==='auto'?'Open the whole block to compare every part.':'Choose a letter. Drag it out, tap it twice, or use the button and slider.';
    update();
  }
  function setView(value) {
    if(!['structure','type'].includes(value)) return;
    state.view=value;
    state.message=value==='type'
      ? 'A conventional glyph gives way to this simplified geometric explanation as you open it.'
      : 'Color makes each component visible inside the shared block.';
    update();
  }
  function reset() {
    animateTo(Object.fromEntries(Object.keys(state.progress).map(id=>[id,0])),
      `${state.syllable} is together again. ${shape().closed}`);
  }
  document.querySelectorAll('[data-syllable]').forEach(b=>b.addEventListener('click',()=>setSyllable(b.dataset.syllable)));
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
  document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
  els.primary.addEventListener('click',()=>{
    if(state.mode==='auto') {
      const max=Math.max(...Object.values(state.progress)), open=max<=.5;
      animateTo(Object.fromEntries(Object.keys(state.progress).map(id=>[id,open?1:0])),
        open?`${state.syllable} opens into ${shape().parts.length} independent letters. The dashed frame shows where they met.`
          :`${state.syllable} is together again. ${shape().closed}`);
    } else if(state.selected) togglePart(state.selected);
    else {selectPart(shape().parts[0].id);groups.get(shape().parts[0].id).group.focus();}
  });
  els.reset.addEventListener('click',reset);
  els.scrub.addEventListener('input',()=>{
    cancelAnimation(); const p=Number(els.scrub.value)/100;
    if(state.mode==='auto') for(const id of Object.keys(state.progress)) state.progress[id]=p;
    else if(state.selected) state.progress[state.selected]=p;
    state.message=p>.02?'Pause anywhere: the change in spacing and proportion is continuous.':shape().closed;
    update();
  });
  els.key.addEventListener('click',e=>{const b=e.target.closest('[data-choose]');if(!b)return;
    if(state.mode!=='direct') setMode('direct');
    selectPart(b.dataset.choose); groups.get(b.dataset.choose).group.focus();
  });
  els.parts.addEventListener('click',e=>{
    const g=e.target.closest('[data-part]'); if(!g||state.mode!=='direct')return;
    if(state.suppressClick){state.suppressClick=false;return;}
    if(state.selected===g.dataset.part)togglePart(g.dataset.part);else selectPart(g.dataset.part);
  });
  els.parts.addEventListener('keydown',e=>{
    if(!['Enter',' '].includes(e.key))return;
    const g=e.target.closest('[data-part]');if(!g||state.mode!=='direct')return;
    e.preventDefault(); if(state.selected===g.dataset.part)togglePart(g.dataset.part);else selectPart(g.dataset.part);
  });
  els.stage.addEventListener('pointerdown',e=>{
    if(state.mode!=='direct'||(e.button!==undefined&&e.button!==0))return;
    const g=e.target.closest('[data-part]');if(!g)return;
    cancelAnimation();
    const id=g.dataset.part,part=shape().parts.find(p=>p.id===id),wasSelected=state.selected===id;
    selectPart(id);
    const a=centroid(part.assembled),b=centroid(part.open);
    const vx=b[0]-a[0],vy=b[1]-a[1],ctm=els.stage.getScreenCTM();
    const vxPx=vx*ctm.a+vy*ctm.c,vyPx=vx*ctm.b+vy*ctm.d;
    const distance=Math.hypot(vxPx,vyPx);
    state.drag={pointerId:e.pointerId,id,startX:e.clientX,startY:e.clientY,
      wasSelected,
      startProgress:state.progress[id],vx:vxPx/distance,vy:vyPx/distance,distance,moved:false};
    els.stage.setPointerCapture(e.pointerId);
  });
  els.stage.addEventListener('pointermove',e=>{
    const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    const dx=e.clientX-d.startX,dy=e.clientY-d.startY;
    if(Math.hypot(dx,dy)>5)d.moved=true;
    if(!d.moved)return;
    state.progress[d.id]=clamp(d.startProgress+(dx*d.vx+dy*d.vy)/d.distance);
    state.message=`Drag ${shape().parts.find(p=>p.id===d.id).glyph} outward or back. The other parts stay anchored.`;
    update();
  });
  els.stage.addEventListener('pointerup',e=>{
    const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    if(d.moved){state.suppressClick=true;state.message=state.progress[d.id]>.5
      ? 'The component stays detached until you put it back. Nothing snaps shut by itself.'
      : 'The component can pause partway through the block.';update();}
    else if(d.wasSelected){togglePart(d.id);state.suppressClick=true;}
    else state.suppressClick=true;
    if(state.suppressClick)setTimeout(()=>{state.suppressClick=false;},0);
    state.drag=null;
  });
  els.stage.addEventListener('pointercancel',e=>{
    const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    state.progress[d.id]=d.startProgress;state.drag=null;state.message='Move cancelled; the previous position is kept.';update();
  });
  buildParts(); update();
  // Read-only inspection hook for focused browser checks; no saved progress.
  window.__explodingSyllable={snapshot:()=>({syllable:state.syllable,view:state.view,mode:state.mode,
    progress:{...state.progress},selected:state.selected}),setSyllable,setMode,setView};
})();
