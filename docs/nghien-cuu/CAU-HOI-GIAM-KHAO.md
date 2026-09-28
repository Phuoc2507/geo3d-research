# Câu hỏi giám khảo → tra ở đâu trong repo

Bảng tra nhanh: mỗi câu hỏi thường gặp, câu trả lời gọn, và **chỗ trong repo** để xem chi tiết
hoặc xem code. Đường dẫn tính từ gốc repo.

---

## 1. Thuật toán/kiến trúc của đề tài là gì?
**Gọn:** Kiến trúc **Neuro‑Symbolic** ba khối: (1) LLM chỉ **DỊCH** đề tiếng Việt thành mô hình
hình học hình thức; (2) một **engine tất định** dựng hình, **TÍNH** đáp số chính xác và **TỰ KIỂM**;
(3) một **cổng từ chối** để "thà không trả còn hơn trả sai".
**Xem:** `docs/nghien-cuu/bao-cao-nghien-cuu.md` §4 (Phương pháp và kiến trúc). Tổng quan luồng: §4.1.

## 2. "Bộ tính toán" và "bộ kiểm chứng" khác nhau chỗ nào?
Ba thứ khác nhau, đừng nhầm:
- **Bộ tính toán (engine):** nhận mô hình hình học → tính đáp số chính xác (căn/π/phân số).
  Code: `api/_lib/kernel/compute/`, `api/_lib/kernel/run.ts`, số học chính xác ở `api/_lib/kernel/scalar.ts`.
- **Tự kiểm chứng (bên trong engine):** sau khi tính, engine **thử lại** đáp có thoả mọi ràng buộc
  của đề không; không thoả thì **hạ mức tin cậy**, không dám khẳng định. Code: `api/_lib/kernel/verify.ts`,
  `api/_lib/kernel/verifyE.ts`.
- **Bộ kiểm chứng hồi quy (`bench:gate`):** chạy **210 bài mẫu đã biết đáp đúng** qua engine, sai
  một bài là chặn (exit≠0). Đây là bằng chứng **tái lập**, chạy offline không tốn tiền.
  Code: `scripts/bench-gate.mjs`, `api/_lib/bench/runGate.js`, dữ liệu `bench/golden/` (210 tệp).
**Chạy thử:** `npm run bench:gate` → kỳ vọng `GATE PASS 210/210`.

## 3. Giải thích "cổng từ chối" (khi nào hệ thống từ chối trả lời)?
**Gọn:** Hệ thống từ chối theo **ba tầng**, mỗi tầng neo vào một tính chất toán học:
- **Tầng 1 — cổng ngữ nghĩa:** bộ dịch tự khước từ khi đề **thiếu dữ kiện** hoặc **ngoài danh mục**.
- **Tầng 2 — từ chối tất định ở khâu tính:** engine trả `ok:false` khi ràng buộc mâu thuẫn/suy biến.
- **Tầng 3 — tự kiểm chứng chỉ:** khi không chứng nhận được đáp là chính xác thì hạ `exact`→`approximate`,
  hiện nhãn "chưa kiểm chứng" thay vì khẳng định.
**Xem:** `docs/nghien-cuu/nang-luc-va-ranh-gioi.md` §3 (Ranh giới từ chối).
**Code:** phân mức `api/_lib/kernel-bridge/classifyTier.js`; cổng dịch/khước từ `api/_lib/kernel-bridge/solveWithKernel.js`;
bộ đề để thử cổng `bench/abstain-set/cases.json`.

## 4. Cho xem code bộ kiểm chứng.
- Cổng hồi quy: `scripts/bench-gate.mjs` → gọi `api/_lib/bench/runGate.js` (chạy engine, so đáp với golden).
- So khớp đáp (căn/π/thang chữ): `api/_lib/bench/compareCase.js`.
- Dữ liệu chuẩn: `bench/golden/` (210 ca). Tài liệu quy trình: `docs/nghien-cuu/du-lieu-benchmark.md`.
- Ví dụ kiểm hai chiều: `docs/nghien-cuu/vi-du-kiem-hai-chieu.md`.

## 5. Nhóm làm đề tài này trong bao lâu? Ngày nào làm gì?
- **Tiến trình theo ngày:** xem **lịch sử git** của repo (tab Commits). Mỗi commit có ngày giờ + mô tả.
- **Mốc sự kiện đã tổng hợp:** `docs/nghien-cuu/nhat-ky-moc-su-kien.md` (23 mốc, ngày lấy từ git).
- **Bản đầy đủ 6 mục để đối chiếu:** `docs/nghien-cuu/nhat-ky-nghien-cuu.docx`.
- Lõi nghiên cứu (engine + benchmark + cổng từ chối) làm từ **giữa tháng 7 đến giữa tháng 9/2026**.

## 6. Dữ liệu đánh giá lấy ở đâu? Có trung thực không?
- **210 ca golden** (tự soạn + capture) kèm đáp chính xác: `bench/golden/`.
- **116 câu đề thi thật** (THPT Quốc gia/Tốt nghiệp): **không đăng toàn văn** vì bản quyền — chỉ có
  **bảng nguồn** (kỳ thi–năm–mã đề) và **kết quả**. Xem `docs/nghien-cuu/du-lieu-benchmark.md`.
- Nguyên tắc: **đáp do người xác minh**, engine chỉ được *đo*; ca engine giải sai không được đưa vào golden.

## 7. Ai viết code? Có dùng AI không?
Có dùng trợ lý AI để **hiện thực mã**, dưới chỉ đạo/kiểm thử/nghiệm thu của nhóm; **quyết định thiết kế,
công thức toán, soạn & xác minh đề, diễn giải kết quả** là của nhóm. Khai báo minh bạch ở README mục
"Liêm chính & ghi công" và trong báo cáo (`docs/nghien-cuu/bao-cao-nghien-cuu.md` §6 Đạo đức & liêm chính),
kèm nhật ký câu lệnh `docs/nghien-cuu/nhat-ky-cau-lenh.docx`.

## 8. Bộ câu hỏi phỏng vấn/bảo vệ đã chuẩn bị?
Có: `docs/nghien-cuu/hoi-dap-phong-van-de-hieu.md` và `docs/nghien-cuu/phong-van-bao-ve.md`.

---

> **Lưu ý phạm vi bản công khai:** engine **chứng minh quan hệ** (kiểm mệnh đề đúng/sai bằng đa thể
> hiện ngẫu nhiên — Schwartz–Zippel) hiện đặt sau cổng `PROVE_MODE` trong bản phát triển và **sẽ bổ
> sung vào repo này sau kỳ thi**; nên nếu hỏi riêng phần đó, code chưa có trong bản công khai này.
