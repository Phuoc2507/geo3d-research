// api/_lib/gemini.js
// Client GEMINI CHÍNH HÃNG (Google Generative Language API) — dùng cho EVAL SO SÁNH ĐA MÔ HÌNH.
// Trả về TEXT (giống callVilao) để nối thẳng vào planFromProblem (khâu dịch) và baseline llm-direct.
// KHÔNG dùng ở đường sản xuất; chỉ chạy trên MÁY người dùng (có GEMINI_API_KEY từ Google AI Studio /
// Vertex, trả bằng credit $300). Web/CI có thể chặn mạng ra Google — đó là chủ ý.
//
// Vì sao viết riêng thay vì tái dùng provider trên main: nhánh nghiên cứu giữ độc lập, client này
// chỉ cần đủ cho eval (dịch đề → JSON), không kéo theo hạ tầng khác.

const GEMINI_BASE = 'https://generativelanguage.googleapis.com/v1beta';
const DEFAULT_MODEL = 'gemini-2.0-flash';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function resolveGeminiKey(options = {}, envKey = process.env.GEMINI_API_KEY) {
  const key = options.apiKey || envKey;
  if (!key) throw new Error('Gemini API key chưa đặt (opts.apiKey hoặc biến môi trường GEMINI_API_KEY)');
  return key;
}

/**
 * Gọi Gemini một lượt. Chữ ký khớp callVilao: callGemini(systemPrompt, userPrompt, options) → string.
 * options: { model, maxTokens, timeoutMs, apiKey, json=true, imageBase64, maxAttempts=2 }
 */
export async function callGemini(systemPrompt, userPrompt, options = {}) {
  const {
    maxTokens = 4096,
    timeoutMs = 25000,
    model = null,
    apiKey = null,
    json = true,          // ép responseMimeType JSON (khâu dịch đề → Plan JSON cần JSON sạch)
    imageBase64 = null,   // đưa ảnh đề vào (vision) — cho bộ "cần hình" sau này
    maxAttempts = 2,
  } = options;

  const modelToUse = model || process.env.GEMINI_MODEL || DEFAULT_MODEL;
  const key = resolveGeminiKey({ apiKey });

  const parts = [{ text: userPrompt }];
  if (imageBase64) {
    const b64 = String(imageBase64).replace(/^data:[^;]+;base64,/, '');
    parts.push({ inline_data: { mime_type: 'image/jpeg', data: b64 } });
  }

  const body = {
    contents: [{ role: 'user', parts }],
    generationConfig: { maxOutputTokens: maxTokens, temperature: 0 },
  };
  if (systemPrompt) body.systemInstruction = { parts: [{ text: systemPrompt }] };
  if (json) body.generationConfig.responseMimeType = 'application/json';

  const url = `${GEMINI_BASE}/models/${encodeURIComponent(modelToUse)}:generateContent?key=${encodeURIComponent(key)}`;

  let attempt = 0;
  let lastErr = null;
  while (attempt < maxAttempts) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      clearTimeout(timer);

      if (!res.ok) {
        const t = await res.text().catch(() => '');
        // 429 (quá tải/quota) và 5xx là lỗi TẠM → thử lại; còn lại ném thẳng.
        if ([429, 500, 502, 503, 504].includes(res.status) && attempt < maxAttempts - 1) {
          await sleep(600 * (attempt + 1));
          attempt++;
          continue;
        }
        throw new Error(`Gemini API error: ${res.status} ${t.slice(0, 300)}`);
      }

      const data = await res.json();
      const cand = data?.candidates?.[0];
      const text = (cand?.content?.parts || []).map((p) => p.text || '').join('');
      if (!text.trim()) {
        // Rỗng thường do safety block (finishReason=SAFETY) hoặc cắt token — coi như lỗi tạm, thử lại.
        if (attempt < maxAttempts - 1) {
          await sleep(600 * (attempt + 1));
          attempt++;
          continue;
        }
        throw new Error('Gemini trả về rỗng (finishReason=' + (cand?.finishReason || '?') + ')');
      }
      return text;
    } catch (err) {
      clearTimeout(timer);
      lastErr = err;
      const msg = String((err && err.message) || err).toLowerCase();
      const isNet = /abort|timeout|timed out|network|fetch failed|econnreset|econnrefused/.test(msg);
      if (isNet && attempt < maxAttempts - 1) {
        await sleep(1000 * (attempt + 1));
        attempt++;
        continue;
      }
      throw err;
    }
  }
  throw lastErr || new Error('Gemini failed after maximum retries');
}
