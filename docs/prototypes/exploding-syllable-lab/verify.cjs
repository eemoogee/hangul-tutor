const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

const PAGE = process.env.PROTOTYPE_URL || pathToFileURL(path.join(__dirname, 'index.html')).href;
const SHOTS = path.resolve(__dirname, '../../../.verify_out/exploding-syllable-shots');
fs.mkdirSync(SHOTS, {recursive:true});
const almost = (a,b,epsilon=.02) => Math.abs(a-b)<epsilon;
const state = page => page.evaluate(() => window.__explodingSyllable.snapshot());
const settle = page => page.waitForTimeout(580);

(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const errors=[];
  try {
    const page = await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1});
    page.on('pageerror',error=>errors.push(error.message));
    page.on('console',message=>{if(message.type()==='error') errors.push(message.text());});
    await page.goto(PAGE);
    assert.equal((await state(page)).syllable,'나');
    assert.equal(await page.locator('g[data-part]').count(),2);
    await page.screenshot({path:path.join(SHOTS,'na-closed-390x844.png'),fullPage:true});

    await page.locator('#primary-action').click(); await settle(page);
    assert(Object.values((await state(page)).progress).every(p=>almost(p,1)));
    assert.equal(await page.locator('#board-state').innerText(),'OPEN · LETTERS APART');
    await page.screenshot({path:path.join(SHOTS,'na-open-390x844.png'),fullPage:true});
    await page.locator('#reset-action').click(); await settle(page);
    assert(Object.values((await state(page)).progress).every(p=>almost(p,0)));

    await page.locator('[data-view="type"]').click();
    assert(Number(await page.locator('#unicode-glyph').evaluate(el=>getComputedStyle(el).opacity))>.9);
    await page.screenshot({path:path.join(SHOTS,'na-type-closed-390x844.png'),fullPage:true});
    await page.locator('#scrub').fill('50');
    assert(almost((await state(page)).progress.initial,.5));
    assert(Number(await page.locator('#unicode-glyph').evaluate(el=>getComputedStyle(el).opacity))<.1);
    await page.screenshot({path:path.join(SHOTS,'na-glyph-bridge-390x844.png'),fullPage:true});

    await page.locator('[data-syllable="노"]').click();
    assert.equal((await state(page)).syllable,'노');
    assert.equal(await page.locator('#unicode-glyph').textContent(),'노');
    await page.locator('[data-view="structure"]').click();
    await page.locator('#primary-action').click(); await settle(page);
    await page.screenshot({path:path.join(SHOTS,'no-open-390x844.png'),fullPage:true});
    assert(Object.values((await state(page)).progress).every(p=>almost(p,1)));

    await page.locator('[data-syllable="난"]').click();
    await page.locator('[data-mode="direct"]').click();
    assert.equal(await page.locator('g[data-part]').count(),3);
    const initialBefore=await page.locator('g[data-part="initial"] .stroke').getAttribute('d');
    const medialBefore=await page.locator('g[data-part="medial"] .stroke').getAttribute('d');
    await page.locator('[data-choose="final"]').click();
    await page.locator('#primary-action').click(); await settle(page);
    let snapshot=await state(page);
    assert(almost(snapshot.progress.final,1));
    assert(almost(snapshot.progress.initial,0)&&almost(snapshot.progress.medial,0));
    assert.equal(await page.locator('g[data-part="initial"] .stroke').getAttribute('d'),initialBefore);
    assert.equal(await page.locator('g[data-part="medial"] .stroke').getAttribute('d'),medialBefore);
    assert.match(await page.locator('#feedback').innerText(),/stays detached|other letters did not move/);
    await page.screenshot({path:path.join(SHOTS,'nan-final-pulled-390x844.png'),fullPage:true});
    await page.locator('#primary-action').click(); await settle(page);
    assert(almost((await state(page)).progress.final,0));

    await page.locator('[data-syllable="나"]').click();
    const point=await page.evaluate(() => {const m=document.getElementById('stage').getScreenCTM();
      const p=new DOMPoint(131,125).matrixTransform(m); return {x:p.x,y:p.y};});
    await page.mouse.move(point.x,point.y); await page.mouse.down();
    await page.mouse.move(point.x-112,point.y+10,{steps:12}); await page.mouse.up();
    snapshot=await state(page);
    assert(snapshot.progress.initial>.55,JSON.stringify(snapshot));
    assert(almost(snapshot.progress.medial,0));
    await page.waitForTimeout(100);
    assert((await state(page)).progress.initial>.55,'dragged letter must not snap back');
    await page.screenshot({path:path.join(SHOTS,'na-direct-drag-390x844.png'),fullPage:true});

    await page.locator('#reset-action').click(); await settle(page);
    await page.locator('g[data-part="medial"]').focus();
    await page.keyboard.press('Enter');
    assert.equal((await state(page)).selected,'medial');
    await page.keyboard.press('Enter'); await settle(page);
    assert(almost((await state(page)).progress.medial,1));
    assert(almost((await state(page)).progress.initial,0));

    const touch=await browser.newPage({viewport:{width:390,height:844},hasTouch:true,isMobile:true});
    touch.on('pageerror',error=>errors.push(error.message));
    await touch.goto(PAGE);
    await touch.locator('[data-mode="direct"]').tap();
    const touchPoint=await touch.evaluate(() => {const m=document.getElementById('stage').getScreenCTM();
      const p=new DOMPoint(131,125).matrixTransform(m); return {x:p.x,y:p.y};});
    await touch.touchscreen.tap(touchPoint.x,touchPoint.y);
    assert.equal((await state(touch)).selected,'initial');
    assert(almost((await state(touch)).progress.initial,0),'first tap selects without moving');
    await touch.touchscreen.tap(touchPoint.x,touchPoint.y); await settle(touch);
    assert(almost((await state(touch)).progress.initial,1),'second tap lifts the selected component');

    await page.setViewportSize({width:320,height:568});
    await page.locator('[data-syllable="난"]').click();
    const widths=await page.evaluate(() => ({page:document.documentElement.scrollWidth,viewport:innerWidth,
      bottom:document.querySelector('#reset-action').getBoundingClientRect().bottom}));
    const overflow=await page.evaluate(() => [...document.querySelectorAll('*')]
      .filter(el=>el.getBoundingClientRect().right>innerWidth+1)
      .slice(0,12).map(el=>({tag:el.tagName,class:el.className?.baseVal||el.className,
        right:Math.round(el.getBoundingClientRect().right)})));
    assert(widths.page<=widths.viewport+1,JSON.stringify({widths,overflow}));
    await page.locator('#reset-action').scrollIntoViewIfNeeded();
    await page.locator('#reset-action').click();
    await page.screenshot({path:path.join(SHOTS,'nan-closed-320x568.png'),fullPage:true});

    const reduced=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
    reduced.on('pageerror',error=>errors.push(error.message));
    await reduced.goto(PAGE);
    await reduced.locator('#primary-action').click();
    assert(Object.values((await state(reduced)).progress).every(p=>almost(p,1)));
    assert.deepEqual(errors,[]);
    console.log('PASS: 3 syllables, reversible auto separation, continuous scrub, typographic bridge, anchored direct lift, pointer drag, touch tap, keyboard control, 390×844, 320×568, reduced motion, no page errors');
    console.log(`Screenshots: ${SHOTS}`);
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
