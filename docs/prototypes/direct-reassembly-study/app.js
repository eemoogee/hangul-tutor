(() => {
  'use strict';

  // Coordinates and fixed path topology are adapted from the preserved
  // Relief-Exploded Syllable Study. These are authored instructional outlines.
  const NAN = [
    {id:'initial', label:'initial ㄴ', type:'L', dir:[-.7071,-.7071], packed:[[[120,107],[120,169],[194,169]]], na:[[[118,111],[118,202],[194,202]]]},
    {id:'medial', label:'vowel ㅏ', type:'A', dir:[.7071,-.7071], packed:[[[220,96],[220,198]],[[220,158],[247,158]]], na:[[[219,96],[219,242]],[[219,159],[247,159]]]},
    {id:'final', label:'final ㄴ', type:'L', dir:[0,1], packed:[[[137,200],[137,239],[229,239]]]}
  ];
  const NS='http://www.w3.org/2000/svg';
  const $=id=>document.getElementById(id);
  const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
  const mix=(a,b,t)=>a+(b-a)*t;
  const fmt=x=>Number(x.toFixed(2));
  const shape=(a,b,t)=>a.map((line,i)=>line.map((point,j)=>[mix(point[0],b[i][j][0],t),mix(point[1],b[i][j][1],t)]));
  const bounds=lines=>{const pts=lines.flat(),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);return {minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)};};
  const center=lines=>{const b=bounds(lines);return [(b.minX+b.maxX)/2,(b.minY+b.maxY)/2];};
  const svg=(tag,attrs={})=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e;};
  function standalone(part){
    const [cx,cy]=center(part.packed);
    if(part.type==='L')return [[[cx-49,cy-56],[cx-49,cy+56],[cx+49,cy+56]]];
    return [[[cx-20,cy-60],[cx-20,cy+60]],[[cx-20,cy-4],[cx+38,cy-4]]];
  }
  for(const part of NAN){
    part.free=standalone(part);
    for(const candidate of [part.free,part.na].filter(Boolean)){
      if(candidate.length!==part.packed.length||candidate.some((line,i)=>line.length!==part.packed[i].length))throw Error(`Topology mismatch: ${part.label}`);
    }
  }
  function rect(x1,y1,x2,y2){return `M${fmt(x1)} ${fmt(y1)}L${fmt(x2)} ${fmt(y1)}L${fmt(x2)} ${fmt(y2)}L${fmt(x1)} ${fmt(y2)}Z`;}
  function outline(lines,type){
    const h=6;
    if(type==='L'){
      const [a,b,c]=lines[0];
      return `M${fmt(a[0]-h)} ${fmt(a[1]-h)}L${fmt(a[0]+h)} ${fmt(a[1]-h)}L${fmt(b[0]+h)} ${fmt(b[1]-h)}L${fmt(c[0]+h)} ${fmt(c[1]-h)}L${fmt(c[0]+h)} ${fmt(c[1]+h)}L${fmt(b[0]-h)} ${fmt(b[1]+h)}Z`;
    }
    const [top,bottom]=lines[0],[start,end]=lines[1];
    return rect(top[0]-h,top[1]-h,bottom[0]+h,bottom[1]+h)+rect(start[0],start[1]-h,end[0]+h,end[1]+h);
  }

  const state={mode:'flat',phase:'closed',open:0,lift:0,place:0,dragX:0,dragY:0,returnStartQ:0,returnStartX:12,returnStartY:56,reduce:false,raf:0,active:false};
  const nodes=new Map();
  const reduced=()=>state.reduce||matchMedia('(prefers-reduced-motion: reduce)').matches;
  const scale=()=>$('stage').clientWidth/360;
  const ease=t=>1-Math.pow(1-t,3);
  const settle=t=>t<.88?1.012*ease(t/.88):mix(1.012,1,ease((t-.88)/.12));
  const slotDistance=()=>Math.hypot(12+state.dragX,56+state.dragY);
  function setText(on){$('type-glyph').classList.toggle('visible',on);$('pieces').classList.toggle('text-on',on);}
  function stop(){if(state.raf)cancelAnimationFrame(state.raf);state.raf=0;state.active=false;}
  function run(target,duration,done){
    stop();
    if(reduced()){
      Object.assign(state,target);render();done?.();return;
    }
    const from=Object.fromEntries(Object.keys(target).map(k=>[k,state[k]]));
    const start=performance.now();state.active=true;
    function frame(now){
      const t=clamp((now-start)/duration),f=settle(t);
      for(const [key,value] of Object.entries(target))state[key]=mix(from[key],value,f);
      render();
      if(t<1)state.raf=requestAnimationFrame(frame);
      else{Object.assign(state,target);state.raf=0;state.active=false;render();done?.();}
    }
    state.raf=requestAnimationFrame(frame);
  }
  function render(){
    const isReduced=reduced();
    const q=state.phase==='dragging'?clamp(1-slotDistance()/Math.hypot(12,56)):state.place;
    const opening=state.phase==='opening'||state.phase==='closed'||state.phase==='open'||state.phase==='lifting'||state.phase==='lifted';
    const loosen=clamp(state.open/.16);
    const motion=state.open<=.16?0:settle(clamp((state.open-.16)/.84));
    const morph=clamp((state.open-.16)/.74);
    const inReturn=!opening;
    const openAmount=inReturn?1:motion;
    const seam=inReturn?1:loosen;
    const near=state.phase==='dragging'&&slotDistance()<=38;
    for(const {part,wrapper,front,hit,box,sides,origin,contact,group} of nodes.values()){
      let lines,dx,dy;
      if(inReturn){
        if(part.id==='final'){
          lines=shape(part.free,part.packed,q);
          const remaining=(1-q)/(1-state.returnStartQ);
          dx=state.phase==='dragging'?12+state.dragX:state.returnStartX*remaining;
          dy=state.phase==='dragging'?56+state.dragY:state.returnStartY*remaining;
        }else{
          lines=q<.57?shape(part.free,part.na,clamp(q/.57)):shape(part.na,part.packed,clamp((q-.57)/.43));
          dx=part.dir[0]*42*(1-q);dy=part.dir[1]*42*(1-q);
        }
      }else{
        const growth=part.id==='final'?morph*(.4+.6*state.lift):morph;
        lines=shape(part.packed,part.free,growth);
        dx=part.dir[0]*42*openAmount+(part.id==='final'?12*state.lift:0);
        dy=part.dir[1]*42*openAmount+(part.id==='final'?14*state.lift:0);
      }
      const selected=part.id==='final'&&['lifting','lifted','dragging','returning'].includes(state.phase);
      const liftCue=part.id==='final'?(inReturn?(1-q):state.lift):0;
      const z=state.mode==='relief'&&!isReduced?32*liftCue:0;
      wrapper.style.transform=`translate3d(${fmt(dx*scale())}px,${fmt(dy*scale())}px,${fmt(z)}px)`;
      wrapper.style.zIndex=selected?'4':'1';
      const d=outline(lines,part.type),[cx,cy]=center(lines);
      front.setAttribute('d',d);front.classList.toggle('selected',selected);
      hit.setAttribute('d',d);box.setAttribute('x',fmt(cx-32));box.setAttribute('y',fmt(cy-32));
      const thickness=state.mode==='relief'&&!isReduced?7*(.22*seam+.78*(inReturn?1-q:morph)):0;
      for(const {el,level} of sides){el.setAttribute('d',d);el.setAttribute('transform',`translate(${fmt(thickness*level/8)} ${fmt(thickness*level/8)})`);el.style.fillOpacity=thickness>0?'1':'0';}
      origin.style.strokeOpacity=String(fmt(part.id==='final'?.42*seam*(inReturn?1-q:1):.15*seam*(1-q)));
      contact.style.fillOpacity=part.id==='final'&&state.mode==='relief'&&!isReduced?String(fmt(.31*liftCue)):'0';
      group.setAttribute('aria-label',`${part.label}. ${part.id==='final'?(state.phase==='open'?'Lift this piece.':selected?'Return this piece to its slot.':''):'Upper piece remains anchored while the final ㄴ lifts.'}`);
    }
    $('slot-outline').classList.toggle('near',near);
    $('slot-outline').style.strokeOpacity=String(fmt(.55*seam*(1-q)));
    $('slot-group').classList.toggle('available',['lifted','dragging'].includes(state.phase));
    $('slot-group').setAttribute('aria-hidden',String(!['lifted','dragging'].includes(state.phase)));
    $('slot-group').setAttribute('tabindex',['lifted','dragging'].includes(state.phase)?'0':'-1');
    $('phase').textContent=({closed:'ASSEMBLED',opening:'OPENING',open:'OPEN',lifting:'LIFTING',lifted:'LIFTED',dragging:'APPROACH',returning:'RETURNING',complete:'ASSEMBLED'})[state.phase];
    const canOpen=['closed','complete'].includes(state.phase);
    $('stage').setAttribute('aria-label',canOpen?`Open 난${state.phase==='complete'?' again':''}`:`난 ${state.phase}. Final ㄴ is ${selectedLabel()}.`);
    $('stage').setAttribute('role',canOpen?'button':'img');
    $('stage').setAttribute('tabindex',canOpen?'0':'-1');
    $('final-control').disabled=state.active||!['open','lifted'].includes(state.phase);
    $('final-control').textContent=state.phase==='lifted'?'Tap to return final ㄴ':'Lift final ㄴ';
    $('slot-control').disabled=state.active||state.phase!=='lifted';
    $('open').disabled=state.active||!['closed','complete'].includes(state.phase);
    $('open').textContent=state.phase==='complete'?'Open again':'Open 난';
    $('undo').disabled=state.active||['closed','opening'].includes(state.phase);
    document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode)));
  }
  const selectedLabel=()=>['lifting','lifted','dragging','returning'].includes(state.phase)?'selected':'at rest';
  function create(){
    for(const part of NAN){
      const ground=svg('svg',{viewBox:'0 0 360 360','aria-hidden':'true'});
      const origin=svg('path',{class:'origin',d:outline(part.packed,part.type)});
      const [cx]=center(part.packed),b=bounds(part.packed);
      const contact=svg('ellipse',{class:'contact',cx,cy:b.maxY+12,rx:39,ry:6});
      ground.append(origin,contact);$('ground').append(ground);
      const wrapper=document.createElement('div');wrapper.className='piece';wrapper.dataset.part=part.id;
      const drawing=svg('svg',{viewBox:'0 0 360 360'});
      const group=svg('g',{class:'piece-group',role:part.id==='final'?'button':'img',tabindex:part.id==='final'?'0':'-1','data-part':part.id});
      const sides=[];for(let level=8;level>=1;level--){const el=svg('path',{class:'side'});group.append(el);sides.push({el,level});}
      const front=svg('path',{class:'front'}),hit=svg('path',{class:'hit'}),box=svg('rect',{class:'hit-box',width:64,height:64});
      group.append(front,hit,box);drawing.append(group);wrapper.append(drawing);$('pieces').append(wrapper);
      group.addEventListener('click',event=>{event.stopPropagation();if(Date.now()<suppressClickUntil)return;partTap(part.id);});
      group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();partTap(part.id);}});
      nodes.set(part.id,{part,wrapper,front,hit,box,sides,origin,contact,group});
    }
    const slotSvg=svg('svg',{viewBox:'0 0 360 360'});
    const slotGroup=svg('g',{id:'slot-group',class:'slot-group',role:'button',tabindex:'0','aria-label':'Place final ㄴ in its lower slot','aria-hidden':'true'});
    const slotOutline=svg('path',{id:'slot-outline',class:'slot-outline',d:outline(NAN[2].packed,'L')});
    const slotHit=svg('rect',{class:'slot-hit',x:149,y:187,width:68,height:68});
    slotGroup.append(slotOutline,slotHit);slotSvg.append(slotGroup);$('ground').append(slotSvg);
    slotGroup.addEventListener('click',event=>{event.stopPropagation();if(state.phase==='lifted')placeFinal();});
    slotGroup.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&state.phase==='lifted'){event.preventDefault();placeFinal();}});
    nodes.get('final').group.addEventListener('pointerdown',pointerDown);
  }
  function open(){
    if(!['closed','complete'].includes(state.phase)||state.active)return;
    state.phase='opening';state.open=0;state.place=0;state.lift=0;state.dragX=state.dragY=0;
    setText(false);render();$('status').textContent='Opening 난 into three recognizable pieces.';
    run({open:1},700,()=>{state.phase='open';render();$('status').textContent='Tap the lower ㄴ to lift it. The upper pieces stay anchored.';});
  }
  function lift(){
    if(state.phase!=='open'||state.active)return;
    state.phase='lifting';render();$('status').textContent='Lifting final ㄴ; the upper components stay where they are.';
    run({lift:1},300,()=>{state.phase='lifted';render();$('status').textContent='Return the final ㄴ by tapping it or its slot, or drag it near the slot.';});
  }
  function placeFinal(){
    if(!['lifted','dragging'].includes(state.phase)||state.active)return;
    if(state.phase==='dragging'){
      state.returnStartQ=clamp(1-slotDistance()/Math.hypot(12,56),0,.98);
      state.returnStartX=12+state.dragX;state.returnStartY=56+state.dragY;
      state.place=state.returnStartQ;
    }else{
      state.returnStartQ=0;state.returnStartX=12;state.returnStartY=56;state.place=0;
    }
    state.phase='returning';render();$('status').textContent='The final ㄴ approaches its slot; upper shapes adjust to make room.';
    run({place:1,dragX:0,dragY:0},650,()=>{
      state.phase='complete';state.lift=0;render();setText(true);
      $('status').textContent='You reassembled 난. The three pieces resolve into printed Korean text.';
    });
  }
  function partTap(id){
    if(state.active)return;
    if(state.phase==='closed'){open();return;}
    if(id!=='final')return;
    if(state.phase==='open')lift();else if(state.phase==='lifted')placeFinal();
  }
  function undo(){
    if(state.active)return;
    if(state.phase==='complete'){
      setText(false);state.phase='lifted';state.place=0;state.lift=1;state.dragX=state.dragY=0;
      $('status').textContent='Undo: final ㄴ is lifted again. Return it when ready.';
    }else if(state.phase==='dragging'){
      pointer=null;state.phase='lifted';state.dragX=state.dragY=0;
      $('status').textContent='Undo: the final ㄴ is lifted again.';
    }else if(state.phase==='lifted'){
      state.phase='open';state.lift=0;state.dragX=state.dragY=0;
      $('status').textContent='Undo: all three pieces are open.';
    }else if(state.phase==='open'){
      state.phase='closed';state.open=0;setText(true);
      $('status').textContent='Undo: 난 is assembled.';
    }
    render();
  }
  function reset(){
    stop();pointer=null;state.phase='closed';state.open=state.lift=state.place=state.dragX=state.dragY=0;
    setText(true);render();$('status').textContent='Reset to completed 난.';
  }
  let pointer=null,suppressClickUntil=0;
  function pointerDown(event){
    if(state.phase!=='lifted'||reduced()||state.active)return;
    if(event.pointerType==='mouse'&&event.button!==0)return;
    pointer={id:event.pointerId,x:event.clientX,y:event.clientY,moved:false};
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pointerMove(event){
    if(!pointer||pointer.id!==event.pointerId)return;
    const dx=(event.clientX-pointer.x)/scale(),dy=(event.clientY-pointer.y)/scale();
    if(Math.hypot(dx,dy)>5)pointer.moved=true;
    if(!pointer.moved)return;
    event.preventDefault();state.phase='dragging';state.dragX=clamp(dx,-125,125);state.dragY=clamp(dy,-100,45);
    render();
  }
  function pointerUp(event){
    if(!pointer||pointer.id!==event.pointerId)return;
    const moved=pointer.moved;pointer=null;
    if(!moved)return;
    suppressClickUntil=Date.now()+400;
    if(event.type!=='pointercancel'&&slotDistance()<=38){placeFinal();return;}
    $('status').textContent='The final ㄴ is outside its lower slot. Move it closer or tap to return.';
    run({dragX:0,dragY:0},220,()=>{state.phase='lifted';render();});
  }
  $('stage').addEventListener('click',event=>{if(event.target.closest?.('.piece-group,.slot-group'))return;if(['closed','complete'].includes(state.phase))open();});
  $('stage').addEventListener('keydown',event=>{if(event.target!==$('stage'))return;if((event.key==='Enter'||event.key===' ')&&['closed','complete'].includes(state.phase)){event.preventDefault();open();}});
  $('open').addEventListener('click',open);
  $('final-control').addEventListener('click',()=>state.phase==='open'?lift():placeFinal());
  $('slot-control').addEventListener('click',placeFinal);
  $('undo').addEventListener('click',undo);
  $('reset').addEventListener('click',reset);
  document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{state.mode=button.dataset.mode;render();$('status').textContent=`${button.textContent.trim()} selected at the same interaction state.`;}));
  $('reduce').addEventListener('change',event=>{stop();state.reduce=event.target.checked;if(state.phase==='dragging'){pointer=null;state.phase='lifted';state.dragX=state.dragY=0;}render();$('status').textContent=state.reduce?'Reduced motion: state changes use short fades and no depth.':'Reduced motion simulation off.';});
  matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',()=>{stop();if(state.phase==='dragging'){pointer=null;state.phase='lifted';state.dragX=state.dragY=0;}render();});
  addEventListener('resize',render);
  create();
  nodes.get('final').group.addEventListener('pointermove',pointerMove);
  nodes.get('final').group.addEventListener('pointerup',pointerUp);
  nodes.get('final').group.addEventListener('pointercancel',pointerUp);
  setText(true);render();
  document.fonts.load('400 176px "Noto KR Study"','난').then(()=>{
    const loaded=[...document.fonts].some(face=>face.family==='Noto KR Study'&&face.status==='loaded');
    if(!loaded)$('font-status').textContent='Bundled Korean font unavailable. This device may show a fallback; compare lettering only after the font loads.';
  }).catch(()=>$('font-status').textContent='Bundled Korean font failed to load. This device is showing a fallback.');
  window.__directReassembly={snapshot:()=>({...state,reduced:reduced(),slotDistance:slotDistance()}),topology:()=>NAN.map(p=>({id:p.id,packed:p.packed.map(x=>x.length),free:p.free.map(x=>x.length),na:p.na?.map(x=>x.length)}))};
})();
