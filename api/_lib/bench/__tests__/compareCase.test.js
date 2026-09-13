import { describe, it, expect } from 'vitest';
import { compareCase, answerText } from '../compareCase.js';

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

  // Không phải đáp nào cũng có `.text`: relative_position trả {relation},
  // intersection trả {result, point}. Trước đây hai loại truy vấn ĐÃ SHIP này
  // không thể canh hồi quy vì text luôn undefined.
  describe('đáp không phải số', () => {
    it('answerText đọc được relation và intersection', () => {
      expect(answerText({ kind: 'relative_position', relation: 'rời nhau' })).toBe('rời nhau');
      expect(answerText({
        kind: 'intersection', result: 'point',
        point: { p: { x: { approx: 1 }, y: { approx: 2 }, z: { approx: 0 } } },
      })).toBe('point (1,2,0)');
      expect(answerText(null)).toBe('');
      expect(answerText({ kind: 'gì đó' })).toBe('');
    });

    it('pass khi kỳ vọng là chuỗi và đáp khớp (bỏ qua hoa/thường, khoảng trắng)', () => {
      const g = { id: 't', plan: {}, expect: { ok: true, answers: [{ text: 'rời nhau' }] } };
      const r = { ok: true, answers: [{ kind: 'relative_position', relation: '  Rời   nhau ' }] };
      expect(compareCase(g, r).verdict).toBe('pass');
    });

    it('regress-answer khi chuỗi khác', () => {
      const g = { id: 't', plan: {}, expect: { ok: true, answers: [{ text: 'rời nhau' }] } };
      const r = { ok: true, answers: [{ kind: 'relative_position', relation: 'tiếp xúc' }] };
      expect(compareCase(g, r).verdict).toBe('regress-answer');
    });

    it('đáp rỗng KHÔNG được coi là khớp với kỳ vọng rỗng', () => {
      const g = { id: 't', plan: {}, expect: { ok: true, answers: [{ text: '' }] } };
      expect(compareCase(g, { ok: true, answers: [{ kind: 'x' }] }).verdict).toBe('regress-answer');
    });
  });

  // Translator được phép trả "tìm giao điểm" thành MỘT truy vấn `intersection`
  // (đáp "point (x,y,z)") HOẶC thành BA `point_coord` x/y/z rời. Golden viết theo
  // khuôn thứ nhất KHÔNG được đánh trượt oan khuôn thứ hai — gộp 3 toạ độ rồi so.
  describe('gộp 3 toạ độ rời thành 1 điểm', () => {
    const gPoint = { id: 't', plan: {}, expect: { ok: true, answers: [{ kind: 'intersection', text: 'point (1,2,0)' }] } };
    const threeCoords = (x, y, z) => ({
      ok: true,
      answers: [
        { kind: 'point_coord', approx: x, text: String(x) },
        { kind: 'point_coord', approx: y, text: String(y) },
        { kind: 'point_coord', approx: z, text: String(z) },
      ],
    });

    it('pass khi 3 toạ độ khớp điểm kỳ vọng', () => {
      expect(compareCase(gPoint, threeCoords(1, 2, 0)).verdict).toBe('pass');
    });

    it('regress-answer khi một toạ độ lệch', () => {
      const r = compareCase(gPoint, threeCoords(1, 2, 5)); // z sai
      expect(r.verdict).toBe('regress-answer');
      expect(r.detail).toContain('#3');
    });

    it('không gộp nhầm khi kỳ vọng KHÔNG phải điểm', () => {
      // golden mong 1 khoảng cách, engine trả 3 số → vẫn là số-lượng-đáp-khác, KHÔNG gộp.
      const g = { id: 't', plan: {}, expect: { ok: true, answers: [{ kind: 'distance', text: '√2' }] } };
      expect(compareCase(g, threeCoords(1, 2, 0)).verdict).toBe('regress-answer');
    });
  });

  // Các ca dưới đây đến từ nhánh nghiên cứu (rổ golden 210 ca có nhiều đáp "thang chữ").
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
