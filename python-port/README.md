# geo3d (bản Python) — engine hình học ký hiệu

Bản Python **dịch từ engine gốc TypeScript** (`api/_lib/kernel/`), giữ đúng 3 trụ cột và
đủ để **chạy giải bài thật**. Mục đích: dễ đọc + chạy được, để hiểu thuật toán.

## Trạng thái: ĐÃ PORT GẦN TRỌN + DIFF KHỚP ENGINE GỐC

- **210/210 unit test PASS** (9 bộ: geo3d 14 · analysis 12 · solver 10 · compute_extra 39 · build 22 ·
  analysis_helpers 26 · analysis_solids 42 · synthetic 24 · run_analysis 21).
- **Diff HÌNH HỌC với engine TS**: `geo3d.run` trên **209 ca golden** → **278/278 đáp KHỚP**,
  **209/209 cờ ok/vi-phạm KHỚP** (`golden_diff_all.py`).
- **Diff GIẢI TÍCH với engine TS**: `geo3d.analysis.run_analysis` trên **11 plan** (solve/optimize/
  integrate/optimize_multi/eval/solid_volume…) → **11/11 KHỚP** cả `ok/param/approx/text`,
  gồm dạng căn đẹp `10 - 2√7`, `165√385/196`, `4π` (`analysis_diff.py`).

Đã port: số chính xác, vector/thực thể, mọi compute (khoảng cách/góc/diện tích/thể tích/trụ-nón/
phương trình/vị trí tương đối/giao), dựng hình 2 dialect (oxyz + tổng hợp), verify, đường ống `run`,
nhánh giải tích đầy đủ (tích phân, khối tròn xoay, vessel/lát/cắt, giải & tối ưu 1 và nhiều biến,
làm đẹp số `recognize`, bộ điều phối `run_analysis`). CHƯA port: trực quan hoá 3D và phần chứng minh
quan hệ (Schwartz–Zippel, vốn cũng chưa có trong bản public TS).

## Chạy thử
```bash
cd python-port
python demo.py               # hình học: 3 bài mẫu, 3 MỨC an toàn
python demo_analysis.py      # giải tích: tích phân + khối tròn xoay
python demo_solver.py        # giải phương trình + tối ưu 1 biến
python tests/test_geo3d.py   # (và test_analysis / test_solver / test_compute_extra / test_build)

# DIFF TOÀN BỘ với engine TS (cần Node đã cài để tạo ground truth):
#   1) node golden_run_all.mjs      -> golden_all_ts.json (đáp engine TS cho 209 ca)
#   2) python golden_diff_all.py    -> so 278 truy vấn Python vs TS
```
> Windows: nếu console báo lỗi Unicode, chạy với `PYTHONIOENCODING=utf-8`.

## Ba trụ cột (bản đồ file ↔ file gốc)

