# Biên bản phản biện — Hội đồng 4 giám khảo (mô phỏng)

> Bốn agent đóng vai giám khảo ViSEF phản biện **bản nộp** `bao-cao-visef.docx`
> (rút văn bản qua pandoc). Mục đích: tìm chỗ yếu TRƯỚC khi hội đồng thật tìm.
> Nguyên tắc: không bịa số; mọi nghi vấn kèm trích mục; tách "mới thật" khỏi "nghe kêu".

## Bảng điểm (thang 10)

| Giám khảo | Tiêu chí & điểm |
|---|---|
| 1. Khoa học & Phương pháp | Độ chặt PP **5** · Giá trị bằng chứng **5** · Trung thực số liệu **6.5** |
| 2. Liêm chính & Hậu kiểm | Minh bạch đóng góp **3.5** · Tái lập/hậu kiểm **6** · Rủi ro liêm chính **4** |
| 3. Tính mới & Định vị | Tính mới **6.5** · Ý nghĩa **7** · Định vị vs related work **8** |
| 4. Trình bày & Phỏng vấn | Cấu trúc **6.5** · Rõ ràng **6** · Trực quan **5.5** · Thuyết phục **7.5** |

**Đồng thuận:** số liệu trung thực, truy được ra file run thật; engine-replay tái lập offline; kiểm hai chiều bắt được lỗi thật. Nền tảng đủ mạnh. Nhưng có **2 lỗ hổng P0** và phần thể thức chưa hoàn thiện.

---

## Điểm mạnh được công nhận
1. Số Bảng 3 khớp từng chữ số với `eval-runs/full210-*-norm/report.md` (chế độ THẬT). Không bịa số.
2. Engine-replay 210/210 tái lập offline, miễn phí, tất định (`npm run bench:gate`).
3. Kiểm hai chiều (công thức tay ↔ engine) bắt được lỗi thật: mặt cầu thang chữ rớt hệ số `a` (25/8 → 25a/8), commit `b7fbd09`.
4. Tách chỉ số an toàn (confidently-wrong, precision-khi-trả-lời) khỏi accuracy — đúng tư duy công cụ giáo dục.
5. Cổng từ chối theo **bất biến affine** (không dựa từ khoá) + chứng chỉ tự kiểm hạ `exact→approximate` — đóng góp thiết kế mới, có gốc toán học, truy được ra mã.
6. `related-work.md` đối chiếu trung thực, tự ghi "cần xác minh" cho chi tiết phụ.

---

## LỖ HỔNG THEO ƯU TIÊN

### P0 — Chặn giải nếu không xử lý

**P0-a. Liêm chính: không khai dùng AI viết code.**
`git log`: 98/109 commit tác giả "Claude", commit lõi mang `Co-Authored-By: Claude`. Báo cáo (§D.6) chỉ ghi công thư viện bên thứ ba, hứa "công bố toàn bộ mã nguồn" nhưng không khai AI-assisted coding. → dễ bị quy "không phải học sinh làm".
*Không lách. Phải: (1) khai minh bạch; (2) học sinh thật sự hiểu & bảo vệ được phần lõi.*

**P0-b. "Sân nhà" + suy diễn quá mạnh từ số.**
- Benchmark = tập ca engine đã giải đúng ⇒ 210/210 (Bảng 1) & 279/279 (Bảng 2) là **nhất quán hồi quy**, KHÔNG "xác nhận GT1". (du-lieu-benchmark.md §3: ca engine sai không được nạp làm golden.)
- **Cổng từ chối chưa được kiểm**: abstainRate ≈ 0.5% (1/210); benchmark không có ca "phải từ chối". Confidently-wrong thấp đến từ engine tự-kiểm + 22 ca "error", **chưa chứng minh nhờ cổng affine** ⇒ GT2 gán công sai nguồn.
- **Bảng 3 báo trên 210 ca** (gồm TRAIN), trái nguyên tắc "đo trên TEST" (danh-gia.md §1). Có bản TEST-65 nhưng không dùng.
- **Thiếu thống kê**: không khoảng tin cậy Wilson, không kiểm định hai tỉ lệ. "~4 lần" là điểm ước lượng, n=12 ca sai ⇒ CI rộng (~2–7 lần). "Gần như loại bỏ" là quá mạnh.
- **Bất đối xứng "error"**: hệ 3.5 = correct 175 + wrong 12 + abstain 1 + **error 22**; confidently-wrong = 12/210. Baseline không có van "error" tương đương. Bằng chứng thiên vị: pre-norm 2.5-flash, LLM-thẳng 76.7% > hệ 71.0% ⇒ lợi thế accuracy đến từ lớp chuẩn hoá chỉ thêm cho hệ.
- **GT3 nói quá**: tối ưu prompt (GA) mới chạy MÔ PHỎNG tất định (C.6 tự ghi), chưa trên LLM thật.
- **"Số học chính xác" bó hẹp**: kiểu số = 1 hữu tỉ × 1 căn không-chính-phương; không biểu diễn √2+√3, căn lồng. "279/279 exact" một phần vì chỉ nhận ca trong lớp biểu diễn được.

