// golden_run_all.mjs — chạy TẤT CẢ ca golden mà mọi op ∈ {oxyz_*, edge} qua ENGINE TS GỐC (run),
// xuất JSON đầy đủ (ops + queries + đáp TS + ok/violations) cho Python đối chiếu toàn diện.
// Chạy từ gốc repo:  node python-port/golden_run_all.mjs
import { run } from '../api/_lib/kernel-dist/index.mjs';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const goldenDir = join(root, 'bench', 'golden');

const out = [];
let skipped = 0;
for (const file of readdirSync(goldenDir).filter((f) => f.endsWith('.json'))) {
  let data;
  try { data = JSON.parse(readFileSync(join(goldenDir, file), 'utf8')); } catch { continue; }
  const plan = data.plan;
  if (!plan || !Array.isArray(plan.ops) || !Array.isArray(plan.queries) || plan.queries.length === 0) { skipped++; continue; }
  // Chỉ lấy ca mà mọi op là oxyz_* hoặc 'edge' (edge chỉ để vẽ, không tạo điểm).
  const ok = plan.ops.every((o) => String(o.op).startsWith('oxyz_') || o.op === 'edge');
  if (!ok) { skipped++; continue; }

  const res = run(plan);   // ← ENGINE TS chạy thật (bỏ qua edge nếu schema cho phép; nếu run từ chối, ghi lại)
  // relative_position -> relation; intersection -> result; còn lại -> text.
  const answers = res.answers.map((a) =>
    a.kind === 'relative_position' ? a.relation
    : a.kind === 'intersection' ? a.result
    : (a.text ?? String(a.value ?? '')));
  out.push({
    id: data.id ?? file,
    ops: plan.ops,
    asserts: plan.asserts ?? [],
    queries: plan.queries,
    ts_answers: answers,
    ok: res.ok,
    violations: (res.violations ?? []).length,
    errors: (res.errors ?? []).map((e) => e.message),
  });
}

writeFileSync(join(root, 'python-port', 'golden_all_ts.json'), JSON.stringify(out, null, 2));
process.stdout.write(`Đã chạy ${out.length} ca golden qua engine TS (bỏ ${skipped}) → golden_all_ts.json\n`);
