// Đo CỔNG TỪ CHỐI (abstain gate): chạy khối dịch trên bộ ca bench/abstain-set/cases.json
// và đối chiếu với nhãn expect (abstain/answer) → ra precision/recall của cổng + tỉ lệ "từ chối oan".
//
// Vì sao cần: golden 210 ca gần như không có ca phải từ chối, nên confidently-wrong thấp CHƯA tách
// được phần công của cổng affine. Bộ này lấp đúng khoảng đó.
//
// CHẠY (cần khoá LLM thật — nên dùng Vertex như các eval khác):
//   VERTEX_SA_KEY=/duong/dan/sa.json VERTEX_PROJECT=... \
//   node scripts/eval/do-abstain.mjs --provider vertex --model google/gemini-3.5-flash
// Hoặc Vilao:  VILAO_API_KEY=sk-... node scripts/eval/do-abstain.mjs --provider vilao
//
// Kết quả in ra màn hình + ghi docs/nghien-cuu/eval-runs/abstain-<tag>/report.md
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dir, '../..');

function arg(name, def = null) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : def;
}
const provider = arg('provider', 'vertex');
const model = arg('model', provider === 'vertex' ? 'google/gemini-3.5-flash' : null);
const timeoutMs = Number(arg('timeout', '25000'));
const apiKey =
  provider === 'vilao' ? process.env.VILAO_API_KEY :
  provider === 'gemini' ? process.env.GEMINI_API_KEY :
  provider === 'openai' ? process.env.OAI_API_KEY : null;

// Nạp khoá Vertex từ đường dẫn file nếu chỉ có VERTEX_SA_KEY
if (!process.env.VERTEX_SA_KEY_JSON && process.env.VERTEX_SA_KEY && fs.existsSync(process.env.VERTEX_SA_KEY)) {
  process.env.VERTEX_SA_KEY_JSON = fs.readFileSync(process.env.VERTEX_SA_KEY, 'utf8');
}

const casesFile = arg('cases', path.join(ROOT, 'bench/abstain-set/cases.json'));
const { cases } = JSON.parse(fs.readFileSync(casesFile, 'utf8'));

const { planFromProblem } = await import(path.join(ROOT, 'api/_lib/kernel-bridge/solveWithKernel.js'));

async function classify(text) {
  try {
    await planFromProblem(text, { apiKey, model, timeoutMs, provider });
    return 'answer'; // dịch ra kế hoạch (không từ chối)
  } catch (e) {
    const msg = String((e && e.message) || e);
    if (/abstain/i.test(msg)) return 'abstain';
    return 'error:' + msg.slice(0, 80);
  }
}

const rows = [];
for (const c of cases) {
  const pred = await classify(c.text);
  const predAbstain = pred === 'abstain';
  const ok = (c.expect === 'abstain') === predAbstain && !pred.startsWith('error');
  rows.push({ id: c.id, expect: c.expect, pred, ok });
  console.log(`${ok ? '✅' : (pred.startsWith('error') ? '⚠️ ' : '❌')} ${c.id.padEnd(22)} expect=${c.expect.padEnd(7)} pred=${pred}`);
}

// Ma trận nhầm lẫn (bỏ ca 'error' khỏi mẫu tính precision/recall, đếm riêng)
const shouldAbstain = rows.filter((r) => r.expect === 'abstain');
const shouldAnswer = rows.filter((r) => r.expect === 'answer');
const errors = rows.filter((r) => r.pred.startsWith('error'));
const decided = rows.filter((r) => !r.pred.startsWith('error'));

const TP = shouldAbstain.filter((r) => r.pred === 'abstain').length;               // từ chối đúng
const FN = shouldAbstain.filter((r) => r.pred === 'answer').length;                // bỏ sót (đáng từ chối mà lại trả lời)
const FP = shouldAnswer.filter((r) => r.pred === 'abstain').length;               // từ chối oan
const TN = shouldAnswer.filter((r) => r.pred === 'answer').length;                // trả lời đúng lúc

const recall = TP + FN ? (100 * TP / (TP + FN)) : 0;      // bắt được bao nhiêu % ca phải từ chối
const precision = TP + FP ? (100 * TP / (TP + FP)) : 0;   // trong các lần từ chối, bao nhiêu % là đúng
const falseAbstain = FP + TN ? (100 * FP / (FP + TN)) : 0; // tỉ lệ từ chối oan trên ca đủ dữ kiện

const tag = `abstain-${provider}${model ? '-' + model.replace(/[^\w.]/g, '_') : ''}`;
const outDir = path.join(ROOT, 'docs/nghien-cuu/eval-runs', tag);
fs.mkdirSync(outDir, { recursive: true });
const md = [
  `# Đo cổng từ chối — ${tag}`, '',
  `_Chạy ${new Date().toISOString()} · ${cases.length} ca · provider: ${provider}${model ? ' (' + model + ')' : ''}._`, '',
  '| Chỉ số | Giá trị |', '|---|---:|',
  `| Ca phải từ chối (expect=abstain) | ${shouldAbstain.length} |`,
  `| Ca đủ dữ kiện (expect=answer) | ${shouldAnswer.length} |`,
  `| Từ chối ĐÚNG (TP) | ${TP} |`,
  `| Bỏ sót — đáng từ chối mà trả lời (FN) | ${FN} |`,
  `| Từ chối OAN (FP) | ${FP} |`,
  `| Trả lời đúng lúc (TN) | ${TN} |`,
  `| Lỗi (không phân loại được) | ${errors.length} |`,
  `| **Recall cổng** (bắt được % ca phải từ chối) | **${recall.toFixed(1)}%** |`,
  `| **Precision cổng** (từ chối đúng / tổng từ chối) | **${precision.toFixed(1)}%** |`,
  `| **Tỉ lệ từ chối oan** (FP / ca đủ dữ kiện) | **${falseAbstain.toFixed(1)}%** |`,
  '', '## Từng ca', '', '| id | expect | pred | đúng? |', '|---|---|---|:--:|',
  ...rows.map((r) => `| ${r.id} | ${r.expect} | ${r.pred.startsWith('error') ? 'error' : r.pred} | ${r.ok ? '✅' : '❌'} |`),
  '', '> Nhãn expect do người soạn xác định (không lấy từ máy). Ca "error" là dịch hỏng khác (không phải',
  '> từ chối); xem lại đề hoặc khoá API. Diễn giải: recall cao = cổng ít bỏ sót ca thiếu dữ kiện;',
  '> từ-chối-oan thấp = cổng không quá tay với đề đủ dữ kiện.',
].join('\n');
fs.writeFileSync(path.join(outDir, 'report.md'), md);

console.log('\n================ TÓM TẮT CỔNG TỪ CHỐI ================');
console.log(`Recall (bắt ca phải từ chối): ${recall.toFixed(1)}%  |  Precision: ${precision.toFixed(1)}%  |  Từ chối oan: ${falseAbstain.toFixed(1)}%`);
console.log(`TP=${TP} FN=${FN} FP=${FP} TN=${TN} error=${errors.length}`);
console.log('Báo cáo: ' + path.relative(ROOT, path.join(outDir, 'report.md')));
