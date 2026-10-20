const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

const url = pathToFileURL(path.join(__dirname, 'index.html')).href;
const output = path.resolve(__dirname, '../../../.verify_out/living-syllable-interaction-lab');
fs.mkdirSync(output, {recursive: true});
const state = page => page.evaluate(() => window.__livingLab.snapshot());
const settled = page => page.waitForFunction(() => !window.__livingLab.snapshot().animating);
const depthSettled = page => page.waitForFunction(() => !window.__livingLab.snapshot().depth.animation);
const shot = (page, name) => page.screenshot({path: path.join(output, name), fullPage: true});

async function placeByTap(page, part, slot) {
  if ((await state(page)).selected !== part) await page.locator(`[data-pick="${part}"]`).click();
  await page.locator(`[data-land="${slot}"]`).click();
  await settled(page);
}

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const errors = [];
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}, deviceScaleFactor: 1});
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.goto(url);
    assert.equal((await state(page)).task, 'make-na');
    assert.equal(await page.locator('#pieces .piece').count(), 3);
    assert.equal(await page.locator('#next-task').evaluate(el => el.getBoundingClientRect().bottom <= innerHeight), true, '390×844 construction controls visible');
    await shot(page, '01-start-390x844.png');
    await page.evaluate(() => { window.__initialNode = document.querySelector('.piece[data-id="initial"]'); window.__medialNode = document.querySelector('.piece[data-id="medial"]'); });

    // All three treatments run the same complete three-task sequence.
    const approachPaths = {};
    for (const treatment of ['basic', 'tactile', 'transformative']) {
      await page.locator(`[data-treatment="${treatment}"]`).click();
      await page.locator('#reset-task').click();
      assert.equal((await state(page)).task, 'make-na');
      if (treatment === 'basic') {
        await page.locator('.piece[data-id="initial"]').focus();
        await page.keyboard.press('Enter');
        assert.equal((await state(page)).selected, 'initial');
        await page.locator('[data-land="initial"]').focus();
        await page.keyboard.press('Enter');
        await settled(page);
      } else {
        await placeByTap(page, 'initial', 'initial');
      }
      assert.equal((await state(page)).placed.initial, true);
      assert.equal((await state(page)).placed.medial, false);
      assert.equal((await state(page)).complete, false);
      if (treatment === 'transformative') await shot(page, '02-incomplete-390x844.png');
      await placeByTap(page, 'medial', 'medial');
      assert.equal((await state(page)).complete, true);
      if (treatment === 'transformative') await shot(page, '03-made-na-390x844.png');
      await page.locator('#next-task').click();
      assert.equal((await state(page)).task, 'make-nan');
      assert.equal(await page.evaluate(() => document.querySelector('.piece[data-id="initial"]') === window.__initialNode && document.querySelector('.piece[data-id="medial"]') === window.__medialNode), true, 'unchanged jamo retain DOM identity');

      if (treatment === 'transformative') {
        const before = await page.locator('.piece[data-id="initial"] .stroke').getAttribute('d');
        const from = await page.locator('.piece[data-id="final"] .hit').evaluate(element => {
          const p = element.getPointAtLength(element.getTotalLength() * .55);
          const screen = p.matrixTransform(element.getScreenCTM());
          return {x: screen.x, y: screen.y};
        });
        const to = await page.locator('#bench').evaluate(element => {
          const p = element.createSVGPoint(); p.x = 186; p.y = 222;
          const screen = p.matrixTransform(element.getScreenCTM());
          return {x: screen.x, y: screen.y};
        });
        await page.mouse.move(from.x, from.y);
        await page.mouse.down();
        await page.mouse.move(to.x, to.y + 24, {steps: 5});
        assert.notEqual(await page.locator('.piece[data-id="initial"] .stroke').getAttribute('d'), before, 'upper piece makes room during approach');
        assert.equal(await page.locator('.target-zone[data-slot="final"]').evaluate(el => el.classList.contains('near')), true, 'near slot responds');
        await shot(page, '04-final-approach-390x844.png');
        await page.mouse.move(to.x, to.y, {steps: 3});
        await page.mouse.up();
        await settled(page);
      } else {
        const from = await page.locator('.piece[data-id="final"] .hit').evaluate(element => {
          const p = element.getPointAtLength(element.getTotalLength() * .55);
          const screen = p.matrixTransform(element.getScreenCTM());
          return {x: screen.x, y: screen.y};
        });
        const to = await page.locator('#bench').evaluate(element => {
          const p = element.createSVGPoint(); p.x = 186; p.y = 246;
          const screen = p.matrixTransform(element.getScreenCTM());
          return {x: screen.x, y: screen.y};
        });
        await page.mouse.move(from.x, from.y);
        await page.mouse.down();
        await page.mouse.move(to.x, to.y, {steps: 4});
        approachPaths[treatment] = await page.locator('.piece[data-id="final"] .stroke').getAttribute('d');
        await page.mouse.move(from.x, from.y);
        await page.mouse.up();
        await placeByTap(page, 'final', 'final');
      }
      assert.equal((await state(page)).complete, true);
      assert.equal((await state(page)).placed.final, true);
      if (treatment === 'transformative') await shot(page, '05-made-nan-390x844.png');
      await page.locator('#undo-action').click();
      await settled(page);
      assert.equal((await state(page)).placed.final, false, 'undo removes final');
      await placeByTap(page, 'final', 'final');
      await page.locator('#next-task').click();
      assert.equal((await state(page)).task, 'open-nan');
      await placeByTap(page, 'final', 'release');
      assert.equal((await state(page)).complete, true);
      assert.equal((await state(page)).placed.final, false);
      if (treatment === 'transformative') await shot(page, '06-separated-390x844.png');
      await page.locator('#undo-action').click();
      await settled(page);
      assert.equal((await state(page)).placed.final, true, 'undo restores 난');
      await page.locator('#back-task').click();
      await page.locator('#back-task').click();
    }
    assert.notEqual(approachPaths.basic, approachPaths.tactile, 'tactile treatment visually attracts a near piece');

    // The two spatial presentations use the same two letter-bearing objects.
    await page.locator('[data-area="depth"]').click();
    assert.equal(await page.locator('.spatial-piece').count(), 2);
    assert.equal((await state(page)).depth.progress, 0);
    await shot(page, '07-depth-rest-390x844.png');
    await page.locator('#depth-progress').fill('50');
    assert.equal((await state(page)).depth.progress, .5);
    await shot(page, '08-depth-mid-390x844.png');
    await page.locator('#depth-progress').fill('100');
    assert.equal((await state(page)).depth.progress, 1);
    assert.match(await page.locator('.spatial-piece').first().getAttribute('style'), /translate3d/);
    assert.equal(await page.evaluate(() => {
      const frame = document.querySelector('.spatial-wrap').getBoundingClientRect();
      return [...document.querySelectorAll('.spatial-piece')].every(piece => {
        const box = piece.getBoundingClientRect();
        return box.left >= frame.left - 2 && box.right <= frame.right + 2;
      });
    }), true, 'opened panes stay within phone stage');
    await shot(page, '09-depth-panes-390x844.png');
    await page.locator('[data-spatial="solid"]').click();
    assert.equal((await state(page)).depth.spatial, 'solid');
    assert.equal(await page.locator('.spatial-piece .depth-layer').count(), 24);
    await shot(page, '10-depth-solid-390x844.png');
    await page.locator('#turn-left').click();
    assert.equal((await state(page)).depth.angle, -15);
    await page.locator('#depth-toggle').click();
    await depthSettled(page);
    assert.equal((await state(page)).depth.progress, 0, 'reassembled');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

    // Short-phone reachability and the mobile tap alternative.
    const mobile = await browser.newPage({viewport: {width: 320, height: 568}, isMobile: true, hasTouch: true, deviceScaleFactor: 1});
    mobile.on('pageerror', error => errors.push(error.message));
    await mobile.goto(url);
    assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await mobile.locator('[data-pick="initial"]').tap();
    await mobile.locator('[data-land="initial"]').tap();
    await settled(mobile);
    assert.equal((await state(mobile)).placed.initial, true);
    await shot(mobile, '11-touch-incomplete-320x568.png');
    const touchPoint = await mobile.locator('.piece[data-id="medial"] .hit').evaluate(element => {
      const p = element.getPointAtLength(element.getTotalLength() * .4);
      const screen = p.matrixTransform(element.getScreenCTM());
      return {x: screen.x, y: screen.y};
    });
    await mobile.touchscreen.tap(touchPoint.x, touchPoint.y);
    assert.equal((await state(mobile)).selected, 'medial', 'direct touch lifts the jamo');
    await mobile.locator('[data-land="medial"]').tap();
    await settled(mobile);
    assert.equal((await state(mobile)).complete, true);
    await mobile.locator('[data-area="depth"]').tap();
    await mobile.locator('#depth-progress').fill('100');
    await shot(mobile, '12-depth-320x568.png');
    assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await mobile.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
    assert.equal(await mobile.evaluate(() => {
      const card = document.querySelector('.depth-card').getBoundingClientRect();
      return [...document.querySelectorAll('.depth-actions button')].every(button => {
        const box = button.getBoundingClientRect();
        return box.left >= card.left && box.right <= card.right;
      });
    }), true, 'enlarged controls stay inside card');
    await shot(mobile, '13-depth-enlarged-320x568.png');
    await mobile.locator('#depth-reset').tap({timeout: 5000});
    await mobile.close();

    const reduceContext = await browser.newContext({viewport: {width: 390, height: 844}, reducedMotion: 'reduce'});
    const reducePage = await reduceContext.newPage();
    await reducePage.goto(url);
    await placeByTap(reducePage, 'initial', 'initial');
    assert.equal((await state(reducePage)).progress.initial, 1);
    await reducePage.locator('[data-area="depth"]').click();
    await reducePage.locator('#depth-toggle').click();
    assert.equal((await state(reducePage)).depth.progress, 1);
    await reduceContext.close();
    assert.deepEqual(errors, []);
    console.log('PASS: three tactile treatments × three tasks, persistent parts, drag reflow, undo, spatial panes and solids, reversible depth, 390×844, 320×568 touch, keyboard, reduced motion, no page errors');
    console.log(`Captures: ${output}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
