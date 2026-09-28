# Mốc sự kiện THẬT để chép tay vào Sổ nhật ký nghiên cứu (Phụ lục 2)

> **Cách dùng.** Đây là bản NHẮC mốc — không phải cuốn sổ nộp. Theo Phụ lục 2 (Kế hoạch
> 204/KH-NTN ngày 17/7/2026): sổ phải **viết tay bằng bút bi xanh/đen**, không xé trang, không
> tẩy xoá, **ngày nào ghi ngày đó**, giữ cả lỗi sai và thử nghiệm thất bại. Em chép **bằng lời của
> mình**, mỗi mốc = 1–2 trang theo khung 6 mục (Mục tiêu / Dụng cụ / Tiến trình & hiện tượng /
> Kết quả & số liệu thô / Rút kinh nghiệm & lỗi sai / Kế hoạch tiếp theo), ký tên.
>
> **Nguồn ngày & số.** Ngày lấy từ **dấu thời gian commit** trong git (đã quy về giờ Việt Nam);
> số liệu chép **nguyên văn từ nội dung commit / bench đã chạy**. Ô ⟦…⟧ là việc **không có trong
> git** (giải tay, thảo luận, đọc tài liệu) — em điền theo trí nhớ/lịch thật, **không bịa**.
>
> **Khai báo AI (Phụ lục 1).** Chỗ ghi *(AI hỗ trợ code)* là phần mã do trợ lý AI viết dưới chỉ đạo
> và kiểm thử của nhóm — khai đúng như vậy kèm nhật ký câu lệnh (`nhat-ky-cau-lenh.docx`).
> Suy nghĩ, quyết định, tự giải đề, đối chiếu là của các em. Phần geo3d (ứng dụng 3D) là của
> cộng tác viên (anh Nguyễn Hữu Phước); nhóm nhận **engine + cổng từ chối** (báo cáo v10, D.10).

---

## A. Bảng tổng quan 23 mốc (để nhìn toàn cảnh)

