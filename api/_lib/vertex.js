// api/_lib/vertex.js
// Client VERTEX AI (Gemini qua Google Cloud, endpoint OpenAI-compat) cho EVAL đa mô hình.
// Auth = OAuth access-token mint từ service-account (VERTEX_SA_KEY_JSON), tự refresh — dùng lại
// api/_lib/vertexAuth.js đã có. Chữ ký khớp callVilao(sys,user,opts)->text để nối thẳng vào eval.
//
// Khác 'gemini.js' (AI Studio, key tĩnh): Vertex tính tiền qua Google Cloud → dùng ĐÚNG credit $300.
// Chạy trên MÁY người dùng (có VERTEX_SA_KEY_JSON); web/CI chặn mạng ra Google là chủ ý.

import { ensureVertexAccessToken } from './vertexAuth.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function vertexChatUrl() {
  const project = process.env.VERTEX_PROJECT || '';
  const loc = (process.env.VERTEX_LOCATION || 'global').trim();
  if (!project) throw new Error('Thiếu VERTEX_PROJECT');
  const host = loc === 'global' ? 'aiplatform.googleapis.com' : `${loc}-aiplatform.googleapis.com`;
  return `https://${host}/v1beta1/projects/${project}/locations/${loc}/endpoints/openapi/chat/completions`;
}

/**
 * Gọi Vertex một lượt. callVertex(systemPrompt, userPrompt, options) → string.
 * options: { model, maxTokens, timeoutMs, json=true, imageBase64, maxAttempts=2 }
 * Model phải có tiền tố nhà phát hành, vd 'google/gemini-2.5-flash' (đổi qua VERTEX_MODEL hoặc opts.model).
 */
export async function callVertex(systemPrompt, userPrompt, options = {}) {
  const {
    maxTokens = 4096,
    timeoutMs = 25000,
    model = null,
    json = true,
    imageBase64 = null,
    maxAttempts = 2,
  } = options;

  const modelToUse = model || process.env.VERTEX_MODEL || 'google/gemini-2.5-flash';
  const url = vertexChatUrl();

  const messages = [];
  if (systemPrompt) messages.push({ role: 'system', content: systemPrompt });
  if (imageBase64) {
    const dataUrl = String(imageBase64).startsWith('data:') ? imageBase64 : 'data:image/jpeg;base64,' + imageBase64;
    messages.push({ role: 'user', content: [{ type: 'text', text: userPrompt }, { type: 'image_url', image_url: { url: dataUrl } }] });
  } else {
    messages.push({ role: 'user', content: userPrompt });
  }

  const bodyObj = { model: modelToUse, messages, max_tokens: maxTokens };
  if (json) bodyObj.response_format = { type: 'json_object' };
  // Reasoning mặc định TẮT (nhanh/rẻ, khớp bản "-low"). Đặt VERTEX_REASONING_EFFORT=low để bật.
  const effort = (process.env.VERTEX_REASONING_EFFORT || '').trim();
  if (effort && effort !== 'default') bodyObj.reasoning_effort = effort;

  let attempt = 0;
  let lastErr = null;
  while (attempt < maxAttempts) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const token = await ensureVertexAccessToken();
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
        body: JSON.stringify(bodyObj),
        signal: ctrl.signal,
      });
      clearTimeout(timer);

      if (!res.ok) {
        const t = await res.text().catch(() => '');
        if ([429, 500, 502, 503, 504].includes(res.status) && attempt < maxAttempts - 1) {
          await sleep(600 * (attempt + 1));
          attempt++;
          continue;
        }
        throw new Error(`Vertex API error: ${res.status} ${t.slice(0, 300)}`);
      }

      const data = await res.json();
      const content = data?.choices?.[0]?.message?.content;
      if (typeof content !== 'string' || content.trim() === '') {
        if (attempt < maxAttempts - 1) { await sleep(600 * (attempt + 1)); attempt++; continue; }
        throw new Error('Vertex trả về rỗng (finish=' + (data?.choices?.[0]?.finish_reason || '?') + ')');
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
  throw lastErr || new Error('Vertex failed after maximum retries');
}
