const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push({ type: 'pageerror', msg: e.message, stack: e.stack }));
  page.on('console', msg => { if (msg.type() === 'error') errs.push({ type: 'console.error', msg: msg.text() }); });
  await page.goto('http://localhost:5173/login');
  await page.fill('input[type="email"]', 'libtest3@example.com');
  await page.fill('input[type="password"]', 'password123');
  await Promise.all([
    page.waitForURL(/dashboard/, { timeout: 5000 }),
    page.click('button[type="submit"]'),
  ]);
  console.log('After login URL:', page.url());
  console.log('Errors so far:', errs.length);
  await Promise.all([
    page.waitForURL(/builder/, { timeout: 5000 }),
    page.click('button:has-text("Edit")'),
  ]);
  console.log('After Edit URL:', page.url());
  await page.waitForSelector('button:has-text("Add from library")', { timeout: 10000 });
  console.log('Add from library visible');
  await page.click('button:has-text("Add from library")');
  await new Promise(r => setTimeout(r, 2000));
  console.log('=== ERRORS ===');
  console.log(JSON.stringify(errs, null, 2));
  console.log('=== BODY ===');
  console.log((await page.evaluate(() => document.body.innerText)).slice(0, 500));
  await browser.close();
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