### P1 — Trừ điểm nặng

**P1-a. Định vị (GK3).** Trục "3D khó hơn AlphaGeometry" dễ đọc thành "chọn bài dễ hơn" (AG giải bài MỞ phải dựng điểm phụ; bài THPT đã xác định tới đồng dạng ⇒ toạ-độ-hoá đóng kín). Chưa so với **GeoGebra/Photomath** (công cụ học sinh thật sự dùng). Chỉ số an toàn (điểm bán mạnh nhất) bị chôn dưới bảng. GA nên hạ thành "hạ tầng sẵn sàng". Claim "đầu tiên" cần hạ giọng.

**P1-b. Trình bày (GK4).** Bìa còn ⟦…⟧ (bị coi bản nháp). Thiếu: mục lục, **bảng phân công thành viên**, kế hoạch/tiến độ, lời cảm ơn, phụ lục. Thiếu hình: (1) ví dụ đề→Construction Plan JSON→đáp căn/π; (2) ảnh giao diện app 3D; (3) **biểu đồ cột confidently-wrong** (5% vs 22–24%). Hình 1 dạng khung ký tự dễ vỡ layout. Thuật ngữ (confidently-wrong, bất biến affine, scaleSymbol, tier, engine-replay) chưa việt hoá/định nghĩa trước khi dùng. Giọng còn "nội bộ" ("cỗ máy", "hạng mục tiếp theo"). Định dạng số chưa nhất quán.

**P1-c. Mâu thuẫn nội bộ (GK2).** §D.5 viết "khi học sinh tự giải đề thi thật" nhưng `bench/worklists/de-that/` chỉ có template rỗng; §7 thừa nhận chưa có đề thật. `phong-van-bao-ve.md` còn ghi "26 ca". Phải đồng bộ toàn bộ tài liệu về 210 ca + số end-to-end đã đo.

### P2 — Nên làm để chắc

- Ghi nguồn benchmark theo datasheet (trường `source` thật từng ca); khi nhập đề SGK/đề thi ghi trang/mã đề, không phát tán toàn văn nếu vướng bản quyền.
- Commit `results.json` từng-ca (gỡ khỏi `.gitignore` hoặc bản ẩn danh) để hậu kiểm soi ca nào sai.
- Hướng dẫn tái lập một trang ở đầu repo (offline `bench:gate` không tốn tiền; end-to-end cần khoá gì, chi phí bao nhiêu).
- Ghi rõ endpoint/model/ngày chạy để xác thực (đã có timestamp — tốt).

---

## Câu hỏi "tử huyệt" (chuẩn bị sẵn câu trả lời)
1. Git cho thấy gần như toàn bộ engine do AI commit — em chứng minh phần nào CHÍNH em viết bằng cách nào?
2. Cổng từ chối kích hoạt mấy lần trên 210 ca? Số nào chứng minh nó "gần như loại bỏ đáp sai tự tin"?
3. Nhìn riêng TEST-65 thì con số bao nhiêu, sao Bảng 3 báo trên cả 210?
4. 22 ca "error" tính vào đâu? Cho baseline cùng van đó thì nó còn 24% không?
5. Bỏ cổng affine + chứng chỉ tự kiểm đi, phần còn lại có phải chỉ là toạ-độ-hoá + tính định thức (sách giáo khoa)?
6. Cho tôi xem đề thi thật đã nhập + lời giải tay của em (§D.5).
7. Khác gì GeoGebra/Photomath mà học sinh đang dùng?
8. Mở `answer.ts`: hàm hạ `exact→approximate` hoạt động ra sao, vì sao dung sai `1e-6·max(1,|giá trị|)`?

