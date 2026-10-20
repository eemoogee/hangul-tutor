(() => {
  'use strict';
  // Authored path endpoints are copied from the unchanged Exploding Syllable v2.
  const DATA = {
    '나': [
      {id:'initial',letter:'ㄴ',packed:[[[136,76],[136,221],[183,221]]],free:[[[48,92],[48,205],[126,205]]]},
      {id:'medial',letter:'ㅏ',packed:[[[212,65],[212,230]],[[212,145],[255,145]]],free:[[[270,83],[270,215]],[[270,148],[328,148]]]}
    ],
    '난': [
      {id:'initial',letter:'ㄴ',packed:[[[136,59],[136,150],[181,150]]],free:[[[42,52],[42,166],[121,166]]]},
      {id:'medial',letter:'ㅏ',packed:[[[211,57],[211,159]],[[211,110],[254,110]]],free:[[[270,60],[270,174]],[[270,115],[328,115]]]},
      {id:'final',letter:'ㄴ',packed:[[[143,187],[143,241],[236,241]]],free:[[[141,226],[141,294],[263,294]]]}
    ]
  };
  const NS='http://www.w3.org/2000/svg';
  const descriptions={
    flat:'The original v2 jamo paths move outward in the two-dimensional plane. There is no added depth.',
    relief:'The same planar extraction gains layered side strokes, a contact cue, a small component tilt, and forward movement.',
    layers:'Each jamo remains at its completed-block coordinates on its own translucent plate. The whole stack angles and the plates separate symmetrically along Z.'
  };
  const state={mode:'layers',syllable:'나',progress:0,angle:0,raf:0};
  const $=id=>document.getElementById(id);
  const clamp=x=>Math.max(0,Math.min(1,x));
  const lerp=(a,b,t)=>a+(b-a)*t;
  const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
  function svg(tag,attrs={}){const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);return el;}
  function path(lines){return lines.map(line=>line.map((point,i)=>`${i?'L':'M'}${point[0]} ${point[1]}`).join(' ')).join(' ');}
  function interpolated(part,t){return part.packed.map((line,i)=>line.map((p,j)=>[+(lerp(p[0],part.free[i][j][0],t)).toFixed(1),+(lerp(p[1],part.free[i][j][1],t)).toFixed(1)]));}
  function makeDrawing(part,geometry=part.packed){const drawing=svg('svg',{viewBox:'0 0 360 320','aria-hidden':'true'});drawing.append(svg('path',{class:'stroke',d:path(geometry)}));return drawing;}
  function build(){
    const stack=$('stack');stack.replaceChildren();
    const front=$('front-view');front.replaceChildren();
    const parts=DATA[state.syllable];
    for(const part of parts)front.append(svg('path',{d:path(part.packed)}));
    front.setAttribute('aria-label',`Completed ${state.syllable}, front view`);
    if(state.mode==='layers'){
      for(const part of parts){
        const plate=document.createElement('div');plate.className='plate';plate.dataset.part=part.id;
        const drawing=makeDrawing(part);
        drawing.append(svg('text',{class:'corner',x:'24',y:'38'}));
        drawing.lastChild.textContent=part.letter;
        plate.append(drawing);stack.append(plate);
      }
    }else{
      for(const part of parts){
        const component=document.createElement('div');component.className='component';component.dataset.part=part.id;
        const drawing=svg('svg',{viewBox:'0 0 360 320','aria-hidden':'true'});
        if(state.mode==='relief'){
          drawing.append(svg('ellipse',{class:'contact',cx:part.id==='initial'?158:part.id==='medial'?211:190,cy:part.id==='final'?247:part.id==='medial'?228:220,rx:'46',ry:'12'}));
          drawing.append(svg('path',{class:'footprint',d:path(part.packed)}));
          for(let i=8;i>=1;i--)drawing.append(svg('path',{class:'side','data-level':i}));
        }
        drawing.append(svg('path',{class:'stroke'}));component.append(drawing);stack.append(component);
      }
    }
    $('mode-description').textContent=descriptions[state.mode];
    render();
  }
  function render(){
    const p=state.progress,parts=DATA[state.syllable],stack=$('stack');
    if(state.mode==='layers'){
      stack.style.transform=`scale(var(--model-scale, 1)) rotateX(${(58*p).toFixed(2)}deg) rotateZ(${(-45*p+state.angle*p).toFixed(2)}deg)`;
      stack.querySelectorAll('.plate').forEach((plate,i)=>{
        const z=(i-(parts.length-1)/2)*105*p;
        plate.style.transform=`translateZ(${z.toFixed(2)}px)`;
        plate.style.setProperty('--plate-alpha',(0.19*p).toFixed(3));
        plate.style.setProperty('--plate-edge',(0.74*p).toFixed(3));
        plate.style.setProperty('--label-alpha',(0.92*p).toFixed(3));
      });
    }else{
      stack.style.transform='none';
      stack.querySelectorAll('.component').forEach((component,i)=>{
        const part=parts[i],d=path(interpolated(part,p));
        component.querySelector('.stroke').setAttribute('d',d);
        if(state.mode==='relief'){
          component.style.transform=`translateZ(${(72*p).toFixed(2)}px) rotateX(${(7*p).toFixed(2)}deg) rotateY(${(-6*p).toFixed(2)}deg)`;
          component.style.setProperty('--footprint-alpha',(0.5*p).toFixed(2));
          component.style.setProperty('--contact-alpha',(0.36*p).toFixed(2));
          component.querySelectorAll('.side').forEach(side=>{
            const level=+side.dataset.level;side.setAttribute('d',d);
            side.setAttribute('transform',`translate(${(12*p*level/8).toFixed(1)} ${(14*p*level/8).toFixed(1)})`);
          });
        }
      });
    }
    $('progress').value=Math.round(p*100);$('progress-value').textContent=`${Math.round(p*100)}%`;
    $('state-title').textContent=p===0?`Completed ${state.syllable}`:p===1?`Expanded ${state.syllable}`:`Opening ${state.syllable}`;
    $('toggle').textContent=p>.5?'Close syllable':'Open syllable';
    $('scene').setAttribute('aria-label',`${state.syllable}, ${state.mode} presentation, ${Math.round(p*100)} percent open. Press to ${p>.5?'close':'open'}.`);
    $('scene').setAttribute('aria-pressed',String(p>.5));
    for(const id of ['rotate-left','rotate-right','reset-angle'])$(id).disabled=state.mode!=='layers'||p<.99;
    document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode)));
    document.querySelectorAll('[data-syllable]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.syllable===state.syllable)));
  }
  function stop(){if(state.raf)cancelAnimationFrame(state.raf);state.raf=0;}
  function move(target){
    stop();const start=state.progress;
    if(reduced()){state.progress=target;render();$('status').textContent=`${state.syllable} ${target?'expanded':'closed'} in ${state.mode} view.`;return;}
    const startTime=performance.now(),duration=760;
    function frame(now){const t=clamp((now-startTime)/duration),ease=t*t*(3-2*t);state.progress=lerp(start,target,ease);render();if(t<1)state.raf=requestAnimationFrame(frame);else{state.raf=0;$('status').textContent=`${state.syllable} ${target?'expanded and paused':'closed'} in ${state.mode} view.`;}}
    state.raf=requestAnimationFrame(frame);
  }
  function toggle(){move(state.progress>.5?0:1);}
  $('scene').addEventListener('click',toggle);
  $('scene').addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();toggle();}});
  $('toggle').addEventListener('click',toggle);
  document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{stop();state.mode=button.dataset.mode;state.angle=0;build();$('status').textContent=`${state.mode} presentation selected for ${state.syllable}.`;}));
  document.querySelectorAll('[data-syllable]').forEach(button=>button.addEventListener('click',()=>{stop();state.syllable=button.dataset.syllable;state.progress=0;state.angle=0;build();$('status').textContent=`Completed ${state.syllable}, front facing.`;}));
  $('rotate-left').addEventListener('click',()=>{state.angle=Math.max(-40,state.angle-15);render();});
  $('rotate-right').addEventListener('click',()=>{state.angle=Math.min(40,state.angle+15);render();});
  $('reset-angle').addEventListener('click',()=>{state.angle=0;render();});
  $('progress').addEventListener('input',event=>{stop();state.progress=+event.target.value/100;render();$('status').textContent=`${state.syllable} at ${event.target.value} percent open.`;});
  build();
  window.__layersStudy={snapshot:()=>({...state,raf:Boolean(state.raf)})};
})();
