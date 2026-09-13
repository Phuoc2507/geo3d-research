// api/_lib/kernel/dialects/oxyzInput.ts
import { type Exact, type Scalar, makeExact, fromExact, add, sub, mul, div, neg, sqrt as sqrtS, rat } from '../scalar';
import { type Vec3S, vec3s } from '../vec3s';

export type RationalInput = number | string;

// "1.5" / "-0.25" / "12" (thập phân hoặc nguyên, không dạng mũ) → Exact hữu tỷ.
function decimalToExact(s: string): Exact {
  const neg = s.startsWith('-');
  const body = neg ? s.slice(1) : s;
  if (!/^\d*\.?\d+$/.test(body) && !/^\d+\.?\d*$/.test(body)) {
    throw new Error(`Cannot parse rational from "${s}" (use "p/q" for fractions)`);
  }
  const dot = body.indexOf('.');
  if (dot === -1) {
    const v = BigInt(body);
    return makeExact(neg ? -v : v, 1n, 1);
  }
  const intPart = body.slice(0, dot) || '0';
  const fracPart = body.slice(dot + 1) || '0';
  const den = 10n ** BigInt(fracPart.length);
  const numAbs = BigInt(intPart) * den + BigInt(fracPart);
  return makeExact(neg ? -numAbs : numAbs, den, 1);
}

const INT_RE = /^[+-]?\d+$/;

// Căn đơn: "sqrt(3)", "√3", "2*sqrt(3)", "sqrt(3)/2", "2*sqrt(3)/3", "-sqrt(5)/2"
// → Exact dạng (num/den)·√radicand. Cho phép toạ độ vô tỉ (tam giác đều, góc 60°…) chính xác.
function parseSurd(raw: string): Exact | null {
  const s = raw.replace(/√\s*\(?\s*(\d+)\s*\)?/g, 'sqrt($1)').replace(/\s+/g, '');
  const m = s.match(/^([+-]?)(?:(\d+)(?:\/(\d+))?\*?)?sqrt\((\d+)\)(?:\/(\d+))?$/i);
  if (!m) return null;
  const sign = m[1] === '-' ? -1n : 1n;
  const cnum = m[2] ? BigInt(m[2]) : 1n;
  const cden = m[3] ? BigInt(m[3]) : 1n;
  const rad = Number(m[4]);
  const den = m[5] ? BigInt(m[5]) : 1n;
  return makeExact(sign * cnum, cden * den, rad); // (sign·cnum)/(cden·den) · √rad
}

export function parseRational(input: RationalInput): Exact {
  if (typeof input === 'number') {
    if (!Number.isFinite(input)) throw new Error('Rational input must be finite');
    if (Number.isInteger(input)) {
      if (!Number.isSafeInteger(input)) {
        throw new Error(`Integer ${input} exceeds the safe range; pass it as a string instead`);
      }
      return makeExact(BigInt(input), 1n, 1);
    }
    const s = input.toString();
    if (s.includes('e') || s.includes('E')) {
      throw new Error(`Number "${s}" is in exponent form; pass it as a string fraction instead`);
    }
    return decimalToExact(s);
  }
  const s = input.trim();
  if (/sqrt|√/i.test(s)) {
    const surd = parseSurd(s);
    if (!surd) throw new Error(`Cannot parse surd from "${input}" (dùng "sqrt(3)", "sqrt(3)/2", "2*sqrt(3)")`);
    return surd;
  }
  if (s.includes('/')) {
    const parts = s.split('/');
    const a = parts[0]?.trim();
    const b = parts[1]?.trim();
    if (parts.length !== 2 || !INT_RE.test(a) || !INT_RE.test(b)) {
      throw new Error(`Cannot parse rational from "${input}" (expected "p/q" with integer p, q)`);
    }
    return makeExact(BigInt(a), BigInt(b), 1); // makeExact throws on q = 0
  }
  return decimalToExact(s);
}

// ---------------------------------------------------------------------------
// BỘ ĐỌC BIỂU THỨC SỐ. Trước đây engine chỉ nhận đúng MỘT khuôn
// "[±][a[/b]][*]sqrt(n)[/c]" nên ném lỗi với những biểu thức toán hoàn toàn bình thường
// mà khối dịch sinh ra: "sqrt(3)/2 - 1/2", "2/sqrt(3)", "-1.5*sqrt(3)". Đo trên đề thi
// thật: 7/116 câu hỏng CHỈ vì cửa vào này, trong khi LỚP SỐ của engine (tổng nhiều căn,
// chia cho căn hữu tỉ hoá bằng liên hợp) thừa sức biểu diễn chúng. Nay đọc bằng bộ phân
// tích đệ quy đầy đủ:
//     biểu thức := hạng tử { (+|-) hạng tử }
//     hạng tử   := luỹ thừa { (*|/|kề nhau) luỹ thừa }
//     luỹ thừa  := đơn vị [ ^ số nguyên ]
//     đơn vị    := số | sqrt(biểu thức) | ( biểu thức ) | -đơn vị
// KHÔNG nhận tên biến (vd "h"): đó là dữ kiện chưa xác định — phải báo lỗi thật chứ
// không được đoán. Kết quả là Scalar nên giữ nguyên tính CHÍNH XÁC khi lớp số biểu diễn
// được, và tự hạ về gần đúng khi không (vd căn lồng) — đúng triết lý "thà báo gần đúng".
type Tk = { t: 'num' | 'op' | 'lp' | 'rp' | 'sqrt'; v: string };