---

## DANH SÁCH SỬA GỘP (checklist tới 15/9)

**Nhóm A — Liêm chính (P0-a):**
- [ ] Thêm mục "Phân định đóng góp & công cụ" (3 cột: học sinh tự làm / AI hỗ trợ lập trình / thư viện–dịch vụ bên thứ ba). Khai thẳng dùng trợ lý AI viết engine dưới sự chỉ đạo & kiểm thử của nhóm.
- [ ] Lập nhật ký nghiên cứu (logbook) có mốc thời gian + ảnh lời giải tay của học sinh cho vài ca golden.
- [ ] Hai em học thuộc & giải thích được: cổng affine, `exact→approximate`, tự giải 3–5 đề tiêu biểu.

**Nhóm B — Khoa học (P0-b):**
- [ ] Bổ sung rổ ca "phải từ chối" (thiếu dữ kiện/ô cấm) → báo precision/recall của cổng từ chối. Nếu không có, gỡ mọi tuyên bố "cổng loại bỏ sai tự tin".
- [ ] Báo Bảng 3 trên TEST (ghi rõ n từng ô), hoặc bỏ tuyên bố tách train/test.
- [ ] Thêm khoảng tin cậy Wilson + kiểm định hai tỉ lệ; thay "~4 lần" bằng ước lượng kèm CI.
- [ ] Minh bạch 22 ca "error": tính vào mẫu số nào, áp cùng quy tắc cho baseline; báo confidently-wrong hai kịch bản (error tính/không tính là sai).
- [ ] Nêu prompt baseline, xác nhận cùng model/bộ chấm; thêm baseline "LLM + prompt tốt/CoT" để không so với rơm.
- [ ] Gỡ over-claim: 210/210 & 279/279 là "nhất quán hồi quy trên tập tuyển-chọn-để-engine-giải-được", KHÔNG "xác nhận GT1". Tách GT3: phần đã đo (lớp chuẩn hoá) vs chưa đo (tối ưu prompt thật).
- [ ] Nêu ranh giới lớp số (ℚ×√ một căn); ước lượng tỉ lệ đề thật ngoài lớp.

**Nhóm C — Định vị (P1-a):**
- [ ] Đổi trục: từ "3D khó hơn AG" → "AN TOÀN KIỂM CHỨNG cho giáo dục".
- [ ] Thêm mục "So với GeoGebra / app giải toán chụp-đề".
- [ ] Bổ sung 15–20 ca "ngoài sân nhà" từ đề thi thật + báo tỉ lệ từ chối (đóng khung tỉ lệ từ chối cao = bằng chứng an toàn hoạt động).
- [ ] Dời precision 94% / confidently-wrong 5% lên làm kết quả CHÍNH; accuracy làm phụ; thêm câu chốt chống "AI xịn".
- [ ] Hạ GA xuống "hạ tầng sẵn sàng"; hạ giọng claim "đầu tiên".

**Nhóm D — Trình bày (P1-b):**
- [ ] Điền hết ⟦…⟧ ở bìa; rà toàn văn không còn ⟦ ⟧.
- [ ] Thêm mục lục + bảng phân công thành viên + kế hoạch + lời cảm ơn + phụ lục (đề→plan→đáp mẫu).
- [ ] Thêm 3 hình: ví dụ đề→plan→đáp; ảnh app 3D; biểu đồ cột confidently-wrong. Vẽ lại Hình 1 thành sơ đồ đồ hoạ.
- [ ] Thêm khung "Giải thích thuật ngữ" sau Tóm tắt; định nghĩa confidently-wrong ngay lần đầu.
- [ ] Chuẩn giọng trang trọng; thống nhất định dạng số; "4,2–4,3 lần" thay "~4 lần".

**Nhóm E — Đồng bộ (P1-c, P2):**
- [ ] Sửa §D.5: bỏ "đề thi thật", ghi đúng "đối chiếu đáp tự giải trên ca thang chữ (mặt cầu)".
- [ ] Đồng bộ mọi tài liệu về 210 ca + số end-to-end (sửa phong-van-bao-ve.md "26 ca").
- [ ] Ghi nguồn benchmark; commit results.json từng-ca (bản ẩn danh); hướng dẫn tái lập một trang.
