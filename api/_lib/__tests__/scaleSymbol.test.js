import { describe, it, expect } from 'vitest';
import { applyScaleSymbol } from '../kernel-bridge/solveWithKernel.js';

// Thang chữ (scaleSymbol): engine tính tại a=1 rồi ghép ×a^k vào đáp theo LOẠI đại lượng.
// Regress guard cho lỗi RỚT 'a' ở mặt cầu: sphere_metric (bán kính/đường kính/toạ-độ) là ĐỘ DÀI ⇒ ×a¹.
describe('applyScaleSymbol', () => {
  it('sphere_metric là độ dài ⇒ ghép ×a (trước đây thiếu, engine rớt chữ a)', () => {
    const out = applyScaleSymbol([{ kind: 'sphere_metric', text: '25/8', approx: 3.125 }], 'a');
    expect(out[0].text).toBe('a·25/8'); // 25a/8
    const out2 = applyScaleSymbol([{ kind: 'sphere_metric', text: '3/2', approx: 1.5 }], 'a');
    expect(out2[0].text).toBe('a·3/2'); // 3a/2
  });

  it('số mũ theo loại: distance ×a¹, area ×a², volume ×a³', () => {
    const a = applyScaleSymbol([{ kind: 'distance', text: '√3/3', approx: 0.577 }], 'a');
    expect(a[0].text).toBe('a·√3/3');
    const b = applyScaleSymbol([{ kind: 'area', text: '2', approx: 2 }], 'a');
    expect(b[0].text).toBe('2a²');
    const c = applyScaleSymbol([{ kind: 'volume', text: '√2/12', approx: 0.118 }], 'a');
    expect(c[0].text).toBe('a³·√2/12');
  });

  it('KHÔNG ghép cho góc/tỉ số (bất biến theo cỡ) và cho đáp 0', () => {
    const ang = applyScaleSymbol([{ kind: 'angle', text: '60°', approx: 60 }], 'a');
    expect(ang[0].text).toBe('60°');
    const zero = applyScaleSymbol([{ kind: 'area', text: '0', approx: 0 }], 'a');
    expect(zero[0].text).toBe('0');
  });
});
