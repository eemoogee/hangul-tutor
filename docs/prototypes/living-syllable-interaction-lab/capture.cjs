const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

const url = pathToFileURL(path.join(__dirname, 'index.html')).href;
const output = path.resolve(__dirname, '../../../.verify_out/living-syllable-interaction-lab');
fs.mkdirSync(output, {recursive: true});

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    async function captureFrames(name, steps) {
      const page = await browser.newPage({viewport: {width: 390, height: 844}, deviceScaleFactor: 1});
      await page.goto(url);
      const frames = [];
      const add = async (label, selector) => {
        const buffer = await page.locator(selector).screenshot();
        const number = String(frames.length + 1).padStart(2, '0');
        fs.writeFileSync(path.join(output, `${name}-${number}.png`), buffer);
        frames.push({label, data: buffer.toString('base64')});
      };
      await steps(page, add);
      await page.close();

      const sheet = await browser.newPage({viewport: {width: 1050, height: 760}, deviceScaleFactor: 1});
      const figures = frames.map(frame => `<figure><img src="data:image/png;base64,${frame.data}" alt="${frame.label}"><figcaption>${frame.label}</figcaption></figure>`).join('');
      await sheet.setContent(`<!doctype html><meta charset="utf-8"><style>
        body{margin:0;padding:20px;background:#132633;color:#f0f5ee;font:700 18px system-ui}
        h1{font-size:23px;margin:0 0 15px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
        figure{margin:0;padding:10px;border:1px solid #6d9094;border-radius:14px;background:#1e3643}
        img{display:block;width:100%;height:auto;border-radius:8px}figcaption{padding:10px 2px 2px}
      </style><h1>${name === 'construction' ? 'Final ㄴ makes room in 난' : '나 opens and returns'}</h1><div class="grid">${figures}</div>`);
      await sheet.screenshot({path: path.join(output, `${name}-motion-strip.png`), fullPage: true});
      await sheet.close();
    }

    await captureFrames('construction', async (page, add) => {
      await page.locator('[data-treatment="transformative"]').click();
      for (const [piece, slot] of [['initial', 'initial'], ['medial', 'medial']]) {
        await page.locator(`[data-pick="${piece}"]`).click();
        await page.locator(`[data-land="${slot}"]`).click();
        await page.waitForFunction(() => !window.__livingLab.snapshot().animating);
      }
      await page.locator('#next-task').click();
      await add('01 · na awaits final ㄴ', '#bench');
      await page.locator('[data-pick="final"]').click();
      await add('02 · lifted', '#bench');
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
      await page.mouse.move(to.x, to.y + 26, {steps: 6});
      await add('03 · nearby parts make room', '#bench');
      await page.mouse.move(to.x, to.y, {steps: 3});
      await page.mouse.up();
      await page.waitForTimeout(90);
      await add('04 · moving into place', '#bench');
      await page.waitForTimeout(135);
      await add('05 · settling', '#bench');
      await page.waitForTimeout(165);
      await page.waitForFunction(() => !window.__livingLab.snapshot().animating);
      await add('06 · nan completed', '#bench');
    });

    await captureFrames('spatial', async (page, add) => {
      await page.locator('[data-area="depth"]').click();
      await add('01 · readable flat 나', '#spatial-scene');
      await page.locator('#depth-toggle').click();
      await page.waitForTimeout(125);
      await add('02 · panes appear', '#spatial-scene');
      await page.waitForTimeout(170);
      await add('03 · depth and camera tilt', '#spatial-scene');
      await page.waitForFunction(() => !window.__livingLab.snapshot().depth.animation);
      await add('04 · fully open', '#spatial-scene');
      await page.locator('[data-spatial="solid"]').click();
      await add('05 · solid strokes', '#spatial-scene');
      await page.locator('#depth-toggle').click();
      await page.waitForFunction(() => !window.__livingLab.snapshot().depth.animation);
      await add('06 · reassembled', '#spatial-scene');
    });
    console.log(`PASS: two six-frame motion strips and individual PNG frames in ${output}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
