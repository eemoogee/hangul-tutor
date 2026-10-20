(() => {
  'use strict';
  // Authored instructional polylines. No font outline is read or transformed.
  const GLYPHS = {
    '나': {parts:[
      {id:'initial',letter:'ㄴ',role:'initial consonant',packed:[[[136,76],[136,221],[183,221]]],free:[[[48,92],[48,205],[126,205]]]},
      {id:'medial',letter:'ㅏ',role:'medial vowel',packed:[[[212,65],[212,230]],[[212,145],[255,145]]],free:[[[270,83],[270,215]],[[270,148],[328,148]]]}
    ],insight:'In 나, ㄴ sits beside ㅏ. Both fit into the same square, but each keeps its own role.'},
    '노': {parts:[
      {id:'initial',letter:'ㄴ',role:'initial consonant',packed:[[[130,70],[130,151],[237,151]]],free:[[[55,67],[55,183],[163,183]]]},
      {id:'medial',letter:'ㅗ',role:'medial vowel',packed:[[[185,169],[185,215]],[[120,215],[250,215]]],free:[[[268,151],[268,213]],[[201,213],[331,213]]]}
    ],insight:'In 노, ㅗ sits below ㄴ. The block stacks its parts instead of placing them side by side.'},
    '난': {parts:[
      {id:'initial',letter:'ㄴ',role:'initial consonant',packed:[[[136,59],[136,150],[181,150]]],free:[[[42,52],[42,166],[121,166]]]},
      {id:'medial',letter:'ㅏ',role:'medial vowel',packed:[[[211,57],[211,159]],[[211,110],[254,110]]],free:[[[270,60],[270,174]],[[270,115],[328,115]]]},
      {id:'final',letter:'ㄴ',role:'final consonant',packed:[[[143,187],[143,241],[236,241]]],free:[[[141,226],[141,294],[263,294]]]}
    ],insight:'In 난, the final ㄴ takes the lower region. The initial ㄴ and ㅏ use less height above it.'}
  };
  const $ = id => document.getElementById(id);
  const el = {stage:$('stage'),parts:$('parts'),relief:$('relief-scene'),conditions:$('lift-conditions'),legend:$('legend'),reference:$('reference'),title:$('svg-title'),desc:$('svg-desc'),
    stageLabel:$('stage-label'),stateLabel:$('state-label'),caption:$('method-caption'),instruction:$('instruction'),main:$('main-action'),
    back:$('return-action'),slider:$('progress'),output:$('progress-output'),help:$('slider-help'),feedback:$('feedback'),insight:$('insight')};
  const NS='http://www.w3.org/2000/svg';
  const state={syllable:'나',method:'separation',condition:'flat',progress:{initial:0,medial:0},flow:0,selected:null,raf:null,drag:null,suppress:false};
  const nodes=new Map(),reliefNodes=new Map();
  const clamp=n=>Math.max(0,Math.min(1,n));
  const lerp=(a,b,t)=>a+(b-a)*t;
  const fmt=n=>Math.round(n*10)/10;
  const shape=(segments)=>segments.map(line=>line.map((point,i)=>`${i?'L':'M'}${fmt(point[0])} ${fmt(point[1])}`).join(' ')).join(' ');
  const center=segments=>{const pts=segments.flat();return [pts.reduce((sum,p)=>sum+p[0],0)/pts.length,pts.reduce((sum,p)=>sum+p[1],0)/pts.length];};
  const tween=(a,b,t)=>a.map((line,i)=>line.map((point,j)=>[lerp(point[0],b[i][j][0],t),lerp(point[1],b[i][j][1],t)]));
  const shifted=(a,b,t)=>{const ac=center(a),bc=center(b);return a.map(line=>line.map(p=>[p[0]+(bc[0]-ac[0])*t,p[1]+(bc[1]-ac[1])*t]));};
  const pts=(part,t)=>state.method==='separation'?shifted(part.packed,part.free,t):tween(part.packed,part.free,t);
  const svg=(tag,attrs)=>{const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);return n;};
  const activeParts=()=>state.method==='reflow'?GLYPHS['난'].parts:GLYPHS[state.syllable].parts;
  const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
  function cancel(){if(state.raf)cancelAnimationFrame(state.raf);state.raf=null;}
  function geometry(part){
    if(state.method!=='reflow')return pts(part,state.progress[part.id]||0);
    const na=GLYPHS['나'].parts.find(p=>p.id===part.id);
    const from=na?na.packed:part.free.map(line=>line.map(p=>[p[0],p[1]+25]));
    return tween(from,part.packed,state.flow);
  }
  function rebuild(){
    el.parts.replaceChildren();el.relief.replaceChildren();el.legend.replaceChildren();nodes.clear();reliefNodes.clear();state.selected=null;
    for(const part of activeParts()){
      const g=svg('g',{'class':'component','data-part':part.id,role:'button',tabindex:'0'});
      const stroke=svg('path',{'class':'stroke'}),hit=svg('path',{'class':'hit'});
      g.append(stroke,hit);el.parts.append(g);nodes.set(part.id,{g,stroke,hit});
      const wrapper=document.createElement('div');wrapper.className='relief-piece';wrapper.dataset.wrapper=part.id;
      const layer=svg('svg',{viewBox:'0 0 360 320','aria-hidden':'false'});
      const lifted=svg('g',{'class':'relief-component','data-part':part.id,role:'button',tabindex:'0'});
      const reliefStroke=svg('path',{'class':'stroke'}),reliefHit=svg('path',{'class':'hit'});
      lifted.append(reliefStroke,reliefHit);layer.append(lifted);wrapper.append(layer);el.relief.append(wrapper);
      reliefNodes.set(part.id,{wrapper,g:lifted,stroke:reliefStroke,hit:reliefHit});
      const b=document.createElement('button');b.type='button';b.dataset.choose=part.id;b.className=part.id;
      b.innerHTML=`<i aria-hidden="true"></i><span>${part.letter} · ${part.id}</span>`;
      b.setAttribute('aria-label',`Select ${part.role} ${part.letter}`);el.legend.append(b);
    }
    update();
  }
  function update(){
    const parts=activeParts(),values=state.method==='reflow'?[state.flow]:parts.map(p=>state.progress[p.id]||0);
    const amount=Math.max(...values),all=values.every(v=>v>.985),none=values.every(v=>v<.015);
    const extraction=state.method==='extraction';
    el.relief.hidden=!extraction;el.conditions.hidden=!extraction;el.parts.style.display=extraction?'none':'';
    document.querySelectorAll('[data-condition]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.condition===state.condition)));
    for(const part of parts){
      const n=nodes.get(part.id),d=shape(geometry(part));n.stroke.setAttribute('d',d);n.hit.setAttribute('d',d);
      const r=reliefNodes.get(part.id),p=state.progress[part.id]||0;
      r.stroke.setAttribute('d',d);r.hit.setAttribute('d',d);
      r.wrapper.style.setProperty('--lift-z',`${extraction&&state.condition==='depth'?fmt(p*56):0}px`);
      r.wrapper.style.zIndex=state.selected===part.id?'2':'1';
      r.g.setAttribute('aria-label',`${part.role} ${part.letter}. ${Math.round(p*100)} percent lifted. Press to ${p>.5?'return':'lift'}.`);
      const visible=state.method!=='reflow'||part.id!=='final'||state.flow>.04;
      n.g.style.opacity=visible?String(part.id==='final'&&state.method==='reflow'?Math.min(1,state.flow*4):1):'0';
      n.g.style.pointerEvents=visible?'auto':'none';
      n.g.dataset.selected=String(state.selected===part.id);
      n.g.setAttribute('aria-label',`${part.role} ${part.letter}. ${Math.round((state.method==='reflow'?state.flow:state.progress[part.id]||0)*100)} percent ${state.method==='reflow'?'of final-consonant reflow':'separated'}. Select or move.`);
      const origin=$('origin-'+part.id);origin.setAttribute('d',shape(state.method==='reflow'?(GLYPHS['나'].parts.find(p=>p.id===part.id)||part).packed:part.packed));
      origin.style.opacity=state.method==='reflow'?String(state.flow>.04?.45:0):String((state.progress[part.id]||0)>.04?.5:0);
    }
    if(!parts.some(p=>p.id==='final'))$('origin-final').style.opacity='0';
    const endpoint=state.method==='reflow'?(state.flow<.02?'나':state.flow>.98?'난':null):state.syllable;
    document.querySelectorAll('[data-syllable]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.syllable===endpoint)));
    document.querySelectorAll('[data-method]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.method===state.method)));
    el.legend.querySelectorAll('[data-choose]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.choose===state.selected)));
    const displayed=state.method==='reflow'?(state.flow>.5?'난':'나'):state.syllable;
    el.reference.textContent=displayed;
    el.title.textContent=`${displayed}, an initial consonant and vowel${displayed==='난'?' with a final consonant':''}`;
    el.desc.textContent=state.method==='reflow'?'Adding or removing final ㄴ changes the room available to ㄴ and ㅏ.':extraction?'Tap a component to lift it; tap again to return it.':'Select a component and move it outward or back.';
    el.stageLabel.textContent=state.method==='reflow'?'나 ↔ 난 / FINAL CONSONANT':`${state.syllable} / ${parts.length===3?'INITIAL + MEDIAL + FINAL':'INITIAL + MEDIAL'}`;
    el.stateLabel.textContent=state.method==='reflow'?(none?'NO FINAL':all?'FINAL ADDED':'REFLOWING'):(none?'TOGETHER':extraction?'LIFTED':all?'APART':'IN BETWEEN');
    el.caption.textContent=state.method==='separation'?'01 / Separation':state.method==='deformation'?'02 / Deformation':state.method==='reflow'?'03 / Reflow':'04 / Extraction';
    el.instruction.textContent=state.method==='reflow'?'Add or remove final ㄴ. The other two letters make room.':extraction?'Tap a stroke to lift it. Tap again to return it. The other parts stay in place.':state.selected?`Move ${parts.find(p=>p.id===state.selected)?.letter} alone, or drag it in the diagram.`:'Open all, or select one component to move it alone.';
    el.help.textContent=extraction?'Tap a stroke or labeled part to lift it. Dragging and the slider allow intermediate positions. Arrow keys work on the slider.':'Drag a stroke, tap a labeled part then Move selected, or use this slider. Arrow keys work on the slider.';
    el.main.textContent=state.method==='reflow'?(state.flow>.5?'Remove final ㄴ':'Add final ㄴ'):extraction?(amount>.5?'Return selected':'Lift selected'):state.selected?(state.progress[state.selected]>.5?'Return selected':'Move selected'):(amount>.5?'Close all':'Open all');
    const value=state.method==='reflow'?state.flow:state.selected?state.progress[state.selected]:amount;
    el.slider.value=Math.round(value*100);el.output.textContent=`${Math.round(value*100)}%`;
    el.insight.textContent=state.method==='reflow'?'In this custom drawing, adding final ㄴ reduces the height available to the initial ㄴ and medial ㅏ. Their identities do not change.':GLYPHS[state.syllable].insight;
  }
  function setValue(target){
    if(state.method==='reflow')state.flow=clamp(target);
    else if(state.selected)state.progress[state.selected]=clamp(target);
    else for(const part of activeParts())state.progress[part.id]=clamp(target);
    update();
  }
  function animate(target){
    cancel();const start=state.method==='reflow'?state.flow:state.selected?state.progress[state.selected]:Math.max(...Object.values(state.progress));
    if(reduced()){setValue(target);return;}
    const duration=480,begin=performance.now();
    function frame(now){const t=clamp((now-begin)/duration),ease=1-Math.pow(1-t,3);setValue(lerp(start,target,ease));state.raf=t<1?requestAnimationFrame(frame):null;}
    state.raf=requestAnimationFrame(frame);
  }
  function lift(id,target){
    cancel();state.selected=id;
    const starts=Object.fromEntries(activeParts().map(p=>[p.id,state.progress[p.id]||0]));
    const ends=Object.fromEntries(activeParts().map(p=>[p.id,p.id===id?target:0]));
    if(reduced()){state.progress=ends;update();return;}
    const begin=performance.now(),duration=480;
    function frame(now){
      const t=clamp((now-begin)/duration),ease=1-Math.pow(1-t,3);
      for(const part of activeParts())state.progress[part.id]=lerp(starts[part.id],ends[part.id],ease);
      update();state.raf=t<1?requestAnimationFrame(frame):null;
    }
    state.raf=requestAnimationFrame(frame);
  }
  function toggleLift(id){
    const target=state.selected===id&&(state.progress[id]||0)>.5?0:1;
    lift(id,target);el.feedback.textContent=target?'The selected part lifts while the others stay anchored.':'The selected part returns to the completed syllable.';
  }
  function setSyllable(value){
    cancel();if(state.method==='reflow'&&value==='노'){state.method='deformation';}
    state.syllable=value;state.progress={initial:0,medial:0,final:0};state.flow=state.method==='reflow'&&value==='난'?1:0;
    rebuild();el.feedback.textContent=`${value} is ready for inspection.`;
  }
  function setMethod(value){
    cancel();if(state.method==='reflow'&&value!=='reflow')state.syllable=state.flow>.5?'난':'나';
    state.method=value;if(value==='reflow'&&state.syllable==='노')state.syllable='나';
    state.progress={initial:0,medial:0,final:0};state.flow=value==='reflow'&&state.syllable==='난'?1:0;
    rebuild();el.feedback.textContent=value==='reflow'?'The final ㄴ changes the space used by the other parts.':value==='extraction'?'Tap a stroke to lift it; tap again to return it.':'Select a letter or use the transition control.';
  }
  function setCondition(value){if(!['flat','depth'].includes(value))return;state.condition=value;update();}
  function select(id){cancel();state.selected=id;update();el.feedback.textContent=`${activeParts().find(p=>p.id===id).role} selected. Move it with the button, slider, keyboard, or a drag.`;}
  function toggle(id){cancel();state.selected=id;const current=state.method==='reflow'?state.flow:state.progress[id];animate(current>.5?0:1);el.feedback.textContent=state.method==='reflow'?'Final ㄴ and the upper letters reflow together.':`${id} moves while the other component stays in place.`;}
  document.querySelectorAll('[data-syllable]').forEach(b=>b.addEventListener('click',()=>setSyllable(b.dataset.syllable)));
  document.querySelectorAll('[data-method]').forEach(b=>b.addEventListener('click',()=>setMethod(b.dataset.method)));
  document.querySelectorAll('[data-condition]').forEach(b=>b.addEventListener('click',()=>setCondition(b.dataset.condition)));
  el.main.addEventListener('click',()=>{if(state.method==='extraction'){toggleLift(state.selected||activeParts()[0].id);return;}const current=state.method==='reflow'?state.flow:state.selected?state.progress[state.selected]:Math.max(...Object.values(state.progress));animate(current>.5?0:1);el.feedback.textContent=state.method==='reflow'?'The top parts adjust as final ㄴ enters or leaves.':'The paths can pause at any intermediate position.';});
  el.back.addEventListener('click',()=>{if(state.method==='extraction'){lift(state.selected||activeParts()[0].id,0);}else{state.selected=null;animate(0);}el.feedback.textContent='The parts returned to their composed arrangement.';});
  el.slider.addEventListener('input',()=>{cancel();if(state.method==='extraction'){state.selected=state.selected||activeParts()[0].id;for(const p of activeParts())state.progress[p.id]=p.id===state.selected?Number(el.slider.value)/100:0;update();}else setValue(Number(el.slider.value)/100);el.feedback.textContent='Paused between the two authored endpoint drawings.';});
  el.legend.addEventListener('click',e=>{const b=e.target.closest('[data-choose]');if(b){if(state.method==='extraction')toggleLift(b.dataset.choose);else select(b.dataset.choose);}});
  el.parts.addEventListener('click',e=>{const g=e.target.closest('[data-part]');if(!g||state.suppress)return;state.selected===g.dataset.part?toggle(g.dataset.part):select(g.dataset.part);});
  el.parts.addEventListener('keydown',e=>{if(!['Enter',' '].includes(e.key))return;const g=e.target.closest('[data-part]');if(!g)return;e.preventDefault();state.selected===g.dataset.part?toggle(g.dataset.part):select(g.dataset.part);});
  el.stage.addEventListener('pointerdown',e=>{
    if(e.button!==undefined&&e.button!==0)return;const g=e.target.closest('[data-part]');if(!g)return;
    cancel();const id=g.dataset.part,part=activeParts().find(p=>p.id===id);select(id);
    const naPart=GLYPHS['나'].parts.find(p=>p.id===id);
    const from=state.method==='reflow'?(naPart?naPart.packed:part.free.map(line=>line.map(p=>[p[0],p[1]+25]))):part.packed;
    const to=state.method==='reflow'?part.packed:part.free;
    const a=center(from),b=center(to),m=el.stage.getScreenCTM(),vx=(b[0]-a[0])*m.a+(b[1]-a[1])*m.c,vy=(b[0]-a[0])*m.b+(b[1]-a[1])*m.d;
    const distance=Math.max(24,Math.hypot(vx,vy));
    state.drag={id,pointerId:e.pointerId,x:e.clientX,y:e.clientY,start:state.method==='reflow'?state.flow:state.progress[id],vx:vx/distance,vy:vy/distance,distance,moved:false};
    el.stage.setPointerCapture(e.pointerId);
  });
  el.stage.addEventListener('pointermove',e=>{const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    const dx=e.clientX-d.x,dy=e.clientY-d.y;if(Math.hypot(dx,dy)>5)d.moved=true;if(!d.moved)return;
    const value=clamp(d.start+(dx*d.vx+dy*d.vy)/d.distance);
    if(state.method==='reflow')state.flow=value;else state.progress[d.id]=value;
    update();el.feedback.textContent='The selected part moves continuously; unchanged parts retain their SVG elements.';
  });
  el.stage.addEventListener('pointerup',e=>{const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    if(d.moved){state.suppress=true;setTimeout(()=>{state.suppress=false;},0);}state.drag=null;
  });
  el.stage.addEventListener('pointercancel',e=>{const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    if(state.method==='reflow')state.flow=d.start;else state.progress[d.id]=d.start;state.drag=null;update();
  });
  el.relief.addEventListener('pointerdown',e=>{
    if(e.button!==undefined&&e.button!==0)return;
    const g=e.target.closest('[data-part]');if(!g)return;
    cancel();const id=g.dataset.part,part=activeParts().find(p=>p.id===id);
    const a=center(part.packed),b=center(part.free),m=el.stage.getScreenCTM();
    const vx=(b[0]-a[0])*m.a+(b[1]-a[1])*m.c,vy=(b[0]-a[0])*m.b+(b[1]-a[1])*m.d;
    const distance=Math.max(24,Math.hypot(vx,vy));
    state.drag={id,pointerId:e.pointerId,x:e.clientX,y:e.clientY,start:state.progress[id]||0,vx:vx/distance,vy:vy/distance,distance,moved:false};
    el.relief.setPointerCapture(e.pointerId);
  });
  el.relief.addEventListener('pointermove',e=>{
    const d=state.drag;if(!d||d.pointerId!==e.pointerId||state.method!=='extraction')return;
    const dx=e.clientX-d.x,dy=e.clientY-d.y;
    if(Math.hypot(dx,dy)>5)d.moved=true;if(!d.moved)return;
    state.selected=d.id;
    for(const part of activeParts())state.progress[part.id]=part.id===d.id?clamp(d.start+(dx*d.vx+dy*d.vy)/d.distance):0;
    update();el.feedback.textContent='The selected part moves continuously while the others stay anchored.';
  });
  el.relief.addEventListener('pointerup',e=>{
    const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    state.drag=null;if(!d.moved)toggleLift(d.id);
  });
  el.relief.addEventListener('pointercancel',e=>{
    const d=state.drag;if(!d||d.pointerId!==e.pointerId)return;
    state.progress[d.id]=d.start;state.drag=null;update();
  });
  el.relief.addEventListener('keydown',e=>{
    if(!['Enter',' '].includes(e.key))return;const g=e.target.closest('[data-part]');if(!g)return;
    e.preventDefault();toggleLift(g.dataset.part);
  });
  rebuild();
  window.__syllableV2={snapshot:()=>({syllable:state.syllable,method:state.method,condition:state.condition,selected:state.selected,progress:{...state.progress},flow:state.flow}),setSyllable,setMethod,setCondition};
})();
