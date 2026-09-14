// api/_lib/openaiCompat.js
// Client OpenAI-COMPATIBLE dùng chung cho EVAL — cắm bất kỳ nguồn nào theo chuẩn /chat/completions:
// DeepSeek chính hãng (https://api.deepseek.com), OpenRouter (https://openrouter.ai/api/v1), Together…
// Chữ ký khớp callVilao(sys,user,opts)->text để nối thẳng vào eval.
//
// Cấu hình qua ENV (hoặc opts):
//   OAI_BASE_URL  — gốc API, vd https://api.deepseek.com  hoặc  https://openrouter.ai/api/v1
//   OAI_API_KEY   — khoá của nguồn đó (DeepSeek/OpenRouter…). CHỈ dùng nguồn CHÍNH DANH, tái lập được;
//                   KHÔNG dùng proxy lậu/reverse-engineer (không tái lập, vi phạm ToS → hỏng uy tín bài báo).
//   OAI_MODEL     — tên model, vd deepseek-chat  hoặc  deepseek/deepseek-chat (OpenRouter)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Ghép đúng đường /chat/completions dù base có/không có '/v1'.
function chatUrl(base) {
  const b = String(base || '').replace(/\/+$/, '');
  if (/\/(v1|api\/v1)$/.test(b)) return b + '/chat/completions';
  return b + '/v1/chat/completions';
}

export function resolveOAI(options = {}) {
  const baseUrl = options.baseUrl || process.env.OAI_BASE_URL;
  const apiKey = options.apiKey || process.env.OAI_API_KEY;
  if (!baseUrl) throw new Error('Thiếu OAI_BASE_URL (vd https://api.deepseek.com hoặc https://openrouter.ai/api/v1)');
  if (!apiKey) throw new Error('Thiếu OAI_API_KEY (khoá của nguồn OpenAI-compatible)');
  return { baseUrl, apiKey };
}

/** callOpenAICompat(systemPrompt, userPrompt, options) → string. */
export async function callOpenAICompat(systemPrompt, userPrompt, options = {}) {
  const {
    maxTokens = 4096, timeoutMs = 30000, model = null, json = true, maxAttempts = 2,
    reasoningEffort = null, // 'none'|'low'|'medium'|'high' — gửi `reasoning_effort` (giới hạn thinking). null ⇒ không gửi.
  } = options;
  const { baseUrl, apiKey } = resolveOAI(options);
  const modelToUse = model || process.env.OAI_MODEL || 'deepseek-chat';
  const url = chatUrl(baseUrl);

  const messages = [];
  if (systemPrompt) messages.push({ role: 'system', content: systemPrompt });
  messages.push({ role: 'user', content: userPrompt });

  const bodyObj = { model: modelToUse, messages, max_tokens: maxTokens };
  if (json) bodyObj.response_format = { type: 'json_object' };
  if (reasoningEffort) bodyObj.reasoning_effort = String(reasoningEffort).trim();

  let attempt = 0;
  let lastErr = null;
  while (attempt < maxAttempts) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + apiKey },
        body: JSON.stringify(bodyObj),
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        if ([429, 500, 502, 503, 504].includes(res.status) && attempt < maxAttempts - 1) {
          await sleep(800 * (attempt + 1));
          attempt++;
          continue;
        }
        throw new Error(`OpenAI-compat API error: ${res.status} ${t.slice(0, 300)}`);
      }
      const data = await res.json();
      const content = data?.choices?.[0]?.message?.content;
      if (typeof content !== 'string' || content.trim() === '') {
        if (attempt < maxAttempts - 1) { await sleep(800 * (attempt + 1)); attempt++; continue; }
        throw new Error('OpenAI-compat trả về rỗng (finish=' + (data?.choices?.[0]?.finish_reason || '?') + ')');
      }
      return content;
    } catch (err) {
      clearTimeout(timer);
      lastErr = err;
      const msg = String((err && err.message) || err).toLowerCase();
      const isNet = /abort|timeout|timed out|network|fetch failed|econnreset|econnrefused/.test(msg);
      if (isNet && attempt < maxAttempts - 1) { await sleep(1000 * (attempt + 1)); attempt++; continue; }
      throw err;
    }
  }
  throw lastErr || new Error('OpenAI-compat failed after maximum retries');
}
