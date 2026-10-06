// Quick checks on every deployment, full coverage on PRs/manual runs.
import {readFileSync, mkdirSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const config = JSON.parse(readFileSync(path.join(root, 'lighthouserc.json'))).ci;
const full = process.argv.includes('--full');
const base = process.env.SITE_TEST_URL || 'http://127.0.0.1:8876';
const urls = full ? config.collect.url.map(url => new URL(url).pathname) : ['/', '/sponsors/', '/timeline/', '/Seraphina/oct-4-hotfire/'];
const runs = full ? config.collect.numberOfRuns : 1;
const output = path.join(root, '.lighthouseci/reports');
mkdirSync(output, {recursive: true});
let failed = false;
for (const route of urls) {
  const scores = {};
  for (let run = 0; run < runs; run++) {
    const name = path.join(output, (route.replaceAll('/', '-') || 'home') + '-' + run);
    const result = spawnSync(process.execPath, [path.join(root, 'ci/node_modules/lighthouse/cli/index.js'), base + route,
      '--quiet', '--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage', '--output=json', '--output=html', '--output-path=' + name], {stdio: 'inherit'});
    if (result.status !== 0) throw new Error('Lighthouse failed for ' + route);
    const report = JSON.parse(readFileSync(name + '.report.json'));
    for (const [category, {score}] of Object.entries(report.categories)) (scores[category] ||= []).push(score);
    console.log(JSON.stringify({route, run, scores: Object.fromEntries(Object.entries(report.categories).map(([key, value]) => [key, value.score])),
      lcp: report.audits['largest-contentful-paint'].numericValue, cls: report.audits['cumulative-layout-shift'].numericValue,
      bytes: report.audits['total-byte-weight'].numericValue}));
  }
  for (const [assertion, [, rule]] of Object.entries(config.assert.assertions)) {
    const category = assertion.replace('categories:', '');
    const sorted = scores[category].sort((a, b) => a - b);
    const median = (sorted[Math.floor((sorted.length - 1) / 2)] + sorted[Math.floor(sorted.length / 2)]) / 2;
    if (median < rule.minScore) { console.error(`${route}: ${category} ${median} < ${rule.minScore}`); failed = true; }
  }
}
if (failed) process.exitCode = 1;
