// node_analysis.mjs — chạy các plan giải tích qua ENGINE TS GỐC (runAnalysis) → JSON cho Python diff.
// Chạy từ gốc repo:  node python-port/node_analysis.mjs
import { runAnalysis } from '../api/_lib/kernel-dist/index.mjs';
import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const plans = JSON.parse(readFileSync(join(root, 'python-port', 'analysis_plans.json'), 'utf8'));

const out = {};
for (const { id, plan } of plans) {
  try {
    const r = runAnalysis(plan);
    out[id] = {
      ok: r.ok ?? null,
      param: r.parameter && typeof r.parameter.value === 'number' ? r.parameter.value : null,
      approx: r.answer && typeof r.answer.approx === 'number' ? r.answer.approx : null,
      text: r.answer && typeof r.answer.text === 'string' ? r.answer.text : null,
    };
  } catch (e) {
    out[id] = { error: String(e && e.message || e) };
  }
}
writeFileSync(join(root, 'python-port', 'analysis_ts.json'), JSON.stringify(out, null, 2));
process.stdout.write(`Đã chạy ${plans.length} plan giải tích qua engine TS → analysis_ts.json\n`);