| # | Ngày (giờ VN) | Mốc | Số liệu chốt | Bằng chứng |
|---|---|---|---|---|
| 1 | ⟦đầu 8/2026⟧ | Ý tưởng & thiết kế: LLM chỉ DỊCH → engine tất định TÍNH & TỰ KIỂM | Sơ đồ 3 khối; GT1–GT3 | ⟦sơ đồ vẽ tay⟧ |
| 2 | 02–03/8 | Dựng engine ký hiệu (số học căn/π), chứng chỉ tự kiểm, cổng affine | Đáp dạng căn đúng; test bắt đầu xanh | commit 02–03/8 |
| 3 | 03/8 → 21/8 | Benchmark golden + kiểm HAI CHIỀU; tách train/test seed 42 | 210 ca / 279 đáp; replay 210/210; 145 train / 65 test; 1.086 test | commit 21/8 15:xx |
| 4 | 29/8 | Kiểm hai chiều BẮT LỖI "rớt chữ a" ở mặt cầu | 25/8 → 25a/8; replay vẫn 210/210 | commit 29/8 (sphere_metric ×a¹) |
| 5 | 02–04/8 | Ứng dụng web 3D (cộng tác viên) dùng để nhập đề & đối chiếu | App chạy thật | — |
| 6 | 29/8 | Eval end-to-end golden (Vertex 2.5/3.5-flash) + lớp chuẩn hoá plan | TEST-65: sai-tự-tin 1,5–6,2% vs 23,1–29,2% (số BAN ĐẦU, xem mốc 14); chuẩn hoá 71,0→78,6% / 81,4→83,3% | commit 29/8 |
| 7 | 26/8 & 30/8 | Tab /giai-de + sửa lỗi khoá localStorage đụng nhau | 146/146 câu có khoá riêng | commit 26/8, 30/8 |
| 8 | 30/8 | Lọc bộ đề thật còn 116 câu (validator off-scope/trùng) | 116 câu | commit 30/8 |
| 9 | ⟦…/8⟧ | Các em TỰ GIẢI 116 câu làm đáp chuẩn | 115/116 khớp đối chiếu chéo | ⟦ảnh lời giải tay⟧ |
| 10 | 30/8 | Thí nghiệm "ngoài sân nhà" 116 câu, temperature 0 | Hệ 72,4% / precision 94,4% / sai-tự-tin 4,3% / từ chối 23,3% (số BAN ĐẦU) | eval 30/8 |
| 11 | 30/8 | Sửa engine + vòng lặp sửa lỗi kiểu AlphaGeometry | Vòng lặp: 81,0% nhưng sai-tự-tin 10,3% (đánh đổi an toàn↔phủ) | commit 30/8 |
| 12 | 30/8 | Đối chiếu 2 bộ đáp; SỬA câu 9 | 22/46 lệch → 21/22 ủng hộ bộ 1; câu 9: 8 → 12√3 (6 lời giải độc lập) | eval 30/8 |
| 13 | 01/9 (22:28) | Lớp số TỔNG NHIỀU CĂN (√2+√3); đo riêng cổng từ chối | 15 test mới; 1.124 test; cổng bắt 12/12, oan 0/8 | commit 01/9 |
| 14 | 01–02/9 | Phát hiện BỘ CHẤM THIÊN VỊ → bộ chấm công bằng, chấm lại | Đối chứng 33,8% → 3,1% sai-tự-tin (cùng tập); đo lại 116: hệ 76,7% (4,3%), hệ+sửa 81,9% (1,7%), LLM 98,3% (1,7%) | commit 01/9 00:57, 02/9 |
| 15 | 29–30/8, 02/9 | Viết báo cáo A–E ≤15 trang; viết lại kết quả sau khi đo lại | bỏ luận điểm "an toàn hơn 4–5 lần" | commit 02/9 12:04, 15:31 |
| 16 | 03/9 (14:34–23:55) | Truy 27 câu hỏng → chụp bộ kế hoạch → 3 đợt sửa engine đo OFFLINE | 76,7% → 83,6% → 87,1% → **90,5%**; sai-tự-tin giữ 4,3%; precision 95,5% | commit 03/9 (5 commit) |
| 17 | 08/9 (17:20–22:54) | Báo cáo v10 mục C.6 + khai báo hợp tác; tích hợp geo3d: 4 sự cố hạ tầng thật | 1.156/1.156 test | commit 08/9 (8 commit) |
| 18 | 09/9 (18:55–23:09) | Điền thông tin nhóm v10; chốt kiểm **"xẻ khối"** | sai-tự-tin 4,3% → **2,6%**, precision 95,5% → **97,2%**; 1.157 test | commit 09/9 |
| 19 | 09/9 23:59 → 10/9 11:04 | Engine **chứng minh quan hệ** (prove + Schwartz–Zippel) + nối app (draft) | bench 21 mệnh đề: **14/14 đúng, 7/7 sai bị bắt, 0 đóng dấu sai**; 1.201 → 1.214 test | commit 09–10/9 |
| 20 | 10/9 (11:04; PR 15:46, 15:58) | Quyết định vòng trường: trang **/research** demo kín cho hội đồng | 1.218 test; test live #1: **HTTP 504** khi vẽ → sửa streaming | PR #83, #84 |
| 21 | 10/9 tối (20:53–22:20) | Test live vòng 2 với 10 đề mẫu 3 Mức; 6 bản vá theo lỗi quan sát | 504 / hình lỗi / luôn Mức 3 / "Unexpected token 'A'" → đều truy ra nguyên nhân | PR #85, #87–#92 |
| 22 | 11/9 | Đọc Kế hoạch 204/KH-NTN; chạy lại prove-bench xác nhận | 14/14, 7/7, 0 abstain; hạn nộp **15/9**, phỏng vấn **26/9**, cấp TP **05/10** | bench 11/9 |
| 23 | 12/9 | Đợt làm song song 12 tác vụ AI hỗ trợ (engine, tài liệu, bảo mật, port lên main) — nhóm chỉ đạo & gộp | test 1.218 → **1.498**; corpus chứng minh 21 → **144** (85/85 · 59/59 · 0); đề thật 105 → **106** đúng (91,4%); phát hiện lỗi hiển thị proof; gỡ 6 khoá lộ; hội đồng mô phỏng ≈65/100 | commit 12/9 (nhánh nghiên cứu + `claude/port-engine-len-main`) |

> Mốc 1–15 đã có bản đầy đủ 6 mục trong `nhat-ky-nghien-cuu.docx` (sinh bởi `scripts/gen-nhat-ky.mjs`).
> Dưới đây là bản đầy đủ cho **mốc 16–23** (mới, từ 3/9 đến 12/9).

---

## B. Mốc 16–23 — bản đầy đủ theo khung Phụ lục 2

### MỐC 16 — 03/9/2026 (14:34 → 23:55) — Truy lỗi trên đề thật, chụp bộ kế hoạch, ba đợt sửa engine đo offline

**GIAI ĐOẠN:** Phân tích số liệu / Lập trình. **THỜI GIAN:** ⟦…⟧ (git: 14:34–23:55).

**1. Mục tiêu.** Trả lời câu hỏi "27 câu hệ sai/từ chối trên đề thật là do engine tính sai hay do
mối nối?" — và sửa mà **không** làm tăng sai-tự-tin.

**2. Dụng cụ.** Bộ đề thật 116 câu (đáp do các em giải); engine; script `capture-plans.mjs` /
`replay-plans.mjs` *(AI hỗ trợ code)*; Gemini 3.5-flash qua Vertex, temperature 0 (chỉ gọi 116 lượt
đúng một lần để chụp kế hoạch).

**3. Tiến trình & hiện tượng.**
- Chạy lại **từng câu** hỏng, đọc đúng lý do máy báo (không suy đoán). Kết quả: **không câu nào
  engine tính sai số** — tất cả nằm ở mối nối: (1) bộ đọc số quá hẹp (7/27 câu, ví dụ
  `sqrt(3)/2 - 1/2`, `2/sqrt(3)` bị ném lỗi dù lớp số biểu diễn được); (2) thiếu phép GỘP (4/5 câu
  SAI); (3) tham số đã giải không thay được vào truy vấn (`Cannot parse h`); (4) dung sai assert
  1e-6 mâu thuẫn với residual bộ giải 1e-4 (hình đúng vẫn báo vi phạm: 3,000004 vs 3).
