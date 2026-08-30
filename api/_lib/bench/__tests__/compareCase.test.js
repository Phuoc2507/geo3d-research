import { describe, it, expect } from 'vitest';
import { compareCase } from '../compareCase.js';

const golden = (over = {}) => ({
  id: 't', plan: {},
  expect: { ok: true, answers: [{ kind: 'distance', text: '√2' }, { kind: 'volume', text: '8/3' }] },
  ...over,
});

describe('compareCase', () => {
  it('pass khi ok:true và mọi đáp khớp SỐ (√2 == 1.4142…, 8/3 == 2.666…)', () => {
    const result = { ok: true, answers: [{ text: '1.4142135' }, { text: '2.6666667' }] };
    expect(compareCase(golden(), result).verdict).toBe('pass');
  });

  it('regress-status khi kỳ vọng ok:true nhưng nay ok:false', () => {
    const r = compareCase(golden(), { ok: false, answers: [] });
    expect(r.verdict).toBe('regress-status');
  });

  it('regress-status khi ok:true nhưng KHÔNG ra đáp nào', () => {
    expect(compareCase(golden(), { ok: true, answers: [] }).verdict).toBe('regress-status');
  });

  it('regress-answer khi một đáp số LỆCH', () => {
    const result = { ok: true, answers: [{ text: '√2' }, { text: '3' }] }; // 3 ≠ 8/3
    const r = compareCase(golden(), result);
    expect(r.verdict).toBe('regress-answer');
    expect(r.detail).toContain('#2');
  });

  it('regress-answer khi SỐ LƯỢNG đáp khác', () => {
    expect(compareCase(golden(), { ok: true, answers: [{ text: '√2' }] }).verdict).toBe('regress-answer');
  });

  it('error khi engine văng lỗi (__throw)', () => {
    expect(compareCase(golden(), { __throw: 'kernel-dist lỗi' }).verdict).toBe('error');
  });

  it('pass khi kỳ vọng ok:false và nay cũng ok:false', () => {
    const r = compareCase(golden({ expect: { ok: false } }), { ok: false, answers: [] });
    expect(r.verdict).toBe('pass');
  });

  it('đáp PHI-SỐ (nhãn/phương trình): so chuỗi chuẩn hoá', () => {
    const g = { id: 't', expect: { ok: true, answers: [{ text: 'chéo nhau' }] } };
    expect(compareCase(g, { ok: true, answers: [{ text: 'Chéo  nhau' }] }).verdict).toBe('pass');
    expect(compareCase(g, { ok: true, answers: [{ text: 'song song' }] }).verdict).toBe('regress-answer');
  });

  it('góc theo ĐỘ: so bằng giá trị số', () => {
    const g = { id: 't', expect: { ok: true, answers: [{ text: '60°' }] } };
    expect(compareCase(g, { ok: true, answers: [{ text: '60°' }] }).verdict).toBe('pass');
    expect(compareCase(g, { ok: true, answers: [{ text: '45°' }] }).verdict).toBe('regress-answer');
  });

  it('đáp "thang chữ" (a³·√2/12): khớp bất kể số mũ trên/^ và dấu nhân', () => {
    const g = { id: 't', expect: { ok: true, answers: [{ text: 'a^3·√2/12' }] } };
    expect(compareCase(g, { ok: true, answers: [{ text: 'a³·√2/12' }] }).verdict).toBe('pass');
    expect(compareCase(g, { ok: true, answers: [{ text: 'a³√2/12' }] }).verdict).toBe('pass'); // engine bỏ dấu ·
    const g2 = { id: 't', expect: { ok: true, answers: [{ text: 'a√3' }] } };
    expect(compareCase(g2, { ok: true, answers: [{ text: 'a·√3' }] }).verdict).toBe('pass');
    expect(compareCase(g2, { ok: true, answers: [{ text: 'a·√2' }] }).verdict).toBe('regress-answer'); // vẫn phân biệt √3≠√2
  });

  it('đáp ký hiệu: HIỂU phép nhân đổi chỗ (28πa²/3 == a²·28π/3) mà không khớp sai', () => {
    const g = { id: 't', expect: { ok: true, answers: [{ text: '28πa²/3' }] } };
    expect(compareCase(g, { ok: true, answers: [{ text: 'a²·28π/3' }] }).verdict).toBe('pass');
    const g2 = { id: 't', expect: { ok: true, answers: [{ text: 'a/2' }] } };
    expect(compareCase(g2, { ok: true, answers: [{ text: 'a·1/2' }] }).verdict).toBe('pass');
    // KHÔNG được khớp sai: khác mẫu, hoặc thiếu thừa số a
    const g3 = { id: 't', expect: { ok: true, answers: [{ text: 'a√5/3' }] } };
    expect(compareCase(g3, { ok: true, answers: [{ text: 'a√5/5' }] }).verdict).toBe('regress-answer');
    const g4 = { id: 't', expect: { ok: true, answers: [{ text: '25a/8' }] } };
    expect(compareCase(g4, { ok: true, answers: [{ text: '25/8' }] }).verdict).toBe('regress-answer');
  });
});
