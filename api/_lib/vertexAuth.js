// vertexAuth.js — mint OAuth access-token cho Vertex AI TỪ khoá service-account, an toàn cho prod.
// Vertex KHÔNG dùng key tĩnh: token sống ~3600s. Ở serverless, mỗi tiến trình (kể cả warm) tự mint +
// cache ở module-scope, làm mới khi còn < 5 phút. THUẦN Node (crypto + fetch), 0 dependency — khớp phong
// cách api/_lib. KHÔNG log nội dung khoá.
//
// Nguồn khoá (ưu tiên trên xuống):
//   1. VERTEX_SA_KEY_JSON  — CHUỖI JSON đầy đủ của khoá SA (đặt ở Vercel env). Đường CHÍNH cho prod: tự refresh.
//   2. VERTEX_ACCESS_TOKEN — token tĩnh dựng sẵn (đường test cục bộ). Dùng khi không có SA JSON; KHÔNG tự refresh.
import { createSign } from 'node:crypto';

const TOKEN_URI = 'https://oauth2.googleapis.com/token';
const SCOPE = 'https://www.googleapis.com/auth/cloud-platform';

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

let _sa = null; // khoá SA đã parse (cache)
function loadSA() {
  if (_sa) return _sa;
  const raw = process.env.VERTEX_SA_KEY_JSON;
  if (!raw) return null;
  let sa;
  try { sa = JSON.parse(raw); } catch { throw new Error('VERTEX_SA_KEY_JSON không phải JSON hợp lệ'); }
  if (!sa.client_email || !sa.private_key) throw new Error('VERTEX_SA_KEY_JSON thiếu client_email/private_key');
  _sa = sa;
  return sa;
}

async function fetchAccessToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'RS256', typ: 'JWT' };
  const claim = { iss: sa.client_email, scope: SCOPE, aud: TOKEN_URI, iat: now, exp: now + 3600 };
  const signingInput = `${b64url(JSON.stringify(header))}.${b64url(JSON.stringify(claim))}`;
  const signer = createSign('RSA-SHA256');
  signer.update(signingInput);
  const jwt = `${signingInput}.${b64url(signer.sign(sa.private_key))}`;
  const res = await fetch(TOKEN_URI, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: jwt }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || !json.access_token) {
    throw new Error(`Vertex đổi token thất bại (${res.status}): ${JSON.stringify(json).slice(0, 200)}`);
  }
  return { token: json.access_token, expEpoch: now + (json.expires_in || 3600) };
}

let _cache = null;       // { token, expEpoch }
let _inflight = null;    // chống mint song song khi nhiều request cùng lúc

// Trả access-token còn hạn cho Vertex. Mint từ SA JSON (tự refresh) nếu có; nếu không, dùng VERTEX_ACCESS_TOKEN tĩnh.
export async function ensureVertexAccessToken() {
  const sa = loadSA();
  if (!sa) {
    const staticTok = process.env.VERTEX_ACCESS_TOKEN;
    if (staticTok) return staticTok;
    throw new Error('Thiếu credential Vertex: đặt VERTEX_SA_KEY_JSON (khuyến nghị) hoặc VERTEX_ACCESS_TOKEN');
  }
  const now = Math.floor(Date.now() / 1000);
  if (_cache && _cache.expEpoch - now > 300) return _cache.token;
  if (_inflight) return _inflight;      // đã có lượt mint đang chạy → chờ chung
  _inflight = (async () => {
    try { _cache = await fetchAccessToken(sa); return _cache.token; }
    finally { _inflight = null; }
  })();
  return _inflight;
}