- **Chụp bộ kế hoạch một lần** rồi cho chạy qua engine cũ và mới → tách công của bản sửa khỏi
  biến thiên của mô hình. Phát hiện: **26/116 câu đổi kết cục giữa hai lượt gọi dù temperature 0**
  ⇒ mỗi lượt có sai số ±3 câu; chênh lệch nhỏ hơn thế không kết luận được.
- Ba đợt sửa, mỗi đợt đo lại offline (0 lượt API), chạy `bench:gate` + toàn bộ test sau mỗi đợt.
- Chạy lại đối chứng "LLM giải thẳng" lần 2 để đo độ phân tán của chính đối chứng.

**4. Kết quả & số liệu thô (116 câu đề thật, cùng bộ kế hoạch).**

| Cấu hình | Đúng | Sai tự tin | Từ chối | Precision |
|---|---|---|---|---|
| A. engine cũ + kế hoạch cũ (số đã báo) | 89 (76,7%) | 5 | 22 | — |
| B. engine cũ + kế hoạch mới | 86 (74,1%) | 7 | 23 | — |
| C. engine mới (đợt 1: 4 nút thắt) | 97 (83,6%) | 5 (4,3%) | 14 | 95,1% |
| D. đợt 2: 4 sửa nhánh giải tích | 101 (87,1%) | 5 (4,3%) | 10 (8,6%) | 95,3% |
| E. đợt 3: mở rộng lược đồ (lăng trụ, vế phải tính được, khối ghép) | **105 (90,5%)** | 5 (4,3%) | 6 (5,2%) | **95,5%** |

