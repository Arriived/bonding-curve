const fs = require('fs');
const { chromium } = require('C:/Users/moadl/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  const page = await browser.newPage({ viewport: { width: 1024, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('file:///C:/Users/moadl/Documents/Codex/2026-10-30/referenced-chatgpt-conversation-this-is-an/work/open-launch-preview.html');
  const frame = page.frameLocator('iframe');
  const narrative = frame.locator('[data-view="narrative"]');
  await narrative.locator('[data-mint="B"]').click();
  if (!(await narrative.locator('[data-received]').innerText()).includes('ORB')) throw Error('Direct mint selection failed');
  if (!(await narrative.locator('.oc-order h3').innerText()).includes('ORBITDOG')) throw Error('Purchase heading mismatch');
  await narrative.locator('[data-action="review"]').click();
  if (!(await narrative.locator('.oc-receipt').innerText()).includes('example mint B')) throw Error('Confirmation mismatch');
  await narrative.locator('[data-action="launch"]').click();
  if (await narrative.locator('.oc-shell').isVisible()) throw Error('Launch transition failed');
  await narrative.locator('[data-action="create"]').click();
  if (!(await narrative.locator('.oc-created').innerText()).includes('Late entry')) throw Error('Creation preview failed');
  await narrative.locator('[data-action="close-launch"]').click();
  await page.screenshot({ path: 'work/open-launch-wide.png', fullPage: true });
  const targetFrame = page.frames().find(f => f !== page.mainFrame());
  await targetFrame.evaluate(() => {
    const sections = document.querySelectorAll('#open-launch-concept > section');
    sections[0].hidden = true; sections[1].hidden = false;
  });
  const coin = frame.locator('[data-view="coin"]');
  await coin.locator('[data-action="lead"]').click();
  if (!(await coin.locator('[data-received]').innerText()).includes('MDOG')) throw Error('Optional lead selection failed');
  await page.setViewportSize({ width: 390, height: 1400 });
  const overflow = await targetFrame.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw Error('Narrow layout overflows');
  await page.screenshot({ path: 'work/open-launch-narrow.png', fullPage: true });
  if (errors.length) throw Error(errors.join('\n'));
  fs.writeFileSync('outputs/c_permissionless_study/mockup_qa.json', JSON.stringify({ status:'passed',
    tests:['direct received mint','heading agrees with mint','confirmation agrees with mint','launch navigation','late-entry creation preview','optional lead selection','390px overflow','browser runtime'],
    screenshots:['work/open-launch-wide.png','work/open-launch-narrow.png'], errors }, null, 2));
  await browser.close();
  console.log('Mockup interactions and responsive checks passed');
})().catch(e => { console.error(e); process.exit(1); });