function tokenize(src: string): Tk[] {
  const s = src.replace(/\s+/g, '').replace(/[−–—]/g, '-').replace(/×|·/g, '*').replace(/√/g, 'sqrt');
  const out: Tk[] = [];
  let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (/[0-9.]/.test(c)) {
      let n = '';
      while (i < s.length && /[0-9.]/.test(s[i])) n += s[i++];
      if ((n.match(/\./g) || []).length > 1) throw new Error(`Cannot parse number from "${n}"`);
      out.push({ t: 'num', v: n });
      continue;
    }
    if (/[a-z]/i.test(c)) {
      let w = '';
      while (i < s.length && /[a-z]/i.test(s[i])) w += s[i++];
      if (w.toLowerCase() !== 'sqrt') throw new Error(`Cannot parse "${src}": gặp tên "${w}" — biểu thức phải là số, không chứa ẩn`);
      out.push({ t: 'sqrt', v: 'sqrt' });
      continue;
    }
    if ('+-*/^'.includes(c)) { out.push({ t: 'op', v: c }); i++; continue; }
    if (c === '(') { out.push({ t: 'lp', v: c }); i++; continue; }
    if (c === ')') { out.push({ t: 'rp', v: c }); i++; continue; }
    throw new Error(`Cannot parse "${src}": ký tự không hợp lệ "${c}"`);
  }
  if (out.length === 0) throw new Error(`Cannot parse "${src}": chuỗi rỗng`);
  return out;
}

function parseTokens(tk: Tk[], src: string): Scalar {
  let i = 0;
  const peek = () => tk[i];
  const eat = (t: string, v?: string) => {
    const x = tk[i];
    if (!x || x.t !== t || (v !== undefined && x.v !== v)) throw new Error(`Cannot parse "${src}": sai cú pháp`);
    i++; return x;
  };
  const startsUnit = () => { const x = peek(); return !!x && (x.t === 'num' || x.t === 'sqrt' || x.t === 'lp'); };

  function unit(): Scalar {
    const x = peek();
    if (!x) throw new Error(`Cannot parse "${src}": thiếu toán hạng`);
    if (x.t === 'op' && x.v === '-') { i++; return neg(unit()); }
    if (x.t === 'op' && x.v === '+') { i++; return unit(); }
    if (x.t === 'num') { i++; return fromExact(decimalToExact(x.v)); }
    if (x.t === 'sqrt') { i++; eat('lp'); const inner = expr(); eat('rp'); return sqrtS(inner); }
    if (x.t === 'lp') { i++; const inner = expr(); eat('rp'); return inner; }
    throw new Error(`Cannot parse "${src}": sai cú pháp`);
  }
  function power(): Scalar {
    let base = unit();
    if (peek() && peek()!.t === 'op' && peek()!.v === '^') {
      i++;
      const e = eat('num').v;
      if (!/^\d+$/.test(e) || Number(e) > 8) throw new Error(`Cannot parse "${src}": số mũ phải là số nguyên 0..8`);
      let r = rat(1n);
      for (let k = 0; k < Number(e); k++) r = mul(r, base);
      base = r;
    }
    return base;
  }
  function term(): Scalar {
    let acc = power();
    for (;;) {
      const x = peek();
      if (x && x.t === 'op' && (x.v === '*' || x.v === '/')) {
        i++;
        acc = x.v === '*' ? mul(acc, power()) : div(acc, power());
      } else if (startsUnit()) {
        acc = mul(acc, power()); // nhân ngầm: "2sqrt(3)", "2(1+3)"
      } else return acc;
    }
  }
  function expr(): Scalar {
    let acc = term();
    for (;;) {
      const x = peek();
      if (x && x.t === 'op' && (x.v === '+' || x.v === '-')) {
        i++;
        acc = x.v === '+' ? add(acc, term()) : sub(acc, term());
      } else return acc;
    }
  }
  const out = expr();
  if (i !== tk.length) throw new Error(`Cannot parse "${src}": còn ký tự thừa`);
  return out;
}

export function parseScalar(input: RationalInput): Scalar {
  if (typeof input === 'number') return fromExact(parseRational(input));
  const s = input.trim();
  // Đường CŨ trước: giữ nguyên hành vi (và thông báo lỗi) cho các khuôn đã dùng lâu nay.
  try { return fromExact(parseRational(s)); } catch { /* rơi xuống bộ đọc biểu thức */ }
  return parseTokens(tokenize(s), s);
}

export function parseVec3S(c: [RationalInput, RationalInput, RationalInput]): Vec3S {
  return vec3s(parseScalar(c[0]), parseScalar(c[1]), parseScalar(c[2]));
}