- B→C tất định: 4 câu SAI→ĐÚNG (mất thang chữ), 7 câu TỪ CHỐI→ĐÚNG, **và 2 câu TỪ CHỐI→SAI
  (#26, #48: mô hình xẻ khối thiếu mảnh)** — ghi nhận cả mặt trái.
- Đợt 3: +3 câu là công của lược đồ, **+1 câu (#90) do lượt chụp lại may hơn** — không nhận vơ.
- Đối chứng lượt 1: 114 đúng (98,3%), 2 sai; lượt 2: 111 (95,7%), 5 sai; giống kết cục 113/116.
  Ba câu đổi đều đúng→sai (#4 6√2→8, #9 12√3→90, #26 27√3→21√3) ⇒ đối chứng phải đọc là
  **95,7–98,3%**, không phải một số.
- Kiểm định McNemar ghép cặp (báo cáo Bảng 3): an toàn **không phân biệt được** (p = 0,375 và
  1,000); độ phủ vẫn nghiêng về đối chứng nhưng cặp lệch co từ 19/0 xuống 9/0 (p = 0,0039).
- Test: 1.152 → **1.156** xanh; gate 210/210; tsc sạch.

**5. Rút kinh nghiệm & lỗi sai.**
- Phải **chụp kế hoạch** rồi mới sửa engine, nếu không mọi "cải thiện" đều lẫn với may rủi của
  mô hình (±3 câu/lượt).
- Kết luận Giả thuyết 3 phải sửa: nút thắt **không hẳn ở khâu dịch** mà ở **lược đồ trao đổi**
  giữa hai khối (lược đồ hẹp hơn đề).
- #114 (hợp của 4 khối tròn xoay) chưa làm được — cần phép hợp N khối.

**6. Kế hoạch tiếp theo.** Đưa số mới vào bản báo cáo hội đồng; xử lý lỗi "xẻ khối thiếu mảnh".

---

### MỐC 17 — 08/9/2026 (17:20 → 22:54) — Báo cáo v10 mục C.6 + tích hợp geo3d, gặp 4 sự cố hạ tầng thật

**GIAI ĐOẠN:** Viết báo cáo / Triển khai. **THỜI GIAN:** ⟦…⟧ (git: 17:20–22:54).

**1. Mục tiêu.** (a) Làm rõ trong báo cáo phần **nhóm làm** (engine + cổng từ chối) và phần
**cộng tác viên** (app geo3d); (b) đưa cổng từ chối vào app chạy thật trên Vercel.

**2. Dụng cụ.** Word (báo cáo v10); Vercel (gói Hobby); app geo3d; *(AI hỗ trợ code)*.

**3. Tiến trình & hiện tượng.**
- Thêm mục **C.6** "đưa cổng từ chối vào geo3d": engine trả phán quyết 3 mức → server gắn → UI
  hiện nhãn; nói đúng giới hạn: **cổng chứng nhận đáp SỐ, không chứng nhận hình 3D**; Mức 3 nghĩa
  là "chưa xác nhận", không phải "hình sai". D.10 khai báo hợp tác ngoài nhóm theo Thông tư 06/2024.
- Chọn phương án A: nhóm **không nhận app**, chỉ nhận bộ tính toán; bỏ "ứng dụng web" khỏi
  phần AI nhóm yêu cầu; bỏ "ứng dụng ba chiều" khỏi việc Học sinh 2.
- Thử công tắc Vertex AI ⇒ **deploy Error** — nguyên nhân: glob `api/**/*.js` khiến thư mục
  `_lib` bị coi là function, và thêm 1 endpoint thành **function thứ 13 vượt trần 12 của gói
  Hobby**. Sửa: bỏ glob, gộp endpoint, đặt `maxDuration 60` theo từng file.
- Lỗi **401 INVALID_API_KEY** dù khoá đúng ⇒ do khoá dán vào env dính khoảng trắng/xuống dòng
  ⇒ `.trim()`.
- Lỗi **403 "please subscribe to model gemini-3.1-flash-lite"** ⇒ app đòi model mà khoá không
  đăng ký ⇒ gộp chọn model về **một biến môi trường** `VILAO_MODEL`.
- Theo yêu cầu cộng tác viên: gỡ Vertex khỏi đường production, quay về thuần Vilao.
- Crash `Cannot create property '_systemPromptUsed' on string` khi mô hình trả chuỗi thay vì JSON
  ⇒ thêm chốt kiểm kiểu dữ liệu ở cả hai nhánh vẽ.

**4. Kết quả & số liệu thô.** 1.156/1.156 test qua sau mỗi bước; số function top-level = 12
(không vượt trần).

**5. Rút kinh nghiệm & lỗi sai.** Lỗi "hạ tầng" (trần function, khoảng trắng trong khoá, model
không đăng ký) tốn thời gian ngang lỗi thuật toán — phải ghi vào nhật ký như thử nghiệm thất bại
thật. Mỗi lần đổi nhà cung cấp phải giữ đường cũ nguyên vẹn và có công tắc lùi.

**6. Kế hoạch tiếp theo.** Điền thông tin nhóm; xử lý lỗi xẻ khối (#26/#48).

---

### MỐC 18 — 09/9/2026 (18:55 → 23:09) — Điền thông tin nhóm; chốt kiểm "xẻ khối" chặn đáp sai mang dấu kiểm

**GIAI ĐOẠN:** Lập trình / Phân tích số liệu. **THỜI GIAN:** ⟦…⟧ (git: 18:55–23:09).

**1. Mục tiêu.** Chặn loại lỗi **nguy hiểm nhất**: engine cộng đúng từng mảnh nhưng mô hình xẻ
khối **thiếu** mảnh ⇒ tổng SAI mà vẫn "đã kiểm".

**2. Dụng cụ.** Engine; bộ kế hoạch v2 đã chụp (đo offline, 0 API); *(AI hỗ trợ code)*.

**3. Tiến trình & hiện tượng.**
- Báo cáo v10: điền Nguyễn Bảo Thy (nhóm trưởng), Vũ Tuấn Anh; lớp 12A1; GVHD Lê Văn Thiện;
  địa điểm THPT Ngô Thời Nhiệm; cộng tác viên Nguyễn Hữu Phước; C.6 đã được cộng tác viên xác nhận.
- Viết `decompCoverage`: lấy mẫu **tất định (PRNG có hạt)** trong bao lồi các đỉnh, đo tỉ lệ điểm
  được các mảnh phủ; **dưới 95% ⇒ phần rã có lỗ ⇒ từ chối chứng nhận** thay vì trả đáp sai.
- Hiệu chỉnh bằng khối lập phương: lấp kín = 1,00; thiếu 1/6 = 0,86; câu #26 = 0,76.
- Chỉ áp cho tứ diện/chóp (trụ/cầu/lăng trụ, combine lồng ⇒ bỏ qua để không chặn nhầm).

**4. Kết quả & số liệu thô (116 câu, replay v2, 0 API).**
- Sai tự tin **4,3% → 2,6%**; precision **95,5% → 97,2%**; đúng vẫn 105 (90,5%).
- #26/#48 chuyển **sai → từ chối**; **không câu đúng nào bị chặn nhầm**.
- #61 là lỗi khác (mô hình dựng chóp cụt) — ngoài phạm vi chốt, ghi rõ.
- Báo cáo v10: Bảng 3 dòng "đã mở rộng" → 105 đúng / 3 sai / 8 từ chối; McNemar p = 1,000 và
  0,688 (an toàn vẫn không phân biệt được với đối chứng — nói thẳng).
- gate 210/210; **1.157** test xanh.

**5. Rút kinh nghiệm.** Một chốt kiểm tốt phải được **hiệu chỉnh trên ca biết trước** (lập phương
1,00 / 0,86) trước khi tin số trên đề thật. Cải thiện 4,3→2,6% chỉ là 2 câu — ở n=116 không có ý
nghĩa thống kê, báo cáo phải nói đúng mức.

**6. Kế hoạch tiếp theo.** Giải quyết việc bài **chứng minh** luôn ra "chưa kiểm" khi giám khảo test.

---

### MỐC 19 — đêm 09/9 → 10/9/2026 (23:59 → 00:11, rồi 10:31 → 11:04) — Engine CHỨNG MINH QUAN HỆ

**GIAI ĐOẠN:** Thiết kế / Lập trình / Kiểm thử. **THỜI GIAN:** ⟦…⟧ (git: 23:59–00:11; 10:31–11:04).

**1. Mục tiêu.** Engine cũ chỉ chứng thực **đại lượng số**; bài "chứng minh SA ⊥ (ABCD)" không có
đáp số nên luôn Mức 3. Mở rộng sang **quan hệ hình học** mà vẫn giữ "chính xác hoặc từ chối".

**2. Dụng cụ.** TypeScript; lớp số Exact/ExactSum; bộ 21 mệnh đề SGK (`bench/prove-corpus.mjs`);
*(AI hỗ trợ code)*.

**3. Tiến trình & hiện tượng.**
- Tầng 1 `relations.ts`: quyết định ⊥, ∥, thẳng hàng, đồng phẳng, thuộc, trung điểm, bằng, tỉ số
  bằng **số học chính xác**; cờ `certified` chỉ bật khi không dùng float; toạ độ chỉ-float ⇒ từ chối.
- Tầng 2 truy vấn `prove`: mệnh đề sai ⇒ trả "Sai" có phản ví dụ (không phải lỗi); chỉ khi không
  quyết định được chính xác mới từ chối. Song song kiểm thêm "phân biệt" (không lẫn trùng/chứa).
- Tầng 3 `proveGeneral`: hình khai theo **tham số**; thay **K = 16 bộ số hữu tỷ ngẫu nhiên tất
  định**; đúng ở cả 16 ⇒ đồng nhất thức (bổ đề Schwartz–Zippel, xác suất sai ≤ (bậc/|miền|)^K);
  một thể hiện "Sai" ⇒ phản ví dụ; không đủ thể hiện ⇒ từ chối.
- **Lỗi gặp phải:** bộ lấy mẫu tham số lấy rộng rồi loại ⇒ với 12 tham số (tứ diện tổng quát) tỉ lệ
  chấp nhận sụp về ~0 ⇒ chỉ dựng được **1 thể hiện ⇒ từ chối oan**. Sửa: lấy mẫu **trong** dải
  [min,max] ⇒ đủ 16 thể hiện.
- Nối app (draft, chỉ kích hoạt khi plan mang `mode:"prove"`): validate → proveGeneral → dựng hình
  đại diện → tier; true/false ⇒ Mức 1, abstain ⇒ Mức 3 với lý do trung thực.

**4. Kết quả & số liệu thô.**
- Bench 21 mệnh đề trên họ hình tổng quát (tứ diện / hộp chữ nhật / chóp tứ giác đều):
  **14/14 định lý đúng được chứng nhận (16 thể hiện mỗi định lý)**, **7/7 mệnh đề sai bị bắt kèm
  phản ví dụ**, **0 từ chối**, **0 lần đóng dấu sai**.
- Bắt được cả "đúng nhờ ăn may": |SA| = |AB| chỉ khi h = a ⇒ báo **sai tổng quát**.
- Test: +44 (relations + prove) ⇒ 1.201; +9 (proveGeneral) ; nối app +4 ⇒ **1.214** xanh; tsc sạch.

**5. Rút kinh nghiệm & giới hạn (phải nói với hội đồng).**
- Nhân lõi đúng, nhưng tính đúng ở tầng ứng dụng **phụ thuộc bước dịch tham số hoá**: nếu LLM
  siết dư giả thiết (đề "hình bình hành" dịch thành "hình vuông") thì có thể chứng nhận nhầm.
  Giảm thiểu: danh mục cấu hình chuẩn + kiểm giả thiết mỗi thể hiện + nghi ngờ thì từ chối.
- Chỉ tập mệnh đề quyết định được; chứng minh tổng hợp ngoài tập **vẫn từ chối**.
- Bench này **không phải đề thật**, không dùng làm số so-với-đối-chứng.

**6. Kế hoạch tiếp theo.** Chuẩn bị cho vòng trường: hội đồng cần **xem và test được** demo.

---

### MỐC 20 — 10/9/2026 (11:04; PR 15:46 và 15:58) — Quyết định chiến lược vòng trường; trang /research demo kín

**GIAI ĐOẠN:** Thiết kế / Triển khai / Thử nghiệm live. **THỜI GIAN:** ⟦…⟧.

**1. Mục tiêu.** Vòng trường: hội đồng cần **hiểu, xem demo và tự test** trên geo3d. Một lần gửi đề
⇒ nhận **hình 3D + lời giải + nhãn engine kiểm chứng** (không phải bấm "giải" lần hai, không cần
đăng nhập, không tốn credit người dùng thường).

**2. Dụng cụ.** React/Vite; Vercel; app geo3d live (mạng trường); *(AI hỗ trợ code)*.

**3. Tiến trình & hiện tượng.**
- ⟦Thảo luận nhóm + cộng tác viên: vòng trường cần demo test được; vòng thành phố mới "moi"
  điểm chưa làm⟧ — quyết định ưu tiên trang demo, **không đổi mô hình credit của app chính**.
- Dựng trang `/research`: khoá truy cập nghiên cứu qua biến môi trường + header riêng; tắt mặc
  định (env trống); 4 test; tái dùng GeometryCanvas + SolveResultView + phân loại 3 Mức của app
  chính. Link giữ kín, chỉ hội đồng biết; ghi vào báo cáo.
- Đẩy lên `main` (PR #83, 15:46) sau khi được cộng tác viên đồng ý; cộng tác viên đặt env.
- **Test live #1 thất bại: HTTP 504** khi dựng hình (gọi không streaming, vượt trần thời gian
  Vercel). Sửa: dựng hình kiểu **streaming SSE** giữ kết nối (PR #84, 15:58).

**4. Kết quả & số liệu thô.** 1.218 test xanh; typecheck sạch; build OK; sau #84 dựng hình được
trên mạng trường.

**5. Rút kinh nghiệm.** Sandbox không gọi được API nên **mọi thứ phải test live**; lỗi 504 chỉ lộ
khi chạy thật trên Vercel.

**6. Kế hoạch tiếp theo.** Đưa 10 đề mẫu đủ 3 Mức lên demo và test từng bài.

---

### MỐC 21 — tối 10/9/2026 (20:53 → 22:20) — Test live vòng 2 với 10 đề mẫu; 6 bản vá theo lỗi quan sát được

**GIAI ĐOẠN:** Thử nghiệm / Sửa lỗi. **THỜI GIAN:** ⟦…⟧ (PR: 20:53–22:20).

**1. Mục tiêu.** Kiểm demo trên 10 đề khó đủ Mức 1 / Mức 2 / Mức 3; tìm vì sao demo lệch app chính.

**2. Dụng cụ.** Trang /research live; 10 đề mẫu (PR #85); ảnh chụp màn hình lỗi; *(AI hỗ trợ code)*.

**3. Tiến trình & hiện tượng (ghi đúng thứ tự quan sát).**
1. Đề mẫu 1: **"Chưa dựng được hình"**; đề 2, 3 chạy được ở app chính nhưng **đề 3 trên demo hình
   bị lỗi** ⇒ nghi demo gửi request khác app chính. Truy ra: body request demo khác ⇒ **PR #88**
   gửi giống hệt app chính (mode quick, detailLevel, useReasoning).
2. Demo bị ép model "low" ⇒ **PR #89** dùng model "high" cho bước vẽ ở demo (app chính giữ low)
   — chấp nhận rủi ro timeout để thử.
3. **Kiểm chứng trên demo lúc nào cũng Mức 3** ⇒ truy ra: model DỊCH mặc định
   (`gemini-3.1-flash-lite`) không nằm trong khoá đang dùng ⇒ **PR #90** bước dịch dùng
   `VILAO_MODEL` (chỉ gate cho demo; app chính hỏi cộng tác viên sau); **PR #91** nâng trần bước
   dịch 25s → 48s cho model mạnh.
4. Thêm **dán/chọn ảnh đề** (vision) — PR #87.
5. Bài "chóp đều cạnh a" ra **Mức 2** (minh hoạ đại diện). Nhóm muốn Mức 1 nhưng **quyết định
   KHÔNG đổi nhãn**: đáp chữ `a·√…` đúng tổng quát, nhưng số đo trên hình chỉ đúng ở thang a=1 —
   đổi nhãn là **vi phạm liêm chính** của chính hệ. Bài tỉ số SH/SD (bất biến affine) mới đủ điều
   kiện Mức 1 nếu bước dịch dựng được.
6. Bài SH/SD: hình vẽ được, nhãn "AI vẽ — chưa kiểm", nhưng ô lời giải báo **"Unexpected token
   'A', An error o…"** ⇒ đọc mã: Vercel trả **trang lỗi HTML** vì hàm quá **60 s** (trần gói Hobby):
   đường giải đang **dịch lại đề (~25 s) + viết lời giải (55 s) > 60 s**. **PR #92**: đường demo bỏ
   bước dịch-lại thừa (còn đúng 1 lần gọi model) + đọc text trước khi parse JSON để báo lỗi rõ.

**4. Kết quả & số liệu thô.**
- Trần thời gian mỗi request: 60 s; ngân sách thiết kế: **mỗi request đúng 1 lần gọi model lớn**;
  timeout dịch 48 s, lời giải 55 s.
- Sau #92: bài Mức 3 hiện được **hình + lời giải AI + nhãn Mức 3** không vỡ.
- ⟦Em tự test lại 10 đề sau deploy — ghi từng bài: Mức mấy, thời gian, lỗi gì⟧.

**5. Rút kinh nghiệm & lỗi sai.**
- Hai lỗi "trông như engine hỏng" (luôn Mức 3, hình lỗi) thực ra là **cấu hình model và request**
  — nhật ký phải ghi đúng nguyên nhân, không đổ cho engine.
- Cám dỗ "đổi nhãn Mức 2 thành Mức 1 cho đẹp" bị từ chối — đó là điểm hội đồng sẽ hỏi.

**6. Kế hoạch tiếp theo.** Đọc kỹ quy chế cấp trường; chuẩn bị sổ nhật ký viết tay; xác nhận env
và gói Vercel; xoay khoá sau cuộc thi.

---

### MỐC 22 — 11/9/2026 — Đọc Kế hoạch KHKT cấp trường; chạy lại bench xác nhận số

**GIAI ĐOẠN:** Đọc tài liệu / Kiểm thử. **THỜI GIAN:** ⟦…⟧.

**1. Mục tiêu.** Biết chính xác hồ sơ phải nộp gì, dạng gì, hạn nào.

**2. Dụng cụ.** Kế hoạch số 204/KH-NTN ngày 17/7/2026 (12 trang, bản scan); máy tính.

**3. Tiến trình & hiện tượng.**
- Phụ lục 2: sổ nhật ký **viết tay bút bi xanh/đen**, không xé/tẩy, ngày nào ghi ngày đó, giữ cả
  thất bại; cấu trúc bìa → mục lục (chừa 2–3 trang) → nhật ký hàng ngày → phụ lục dán biểu đồ in.
- Mục 5.3: nộp **file Word + PDF qua link và 02 bản in** cho thầy Nguyễn Hữu Tài (Phó Hiệu trưởng).
- Mục 6.2: Hội đồng thẩm định **quá trình** qua sổ nhật ký; thang điểm dự án kĩ thuật: vấn đề 10 /
  kế hoạch & phương pháp 15 / tiến hành 20 / sáng tạo 20 / trình bày (poster + phỏng vấn) 35.
- Phụ lục 1: AI được dùng có điều kiện — mọi thứ AI hỗ trợ phải **trích dẫn và ghi nhật ký**.
- Chạy lại `prove-bench` trên nhánh: **14/14, 7/7, 0 abstain, 0 đóng dấu sai** (khớp mốc 19).

**4. Kết quả & số liệu thô.** Hạn nộp hồ sơ **trước 15/9/2026**; phỏng vấn **26/9/2026**; tối đa
05 dự án THPT đi cấp thành phố **05/10/2026**. Chạy lại toàn bộ kiểm thử trên nhánh: **1.218/1.218
xanh, 183 file, 79,5 s** (lần chạy đầu báo 11 lỗi — truy ra do môi trường chạy nạp nhầm mã bản cũ,
không phải lỗi mã; chạy lại đúng cách thì xanh — ghi cả sự cố này vào sổ).

**5. Rút kinh nghiệm.** Nhật ký viết tay **không làm gộp một lần được** — phải chép ngay từ hôm nay,
lùi đúng các mốc trên.

**6. Kế hoạch tiếp theo.** ⟦Phân công: ai chép mốc nào; ảnh lời giải tay; xin GVHD ký từng trang⟧.

---

### MỐC 23 — 12/9/2026 — Đợt làm song song: 12 tác vụ AI hỗ trợ, nhóm chỉ đạo và gộp kết quả

**GIAI ĐOẠN:** Lập trình / Kiểm thử / Hoàn thiện hồ sơ. **THỜI GIAN:** ⟦…⟧ (git: rải cả ngày 12/9).

**1. Mục tiêu.** Dồn sức trước hạn 15/9: đẩy engine chứng minh lên mức kiểm được rộng hơn, hoàn thiện
hồ sơ, vá lỗ bảo mật, chuẩn bị đưa engine mới lên app demo — làm song song bằng nhiều trợ lý AI, mỗi
tác vụ một bản sao mã riêng, nhóm ra đề bài, đặt ràng buộc ("chính xác hoặc từ chối", không overfit,
không bịa số) rồi **kiểm lại toàn bộ trước khi gộp**.

**2. Dụng cụ.** 12 phiên trợ lý AI lập trình chạy song song *(AI hỗ trợ code + soạn thảo; nhóm chỉ đạo,
kiểm, quyết)*; git worktree; vitest; bench gate; replay đề thật (0 lượt API).

**3. Tiến trình & hiện tượng (theo thứ tự gộp).**
1. Tài liệu hội đồng (hướng dẫn test demo 1 trang, phiếu test 10 đề, checklist 15/9–26/9).
2. Sổ nhật ký docx đủ 22 mốc (17 trang) + nhật ký câu lệnh AI thêm 14 mục (Phụ lục 1).
3. **Review đường ống chứng minh nối app phát hiện lỗi thật**: bài chứng minh đi qua `/api/solve` bị hiện
   *đáp của LLM* kèm nhãn "Đã kiểm chứng" vì hàm kiểm chỉ nhận đáp có số — sửa + 9 test mô phỏng.
4. **Gỡ 6 khoá API còn hard-code** trong `testApiKeys.js` trên nhánh nghiên cứu (main đã gỡ 1/9) → đọc từ
   biến môi trường; thêm CI quét khoá; ghi danh sách khoá đã lộ để **thu hồi**.
5. +6 predicate quyết định được (chéo nhau, đường nằm trong mặt, góc bằng nhau, khoảng cách bằng nhau,
   cách đều, đồng quy) — tất cả bằng số học chính xác, không acos/không chia.
6. Báo cáo v10 → v11: 20 thay đổi có bảng đối chiếu để học sinh duyệt từng dòng; còn 5 chỗ trống phải
   người thật điền; ước lượng 15 trang.
7. Hỏi-đáp phỏng vấn +12 câu; sửa số cũ ở poster/slides (1.086 → 1.218 test, thêm 116 đề thật…).
8. Corpus chứng minh 21 → **144 ca / 16 họ hình**, có 6 cặp "bẫy siết giả thiết"; prompt dịch viết lại
   danh mục cấu hình + 7 ví dụ JSON được test tự động.
9. Hội đồng mô phỏng v2 chấm ≈65/100, chỉ 4 tử huyệt (khai báo AI trong D.10 chưa đúng sự thật; câu
   "185 bài tự soạn"; chưa có hiện vật đứng tên học sinh; hồ sơ chưa soát lần cuối).
10. Port engine mới lên nhánh tách từ main (`claude/port-engine-len-main`, chưa merge): cùng bộ kế hoạch
    116 câu, engine cũ trên main chỉ **56 đúng / 55 từ chối**, engine mới **105 / 8**.
11. Gia cố proveGeneral: kiểm giả thiết chính xác mỗi thể hiện, phát hiện siết dư (`notAssumed`), loại
    suy biến, phản ví dụ phân số, ước lượng xác suất sai (hoặc ghi "không ước lượng").
12. 11 câu chưa đúng trên đề thật: phân loại nguyên nhân gốc; chỉ sửa lỗ hổng tổng quát (gộp đại lượng
    dạng π, thể tích bao lồi) → #110 từ chối → đúng; 4 câu plan sai **vẫn từ chối** (đúng); #114 nghi
    đáp chuẩn sai → không làm để khỏi thành sai-tự-tin.
- Xung đột khi gộp: 2 chỗ (một đoạn tài liệu, một dòng import) — sửa tay, build lại kernel, chạy lại đủ.

**4. Kết quả & số liệu thô (sau khi gộp hết, chạy lại trên một cây mã).**
- vitest **1.498/1.498** (187 file); bench gate **210/210**; prove-bench **144 ca: 85/85 · 59/59 · 0 từ
  chối · 0 đóng dấu sai**; replay 116 đề thật **106 đúng (91,4%) / 3 sai (2,6%) / 7 từ chối / precision 97,2%**
  (trước: 105/3/8).
- Nhánh port lên main: 2.476 test, gate 230/230 (main có thêm 20 ca), 12 function, build OK.

**5. Rút kinh nghiệm & lỗi sai.**
- Lần chạy test đầu trong bản sao mã báo 11 lỗi — do bản sao nạp nhầm mã cũ qua liên kết thư mục,
  không phải lỗi mã; chạy đúng cách thì xanh. Ghi lại vì đó là "thất bại thật".
- Kết quả tốt nhất của ngày không phải số 91,4% mà là **lỗi nhãn "Đã kiểm chứng" gắn nhầm lên đáp LLM**
  được bắt trước khi hội đồng thấy — đúng loại lỗi nguy hiểm nhất của hệ.
- Hội đồng mô phỏng nhắc: mọi con số đẹp vô nghĩa nếu khai báo AI không đúng sự thật ⇒ việc phải làm
  tiếp là **của học sinh**, không phải của máy.

**6. Kế hoạch tiếp theo.** ⟦Học sinh: viết tay Tóm tắt/D.7/D.9/D.10 và sửa khai báo AI; sửa câu "185 bài
tự soạn"; bắt đầu sổ viết tay; chụp ảnh lời giải tay; mỗi em 1 commit; anh Phước review nhánh port và
quyết định merge; thu hồi 6 khoá đã lộ⟧.

---

## C. Ghi chú để không ghi sai

- **Số 76,7% / 83,6% / 87,1% / 90,5%** là **cùng một bộ kế hoạch đã chụp** chạy qua các bản engine
  — so được với nhau. **Không** so với 72,4% của mốc 10 (bộ chấm cũ + lượt gọi khác).
- **Sai-tự-tin 1,5–6,2% vs 23,1–29,2%** (mốc 6) là số **đã bị mốc 14 bác** — vẫn ghi vào sổ vì đó
  là quá trình thật, nhưng ghi kèm "sau này phát hiện bộ chấm thiên vị".
- Bench chứng minh (mốc 19/22) **không phải đề thi thật** — chỉ chứng minh cơ chế chạy đúng.
- Việc trên nhánh `main` ngày 1–2/9 (bảo mật, 4 dạng câu hỏi, mô hình 3D vật thể) là của
  **cộng tác viên**, không ghi thành việc của nhóm.
