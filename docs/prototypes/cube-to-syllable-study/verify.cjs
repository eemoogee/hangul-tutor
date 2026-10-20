const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

const url = pathToFileURL(path.join(__dirname, 'index.html')).href;
const output = path.resolve(__dirname, '../../../.verify_out/cube-to-syllable-study');
fs.mkdirSync(output, {recursive: true});

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const errors = [];
  try {
    for (const [width, height] of [[390, 844], [320, 568]]) {
      const page = await browser.newPage({viewport: {width, height}, deviceScaleFactor: 1});
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(url);
      assert.equal(await page.locator('#rest-glyph').innerText(), '나');
      assert.equal(await page.locator('.face').count(), 6);
      assert.equal(await page.locator('.face.letter-face').count(), 2);
      assert.equal(await page.locator('#scene').getAttribute('data-open'), 'false');
      const closedDistance = await page.locator('#scene').evaluate(el => getComputedStyle(el).getPropertyValue('--d').trim());
      assert.match(closedDistance, /64/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'no horizontal overflow');
      if (width === 390) assert.equal(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight), true, 'single-screen 390×844');
      await page.screenshot({path: path.join(output, `assembled-${width}x${height}.png`), fullPage: true});

      await page.locator('#open-button').click();
      await page.waitForTimeout(700);
      assert.equal(await page.locator('#scene').getAttribute('data-open'), 'true');
      const openedDistance = await page.locator('#scene').evaluate(el => getComputedStyle(el).getPropertyValue('--d').trim());
      assert.match(openedDistance, /108/);
      assert.notEqual(await page.locator('.face').first().evaluate(el => getComputedStyle(el).transform),
        await page.locator('.face').nth(1).evaluate(el => getComputedStyle(el).transform), 'independent face orientation');
      assert.equal(await page.locator('.cube').evaluate(el => getComputedStyle(el).transformStyle), 'preserve-3d');
      await page.locator('#motion-button').click();
      assert.equal(await page.locator('.cube').evaluate(el => getComputedStyle(el).animationPlayState), 'paused');
      const pausedTransform = await page.locator('.cube').evaluate(el => getComputedStyle(el).transform);
      await page.waitForTimeout(100);
      assert.equal(await page.locator('.cube').evaluate(el => getComputedStyle(el).transform), pausedTransform, 'pause holds the current angle');
      await page.locator('#scene').focus();
      await page.keyboard.press('ArrowLeft');
      await page.keyboard.press('ArrowLeft');
      await page.keyboard.press('ArrowLeft');
      assert.equal(await page.locator('#scene').evaluate(el => el.style.getPropertyValue('--view-y')), '-45deg');
      await page.locator('#scene').evaluate(el => el.blur());
      await page.screenshot({path: path.join(output, `panels-open-${width}x${height}.png`), fullPage: true});

      await page.locator('[data-variant="bare"]').click();
      assert.equal(await page.locator('#scene').getAttribute('data-variant'), 'bare');
      assert.equal(await page.locator('.face').first().evaluate(el => getComputedStyle(el).backgroundColor), 'rgba(0, 0, 0, 0)');
      assert.equal(await page.locator('.glyph .extrusion').first().evaluate(el => getComputedStyle(el).display), 'block');
      await page.screenshot({path: path.join(output, `bare-open-${width}x${height}.png`), fullPage: true});
      const bounds = await page.locator('#scene').boundingBox();
      await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
      await page.mouse.down();
      await page.mouse.move(bounds.x + bounds.width / 2 + 40, bounds.y + bounds.height / 2);
      await page.mouse.up();
      assert.notEqual(await page.locator('#scene').evaluate(el => el.style.getPropertyValue('--view-y')), '-45deg', 'pointer turn');
      await page.locator('#reset-button').click();
      assert.equal(await page.locator('#scene').evaluate(el => el.style.getPropertyValue('--view-y')), '0deg', 'reset view');
      await page.locator('#open-button').click();
      assert.equal(await page.locator('#scene').getAttribute('data-open'), 'false');
      assert.equal(await page.locator('#open-button').getAttribute('aria-expanded'), 'false');
      await page.close();
    }

    const context = await browser.newContext({reducedMotion: 'reduce', viewport: {width: 390, height: 844}});
    const reduced = await context.newPage();
    await reduced.goto(url);
    await reduced.locator('#open-button').click();
    assert.equal(await reduced.locator('#motion-button').isDisabled(), true);
    assert.equal(await reduced.locator('#scene').getAttribute('data-playing'), 'false');
    await reduced.close();
    await context.close();
    assert.deepEqual(errors, []);
    console.log('PASS: 390×844 and 320×568, six-face depth, both variations, reassembly, keyboard, reduced motion, no page errors');
    console.log(`Screenshots: ${output}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
