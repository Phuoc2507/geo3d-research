// node_parity.mjs — tính bằng ENGINE TS GỐC (bundle kernel-dist) rồi xuất JSON để Python đối chiếu.
// Chạy từ gốc repo:  node python-port/node_parity.mjs
import {
  revolutionVolumeDisk, revolutionVolumeShellOy,
} from '../api/_lib/kernel-dist/index.mjs';

const poly = (coeffs) => ({ kind: 'poly', coeffs });
const expr = (s) => ({ kind: 'expr', expr: s });
const sqrtp = (a, b) => ({ kind: 'sqrt', a, b });

const cases = {};

// Khối tròn xoay + tích phân (π·∫r²dx hoặc 2π·∫x·h dx) — engine tự Simpson + tự kiểm sai số.
cases['Ox y=x [0,1] -> pi/3']        = revolutionVolumeDisk(poly([0, 1]), [0, 1]).value;
cases['Ox y=sqrt(x) [0,1] -> pi/2']  = revolutionVolumeDisk(sqrtp(1, 0), [0, 1]).value;
cases['Ox r=sqrt(1-x^2) [-1,1] -> 4pi/3'] = revolutionVolumeDisk(expr('sqrt(1 - x^2)'), [-1, 1]).value;
cases['Ox vanh khan sqrt(x)&x [0,1] -> pi/6'] = revolutionVolumeDisk(sqrtp(1, 0), [0, 1], poly([0, 1])).value;
cases['Oy vo tru y=x & y=x^2 [0,1] -> pi/6']  = revolutionVolumeShellOy(poly([0, 1]), [0, 1], poly([0, 0, 1])).value;

process.stdout.write(JSON.stringify(cases, null, 2));
