// golden_run.mjs — chạy ca golden qua ENGINE TS GỐC (run) và xuất JSON cho Python đối chiếu.
// Lọc: chỉ ca mà MỌI op là 'oxyz_point' (Python tái dựng được từ toạ độ) và mọi query thuộc
// nhóm Python hỗ trợ. Chạy từ gốc repo:  node python-port/golden_run.mjs
import { run } from '../api/_lib/kernel-dist/index.mjs';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const goldenDir = join(root, 'bench', 'golden');

const SUPPORTED_QUERY = (q) => {
  if (q.kind === 'distance' || q.kind === 'angle') return true;
  if (q.kind === 'area' && (q.shape === 'triangle' || q.shape === 'polygon')) return true;
  if (q.kind === 'volume' && (q.solid === 'tetrahedron' || q.solid === 'pyramid')) return true;
  if (q.kind === 'volume_ratio') return true;
  return false;
};

const out = [];
for (const file of readdirSync(goldenDir).filter((f) => f.endsWith('.json'))) {
  let data;
  try { data = JSON.parse(readFileSync(join(goldenDir, file), 'utf8')); } catch { continue; }
  const plan = data.plan;
  if (!plan || !Array.isArray(plan.ops) || !Array.isArray(plan.queries) || plan.queries.length === 0) continue;
  if (!plan.ops.every((o) => o.op === 'oxyz_point')) continue;         // chỉ ca toạ độ thuần
  if (!plan.queries.every(SUPPORTED_QUERY)) continue;                   // chỉ truy vấn Python hỗ trợ

  const points = {};
  for (const o of plan.ops) points[o.name] = o.at;

  const res = run(plan);                                                // ← ENGINE TS chạy thật
  const answers = res.answers.map((a) => a.text ?? String(a.value ?? ''));
  out.push({ id: data.id ?? file, points, queries: plan.queries, ts_answers: answers, ok: res.ok });
}

writeFileSync(join(root, 'python-port', 'golden_ts.json'), JSON.stringify(out, null, 2));
process.stdout.write(`Đã chạy ${out.length} ca golden (toạ độ thuần) qua engine TS → golden_ts.json\n`);
