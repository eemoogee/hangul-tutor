(() => {
  'use strict';
  // Packed centerlines retain Exploding Syllable v2's segment topology and were
  // visually recalibrated here against Noto Sans KR at the closed endpoint.
  // The filled face outlines are made with one fixed rule per jamo type.
  const GLYPHS = {
    '나': [
      {id:'initial',letter:'ㄴ',type:'L',role:'initial ㄴ',dir:[-1,0],packed:[[[118,111],[118,202],[194,202]]]},
      {id:'medial',letter:'ㅏ',type:'A',role:'vowel ㅏ',dir:[1,0],packed:[[[219,96],[219,242]],[[219,159],[247,159]]]}
    ],
    '노': [
      {id:'initial',letter:'ㄴ',type:'L',role:'initial ㄴ',dir:[0,-1],packed:[[[130,109],[130,168],[227,168]]]},
      {id:'medial',letter:'ㅗ',type:'O',role:'vowel ㅗ',dir:[0,1],packed:[[[177,169],[177,222]],[[112,222],[243,222]]]}
    ],
    '난': [
      {id:'initial',letter:'ㄴ',type:'L',role:'initial ㄴ',dir:[-.7071,-.7071],packed:[[[120,107],[120,169],[194,169]]]},
      {id:'medial',letter:'ㅏ',type:'A',role:'vowel ㅏ',dir:[.7071,-.7071],packed:[[[220,96],[220,198]],[[220,158],[247,158]]]},
      {id:'final',letter:'ㄴ',type:'L',role:'final ㄴ',dir:[0,1],packed:[[[137,200],[137,239],[229,239]]]}
    ]
  };
  const NS='http://www.w3.org/2000/svg';
  const $=id=>document.getElementById(id);
  const clamp=x=>Math.max(0,Math.min(1,x));
  const mix=(a,b,t)=>a+(b-a)*t;
  const fmt=n=>Number(n.toFixed(2));
  const shape=(a,b,t)=>a.map((line,i)=>line.map((point,j)=>[mix(point[0],b[i][j][0],t),mix(point[1],b[i][j][1],t)]));
  const bounds=lines=>{const pts=lines.flat(),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);return {minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)};};
  const center=lines=>{const b=bounds(lines);return [(b.minX+b.maxX)/2,(b.minY+b.maxY)/2];};
  const svg=(tag,attrs={})=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e;};
  function standalone(part){
    const [cx,cy]=center(part.packed);
    if(part.type==='L')return [[[cx-49,cy-56],[cx-49,cy+56],[cx+49,cy+56]]];
    if(part.type==='A')return [[[cx-20,cy-60],[cx-20,cy+60]],[[cx-20,cy-4],[cx+38,cy-4]]];
    return [[[cx,cy-38],[cx,cy+30]],[[cx-65,cy+30],[cx+65,cy+30]]];
  }
  for(const parts of Object.values(GLYPHS))for(const part of parts){
    part.free=standalone(part);
    if(part.packed.length!==part.free.length||part.packed.some((line,i)=>line.length!==part.free[i].length))throw Error(`Topology mismatch: ${part.role}`);
  }
  function rect(x1,y1,x2,y2){return `M${fmt(x1)} ${fmt(y1)}L${fmt(x2)} ${fmt(y1)}L${fmt(x2)} ${fmt(y2)}L${fmt(x1)} ${fmt(y2)}Z`;}
  function outline(lines,type){
    const h=6;
    if(type==='L'){
      const [a,b,c]=lines[0];
      return `M${fmt(a[0]-h)} ${fmt(a[1]-h)}L${fmt(a[0]+h)} ${fmt(a[1]-h)}L${fmt(b[0]+h)} ${fmt(b[1]-h)}L${fmt(c[0]+h)} ${fmt(c[1]-h)}L${fmt(c[0]+h)} ${fmt(c[1]+h)}L${fmt(b[0]-h)} ${fmt(b[1]+h)}Z`;
    }
    if(type==='A'){
      const [top,bottom]=lines[0],[start,end]=lines[1];
      return rect(top[0]-h,top[1]-h,bottom[0]+h,bottom[1]+h)+rect(start[0],start[1]-h,end[0]+h,end[1]+h);
    }
    const [top,bottom]=lines[0],[left,right]=lines[1];
    return rect(top[0]-h,top[1]-h,bottom[0]+h,bottom[1]+h)+rect(left[0]-h,left[1]-h,right[0]+h,right[1]+h);
  }
  const state={syllable:'나',variant:'v1',progress:0,inspect:null,distance:42,duration:760,depth:7,reduce:false,raf:0,timer:0};
  const nodes=new Map();
  const effectiveReduced=()=>state.reduce||matchMedia('(prefers-reduced-motion: reduce)').matches;
  function textVisible(show){$('type-glyph').classList.toggle('visible',show);$('pieces').classList.toggle('text-on',show);}
  function stop(){if(state.raf)cancelAnimationFrame(state.raf);if(state.timer)clearTimeout(state.timer);state.raf=0;state.timer=0;}
  function rebuild(){
    nodes.clear();$('pieces').replaceChildren();$('ground').replaceChildren();$('part-buttons').replaceChildren();
    for(const part of GLYPHS[state.syllable]){
      const ground=svg('svg',{viewBox:'0 0 360 360','aria-hidden':'true'});
      const origin=svg('path',{class:'origin',d:outline(part.packed,part.type)});
      const b=bounds(part.packed),[cx]=center(part.packed);
      const contact=svg('ellipse',{class:'contact',cx:cx,cy:b.maxY+13,rx:part.type==='A'?26:38,ry:6});
      ground.append(origin,contact);$('ground').append(ground);
      const wrapper=document.createElement('div');wrapper.className='piece';wrapper.dataset.part=part.id;
      const drawing=svg('svg',{viewBox:'0 0 360 360'});
      const group=svg('g',{class:'piece-group',role:'button',tabindex:'0','data-part':part.id});
      const sides=[];
      for(let i=8;i>=1;i--){const side=svg('path',{class:'side'});group.append(side);sides.push({el:side,level:i});}
      const front=svg('path',{class:'front'}),hit=svg('path',{class:'hit'}),hitBox=svg('rect',{class:'hit-box',width:58,height:58});
      group.append(front,hit,hitBox);drawing.append(group);wrapper.append(drawing);$('pieces').append(wrapper);
      group.addEventListener('click',event=>{event.stopPropagation();pieceTap(part.id);});
      group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();pieceTap(part.id);}});
      const button=document.createElement('button');button.type='button';button.dataset.part=part.id;
      button.textContent=`${part.role} · ${part.letter}`;button.addEventListener('click',()=>pieceTap(part.id));$('part-buttons').append(button);
      nodes.set(part.id,{part,wrapper,front,hit,hitBox,sides,origin,contact,group,button});
    }
    $('type-glyph').textContent=state.syllable;
    textVisible(state.progress===0);
    render();
  }
  function springPhase(p){
    if(p<=.16)return 0;
    if(p<.9){const t=(p-.16)/.74;return 1.035*(1-Math.pow(1-t,3));}
    const t=(p-.9)/.1;return mix(1.035,1,t*t*(3-2*t));
  }
  function render(){
    const p=state.progress,reduced=effectiveReduced(),seam=clamp(p/.16),motion=springPhase(p),morph=clamp((p-.16)/.74);
    const scale=$('stage').clientWidth/360;
    for(const {part,wrapper,front,hit,hitBox,sides,origin,contact,group,button} of nodes.values()){
      const lines=state.variant==='v1'?part.packed:shape(part.packed,part.free,morph);
      const d=outline(lines,part.type),[cx,cy]=center(lines),dx=part.dir[0]*state.distance*motion,dy=part.dir[1]*state.distance*motion;
      const selected=state.inspect===part.id&&p>.98;
      const z=state.variant==='v3'&&!reduced&&selected?state.depth*6:0;
      wrapper.style.transform=`translate3d(${fmt(dx*scale)}px,${fmt(dy*scale)}px,${fmt(z)}px)`;
      wrapper.style.zIndex=selected?'4':'1';
      front.setAttribute('d',d);front.classList.toggle('inspected',selected);
      hit.setAttribute('d',d);hitBox.setAttribute('x',fmt(cx-29));hitBox.setAttribute('y',fmt(cy-29));
      const thickness=state.variant==='v3'&&!reduced?state.depth*(.22*seam+.78*clamp(morph)):0;
      for(const {el,level} of sides){el.setAttribute('d',d);el.setAttribute('transform',`translate(${fmt(thickness*level/8)} ${fmt(thickness*level/8)})`);el.style.fillOpacity=thickness>0?'1':'0';}
      origin.style.strokeOpacity=String(fmt(.18*seam));
      contact.setAttribute('transform',`translate(${fmt(dx)} ${fmt(dy)})`);
      contact.style.fillOpacity=state.variant==='v3'&&!reduced?String(fmt((selected?.34:.13)*clamp(morph))):'0';
      group.setAttribute('aria-label',`${part.role} ${part.letter}. ${selected?'Return':'Inspect'} this piece.`);
      button.disabled=p<.98;button.setAttribute('aria-pressed',String(selected));
    }
    $('progress').value=Math.round(p*100);$('progress-value').textContent=`${Math.round(p*100)}%`;
    $('distance-value').textContent=`${state.distance} units`;$('duration-value').textContent=`${state.duration} ms`;$('depth-value').textContent=`${state.depth} units`;
    $('clear-inspect').disabled=!state.inspect;
    $('toggle').textContent=p>.5?'Close syllable':'Open syllable';
    $('stage-label').textContent=`${state.syllable} · ${p===0?'closed':p===1?'open':'opening'}`;
    $('phase-label').textContent=p===0?'REAL TEXT':p<.16?'LOOSEN':p<.9?'OPEN':p<1?'SETTLE':'HOLD';
    $('stage').setAttribute('aria-label',`${state.syllable}, ${Math.round(p*100)} percent open. Press Enter to ${p>.5?'close':'open'}.`);
    document.querySelectorAll('[data-variant]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.variant===state.variant)));
    document.querySelectorAll('[data-syllable]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.syllable===state.syllable)));
  }
  function animate(target){
    stop();state.inspect=null;
    if(effectiveReduced()){
      state.progress=target;render();textVisible(target===0);
      $('status').textContent=target?`${state.syllable} is open. Reduced motion uses a short fade and no depth.`:`${state.syllable} is assembled in real text.`;
      return;
    }
    const run=()=>{
      const begin=performance.now(),from=state.progress,duration=state.duration;
      const frame=now=>{
        const t=clamp((now-begin)/duration);state.progress=mix(from,target,t);render();
        if(t<1)state.raf=requestAnimationFrame(frame);
        else{state.raf=0;state.progress=target;render();if(target===0)textVisible(true);$('status').textContent=target?`${state.syllable} is open and still. Tap one piece to inspect it.`:`${state.syllable} is assembled in real text.`;}
      };
      state.raf=requestAnimationFrame(frame);
    };
    if(target===1&&state.progress===0){textVisible(false);state.timer=setTimeout(()=>{state.timer=0;run();},120);}
    else run();
  }
  function pieceTap(id){
    if(state.progress<.98){
      if(state.progress===0)animate(1);
      else{state.inspect=id;render();$('status').textContent=`${GLYPHS[state.syllable].find(p=>p.id===id).role} will be selected when opening settles.`;}
      return;
    }
    state.inspect=state.inspect===id?null:id;render();
    $('status').textContent=state.inspect?`${GLYPHS[state.syllable].find(p=>p.id===id).role} selected for inspection.`:'Inspection returned.';
  }
  $('stage').addEventListener('click',event=>{if(event.target.closest?.('.piece-group'))return;animate(state.progress>.5?0:1);});
  $('stage').addEventListener('keydown',event=>{if(event.target!==$('stage'))return;if(event.key==='Enter'||event.key===' '){event.preventDefault();animate(state.progress>.5?0:1);}});
  $('toggle').addEventListener('click',()=>animate(state.progress>.5?0:1));
  $('clear-inspect').addEventListener('click',()=>{state.inspect=null;render();});
  document.querySelectorAll('[data-variant]').forEach(button=>button.addEventListener('click',()=>{stop();state.variant=button.dataset.variant;state.inspect=null;render();$('status').textContent=`${button.textContent.trim()} selected at the same position.`;}));
  document.querySelectorAll('[data-syllable]').forEach(button=>button.addEventListener('click',()=>{stop();state.syllable=button.dataset.syllable;state.progress=0;state.inspect=null;rebuild();$('status').textContent=`Completed ${state.syllable}. Open to see its components.`;}));
  for(const id of ['distance','duration','depth'])$(id).addEventListener('input',event=>{state[id]=+event.target.value;render();});
  $('reduce').addEventListener('change',event=>{stop();state.reduce=event.target.checked;state.inspect=null;render();$('status').textContent=state.reduce?'Reduced-motion simulation is on.':'Reduced-motion simulation is off.';});
  $('progress').addEventListener('input',event=>{stop();state.progress=+event.target.value/100;state.inspect=null;textVisible(state.progress===0);render();$('status').textContent=`${state.syllable} at ${event.target.value}% of the transition.`;});
  matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',()=>{stop();state.inspect=null;render();});
  addEventListener('resize',render);
  rebuild();
  window.__reliefExploded={snapshot:()=>({syllable:state.syllable,variant:state.variant,progress:state.progress,inspect:state.inspect,distance:state.distance,duration:state.duration,depth:state.depth,reduced:effectiveReduced()}),
    topology:()=>Object.fromEntries(Object.entries(GLYPHS).map(([s,parts])=>[s,parts.map(p=>({id:p.id,packed:p.packed.map(x=>x.length),free:p.free.map(x=>x.length)}))]))};
})();