| Bản Python | File gốc (TS) | Vai trò |
|---|---|---|
| `geo3d/scalar.py` | `kernel/scalar.ts` | **Số chính xác** `(num/den)·√r` + "rời trường an toàn" (trả `None` thay vì bịa) |
| `geo3d/vec3.py` | `kernel/vec3s.ts` | Vector mà mỗi thành phần là số chính xác |
| `geo3d/entities.py` | `kernel/entities.ts` | Điểm / đường / mặt / cầu |
| `geo3d/compute.py` | `kernel/compute/*.ts` + `answer.ts` | **Công thức tính** + **TỰ KIỂM** (so exact với float độc lập) |
| `geo3d/verify.py` | `kernel/verify.ts` | **Kiểm ràng buộc** đề (⊥, ∥, đồng phẳng, thuộc, khoảng cách) |
| `geo3d/solve.py` | `kernel/index.ts` + `classifyTier.js` | Chạy 1 "plan" → kiểm → tính → **gán 3 MỨC** |
| `geo3d/analysis/expr.py` | `analysis/expr.ts` | Parser biểu thức 1 biến (+ - * / ^, hàm, hằng) |
| `geo3d/analysis/quadrature.py` | `analysis/quadrature.ts` | **Tích phân** Simpson kép + tự kiểm sai số + tinh chỉnh cận |
| `geo3d/analysis/revolution.py` | `analysis/revolution.ts` | **Khối tròn xoay** quanh Ox (đĩa/vành khăn) & Oy (vỏ trụ) |
| `geo3d/analysis/solver.py` | `analysis/solver1d.ts` + `paramsolve.ts` | **Giải phương trình** (bậc hai chính xác + f(x)=target số) & **tối ưu 1 biến** |
| `geo3d/round_solids.py` | `compute/roundSolids.ts` | Trụ / nón / nón cụt / chóp cụt (thể tích, diện tích, đường sinh) |
| `geo3d/equation.py` | `compute/equation.ts` | Phương trình mặt / mặt cầu / đường |
| `geo3d/relative.py` | `compute/relative.ts` | Vị trí tương đối (cắt/song song/chéo/tiếp xúc…) |
| `geo3d/intersect.py` | `compute/intersect.ts` | Giao (đường–mặt, mặt–mặt, đường–cầu…) |
| `geo3d/constructions.py` | `constructions.ts` | Chân vuông góc, đối xứng, trực tâm, tâm ngoại tiếp (Cramer) |
| `geo3d/oxyz_input.py` | `dialects/oxyzInput.ts` | Parser toạ độ/số (hữu tỉ + căn) |
| `geo3d/entity_table.py` | `entityTable.ts` | Bảng thực thể theo tên (bắt trùng tên) |
| `geo3d/oxyz.py` | `dialects/oxyz.ts` + `resolveE.ts` | Thực thi op dựng hình (14 op oxyz) + phân giải token |
| `geo3d/run.py` | `run.ts` + `verifyE.ts` + `compute/query.ts` | **Đường ống**: plan → dựng → kiểm → tính → 3 mức |

## Nhánh giải tích — ý tưởng

- **Tích phân tự kiểm.** Tính Simpson ở lưới `n` rồi `2n`, ước lượng sai số Richardson
  `|I₂ₙ − Iₙ|/15`. Chỉ gắn `verified=True` khi sai số đủ nhỏ — chưa hội tụ thì KHÔNG khẳng định.
- **Tự tinh chỉnh cận.** LLM chỉ cần đưa cận gần đúng (kể cả số vô tỉ làm tròn); engine dò
  nghiệm giao điểm thật rồi snap cận về đó. Cận cho sẵn (không phải giao) thì GIỮ nguyên (fail-safe).
- **Bền với gán nhầm nhãn.** Thể tích lấy `|r_ngoài² − r_trong²|` theo từng điểm nên đúng
  dù đường trong/ngoài bị đổi chỗ.

## Ý tưởng cốt lõi

1. **Số chính xác, biết từ chối.** `√2 + √3` không viết gọn được → engine trả `None`, không
   nhét một số thập phân giả vờ là đáp đúng. Đáp ra `√3/3`, không phải `0.5774`.
2. **Công thức, không tra bảng.** Mọi đáp đến từ công thức toán (giữ ở dạng bình phương để
   không rời trường), `if/switch` chỉ để **định tuyến** và **canh ca đặc biệt**.
3. **Tự kiểm.** Sau khi tính dạng chính xác, engine tính lại một float **độc lập** rồi so;
   lệch quá dung sai `1e-6` → **vứt dạng exact, hạ về gần đúng**. Bắt được cả lỗi chép công thức.

## Khác biệt với bản gốc (còn lược)
- **Dialect Oxyz đã đủ** (14 op) nên chạy được 209/210 ca golden; op `edge` bỏ qua (chỉ để vẽ 3D).
- CHƯA port: dialect **tổng hợp** (`execute.ts`/planSchema zod), nhánh **giải tích nặng** ngoài
  tích phân/tròn xoay/giải-1-biến (vessel, sliceVolume, sectionCut, polyfit, tối ưu nhiều biến),
  tầng **recognize** (làm đẹp nhị thức căn), và phần **chứng minh quan hệ** (Schwartz–Zippel).
- Dùng `Fraction` thay `bigint`; công thức toán + cơ chế tự kiểm **giữ y như gốc** (đã diff 278/278).
