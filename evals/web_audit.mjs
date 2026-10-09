// Measures the web app the way a user meets it: every page at desktop and phone size.
// Writes evals/out/web/<page>-<viewport>.png and evals/out/web/report.json (accessibility, speed, layout problems).
//
//   node evals/web_audit.mjs --base http://127.0.0.1:8080 --cookie "<aroma_session value>" [--character 611]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]]] : acc), []));
const BASE = (args.base || 'http://127.0.0.1:8080').replace(/\/$/, '');
const OUT = path.resolve(args.out || path.join(here, 'out', 'web'));
const CHROME = args.chrome || '/usr/bin/google-chrome';
const axeSource = fs.readFileSync(path.join(here, 'node_modules', 'axe-core', 'axe.min.js'), 'utf8');
fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = { desktop: { width: 1280, height: 900 }, phone: { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 } };
const PAGES = [
  ['catalogo', '#/personaggi', { public: true }],
  ['scheda', `#/personaggio/${args.character || 611}`, { public: true, waitFor: '.sheet2 .s2-body' }],
  ['profilo', '#/profilo'],
  ['statistiche', '#/statistiche'],
  ['achievement', '#/achievement'],
  ['stagione', '#/stagione'],
  ['dungeon', '#/dungeon'],
  ['equipaggiamento', '#/equipaggiamento'],
  ['gilda', '#/gilda'],
  ['giochi', '#/giochi'],
];

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox', '--disable-gpu'] });
const report = { base: BASE, generated: new Date().toISOString(), pages: {} };

for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
  for (const [name, hash, opts = {}] of PAGES) {
    const page = await browser.newPage();
    await page.setViewport(viewport);
    if (args.cookie && !opts.anonymous) await page.setCookie({ name: 'aroma_session', value: args.cookie, url: BASE });
    const consoleErrors = [];
    const failed = [];
    let bytes = 0;
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    page.on('pageerror', (e) => consoleErrors.push(String(e)));
    page.on('requestfailed', (r) => failed.push(r.url()));
    page.on('response', async (r) => { try { bytes += (await r.buffer()).length; } catch { /* redirects, cached */ } });
    const t0 = Date.now();
    await page.goto(`${BASE}/${hash}`, { waitUntil: 'networkidle2', timeout: 60000 });
    if (opts.waitFor) await page.waitForSelector(opts.waitFor, { timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 600));
    const loadMs = Date.now() - t0;

    await page.addScriptTag({ content: axeSource });
    const axe = await page.evaluate(async () => {
      const r = await window.axe.run(document, { resultTypes: ['violations'] });
      return r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length, example: v.nodes[0]?.html?.slice(0, 140) }));
    });
    const layout = await page.evaluate(() => {
      const overflow = document.documentElement.scrollWidth - window.innerWidth;
      const small = [...document.querySelectorAll('button, a, input, select, summary')]
        .filter((el) => el.offsetParent !== null)
        .map((el) => ({ el, r: el.getBoundingClientRect() }))
        .filter(({ r }) => r.width > 0 && (r.height < 32 || r.width < 32))
        .slice(0, 8)
        .map(({ el, r }) => `${el.tagName.toLowerCase()} "${(el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 24)}" ${Math.round(r.width)}x${Math.round(r.height)}`);
      const noAlt = [...document.querySelectorAll('img')].filter((i) => !i.hasAttribute('alt')).length;
      const text = document.body.innerText.length;
      return { horizontalOverflowPx: Math.max(0, overflow), smallTargets: small, imagesWithoutAlt: noAlt, textLength: text, title: document.title };
    });
    await page.screenshot({ path: path.join(OUT, `${name}-${vpName}.png`), fullPage: true });
    report.pages[`${name}-${vpName}`] = { loadMs, kilobytes: Math.round(bytes / 1024), consoleErrors, failedRequests: failed.slice(0, 5), axe, layout };
    await page.close();
  }
}
await browser.close();

const summary = Object.entries(report.pages).map(([k, v]) => ({
  page: k, loadMs: v.loadMs, kb: v.kilobytes, errors: v.consoleErrors.length,
  axeSerious: v.axe.filter((a) => ['serious', 'critical'].includes(a.impact)).length, axeTotal: v.axe.length,
  overflow: v.layout.horizontalOverflowPx, smallTargets: v.layout.smallTargets.length,
}));
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
fs.writeFileSync(path.join(OUT, 'summary.json'), JSON.stringify(summary, null, 2));
console.table(summary);
