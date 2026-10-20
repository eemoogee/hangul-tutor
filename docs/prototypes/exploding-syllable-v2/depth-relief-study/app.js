(() => {
  'use strict';
  // Copied unchanged from v2's authored 나 endpoints; both panels share this data.
  const PARTS = [
    {id:'initial',letter:'ㄴ',role:'initial consonant',packed:[[[136,76],[136,221],[183,221]]],free:[[[48,92],[48,205],[126,205]]]},
    {id:'medial',letter:'ㅏ',role:'medial vowel',packed:[[[212,65],[212,230]],[[212,145],[255,145]]],free:[[[270,83],[270,215]],[[270,148],[328,148]]]}
  ];
  const NS='http://www.w3.org/2000/svg';
  const VIEW='0 35 360 250';
  const state={selected:null,progress:{initial:0,medial:0},raf:null};
  const panels=new Map();
  const $=id=>document.getElementById(id);
  const clamp=n=>Math.max(0,Math.min(1,n));
  const lerp=(a,b,t)=>a+(b-a)*t;
  const round=n=>Math.round(n*10)/10;
  const tween=(a,b,t)=>a.map((line,i)=>line.map((point,j)=>[lerp(point[0],b[i][j][0],t),lerp(point[1],b[i][j][1],t)]));
  const path=segments=>segments.map(line=>line.map((point,i)=>`${i?'L':'M'}${round(point[0])} ${round(point[1])}`).join(' ')).join(' ');
  const svg=(tag,attrs={})=>{const element=document.createElementNS(NS,tag);for(const [key,value] of Object.entries(attrs))element.setAttribute(key,value);return element;};
  const prefersReduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
  function buildPanel(mode){
    const scene=document.querySelector(`[data-scene="${mode}"]`);
    const ground=svg('svg',{viewBox:VIEW,'aria-hidden':'true'});
    const defs=svg('defs');
    const pattern=svg('pattern',{id:`dots-${mode}`,width:'20',height:'20',patternUnits:'userSpaceOnUse'});
    pattern.append(svg('circle',{class:'grid-dot',cx:'1',cy:'1',r:'1'}));defs.append(pattern);ground.append(defs);
    const gradient=svg('radialGradient',{id:`contact-${mode}`});
    gradient.append(svg('stop',{offset:'0%','stop-color':'#34484a','stop-opacity':'.42'}),svg('stop',{offset:'100%','stop-color':'#34484a','stop-opacity':'0'}));
    defs.append(gradient);
    ground.append(svg('rect',{x:'0',y:'35',width:'360',height:'250',fill:`url(#dots-${mode})`}));
    ground.append(svg('rect',{class:'block-frame',x:'111',y:'44',width:'148',height:'216',rx:'13'}));
    const pieces=new Map();
    for(const part of PARTS){
      const shadow=svg('ellipse',{class:'contact-shadow','data-shadow':part.id,cx:part.id==='initial'?'161':'213',cy:part.id==='initial'?'228':'237',rx:part.id==='initial'?'39':'25',ry:'12',fill:`url(#contact-${mode})`});
      const footprint=svg('path',{class:'footprint','data-footprint':part.id,d:path(part.packed)});
      ground.append(shadow,footprint);
      pieces.set(part.id,{shadow,footprint});
    }
    scene.append(ground);
    for(const part of PARTS){
      const wrapper=document.createElement('div');wrapper.className='piece';wrapper.dataset.part=part.id;
      const drawing=svg('svg',{viewBox:VIEW});
      const group=svg('g',{class:'component','data-component':part.id,role:'button',tabindex:'0'});
      const sides=[];
      if(mode==='relief')for(let i=8;i>=1;i--){const side=svg('path',{class:'side'});group.append(side);sides.push({side,level:i});}
      const front=svg('path',{class:'front'}),hit=svg('path',{class:'hit'});
      group.append(front,hit);drawing.append(group);wrapper.append(drawing);scene.append(wrapper);
      Object.assign(pieces.get(part.id),{wrapper,group,front,hit,sides});
    }
    panels.set(mode,{scene,pieces});
  }
  function update(){
    for(const [mode,panel] of panels){
      for(const part of PARTS){
        const node=panel.pieces.get(part.id),amount=state.progress[part.id]||0;
        const d=path(tween(part.packed,part.free,amount));
        node.front.setAttribute('d',d);node.hit.setAttribute('d',d);
        node.footprint.style.opacity=String(Math.min(.48,amount*.7));
        node.shadow.style.opacity=mode==='relief'?String(Math.min(.7,amount*.9)):'0';
        for(const {side,level} of node.sides){
          side.setAttribute('d',d);
          side.setAttribute('transform',`translate(${round(amount*12*level/8)} ${round(amount*14*level/8)})`);
          side.style.opacity=String(Math.min(1,amount*4));
        }
        node.wrapper.style.transform=mode==='relief'?`translateZ(${round(amount*72)}px) rotateX(${round(amount*7)}deg) rotateY(${-round(amount*6)}deg)`:'none';
        node.wrapper.style.zIndex=state.selected===part.id?'2':'1';
        node.group.setAttribute('aria-label',`${part.role} ${part.letter}, ${Math.round(amount*100)} percent lifted. Press to ${amount>.5?'return':'lift'}.`);
      }
    }
    document.querySelectorAll('[data-lift]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.lift===state.selected&&(state.progress[state.selected]||0)>.01)));
    const selected=PARTS.find(part=>part.id===state.selected);
    const value=selected?state.progress[selected.id]:0;
    $('progress').value=Math.round(value*100);
    $('progress-value').textContent=`${Math.round(value*100)}%`;
  }
  function cancel(){if(state.raf)cancelAnimationFrame(state.raf);state.raf=null;}
  function animate(id,target){
    cancel();state.selected=id;
    const letter=PARTS.find(part=>part.id===id).letter;
    $('status').textContent=target?`Lifting ${letter} in both views. The other jamo stays anchored.`:`Returning ${letter} to the completed syllable.`;
    const starts=Object.fromEntries(PARTS.map(part=>[part.id,state.progress[part.id]]));
    const ends=Object.fromEntries(PARTS.map(part=>[part.id,part.id===id?target:0]));
    if(prefersReduced()){state.progress=ends;update();$('status').textContent=target?`${letter} is lifted in both views.`:'Completed 나. Both pieces are in their original plane.';return;}
    const begin=performance.now(),duration=480;
    function frame(now){
      const t=clamp((now-begin)/duration),ease=1-Math.pow(1-t,3);
      for(const part of PARTS)state.progress[part.id]=lerp(starts[part.id],ends[part.id],ease);
      update();state.raf=t<1?requestAnimationFrame(frame):null;
      if(t>=1)$('status').textContent=target?`${letter} is lifted in both views.`:'Completed 나. Both pieces are in their original plane.';
    }
    state.raf=requestAnimationFrame(frame);
  }
  function toggle(id){animate(id,state.selected===id&&state.progress[id]>.5?0:1);}
  for(const mode of ['flat','relief'])buildPanel(mode);
  document.querySelectorAll('.scene').forEach(scene=>{
    scene.addEventListener('click',event=>{const component=event.target.closest('[data-component]');if(component)toggle(component.dataset.component);});
    scene.addEventListener('keydown',event=>{
      if(!['Enter',' '].includes(event.key))return;
      const component=event.target.closest('[data-component]');if(!component)return;
      event.preventDefault();toggle(component.dataset.component);
    });
  });
  document.querySelectorAll('[data-lift]').forEach(button=>button.addEventListener('click',()=>toggle(button.dataset.lift)));
  $('reassemble').addEventListener('click',()=>animate(state.selected||'initial',0));
  $('progress').addEventListener('input',event=>{
    cancel();state.selected=state.selected||'initial';
    for(const part of PARTS)state.progress[part.id]=part.id===state.selected?Number(event.target.value)/100:0;
    update();$('status').textContent=`${PARTS.find(part=>part.id===state.selected).letter} is at ${Math.round(state.progress[state.selected]*100)}% in both views.`;
  });
  update();
  window.__reliefStudy={snapshot:()=>({selected:state.selected,progress:{...state.progress}})};
})();
