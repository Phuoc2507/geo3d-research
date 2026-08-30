# GeometryPro — Hệ Neuro‑Symbolic giải hình học không gian (phần NGHIÊN CỨU)

> **Một câu:** Đề tài không phải “một máy giải toán”, mà là một **mẫu kiến trúc AI đáng tin** —
> chứng minh trên bài hình học không gian THPT rằng có thể bắt AI **“thà từ chối còn hơn bịa”**:
> LLM chỉ **DỊCH** đề thành mô hình hình thức, một **engine tất định TÍNH và TỰ KIỂM**, và một
> **cổng từ chối** an toàn khi đề thiếu dữ kiện.

Đây là repo **nghiên cứu** (engine ký hiệu + bộ dữ liệu chuẩn + quy trình đánh giá), tách khỏi
ứng dụng thương mại để giám khảo dễ xem và **tái lập**. Báo cáo đầy đủ: [`docs/nghien-cuu/`](docs/nghien-cuu/).

---

## Tái lập nhanh (offline, miễn phí — không cần khoá API)

```bash
npm install
npm run bench:gate      # engine-replay trên 210 ca chuẩn  → kỳ vọng: GATE PASS 210/210
npm test                # bộ kiểm thử đơn vị của engine
```

`bench:gate` chạy **tất định, offline**: đưa kế hoạch dựng hình đã đúng qua engine và đối chiếu
đáp — không gọi AI, không tốn tiền. Đây là bằng chứng tái lập mạnh nhất; giám khảo chạy được ngay.

Thí nghiệm **end‑to‑end** (LLM dịch → engine) cần khoá LLM thật (Gemini qua Vertex AI):

```bash
VERTEX_SA_KEY=/duong/dan/sa.json VERTEX_PROJECT=<project> \
  bash scripts/eval/chay-eval-da-mo-hinh.sh          # so hệ vs LLM giải thẳng
VERTEX_SA_KEY=/duong/dan/sa.json VERTEX_PROJECT=<project> \
  node scripts/eval/do-abstain.mjs --provider vertex --model google/gemini-3.5-flash  # đo cổng từ chối
```

> ⚠️ Khoá service‑account (`sa.json`) chỉ dùng làm biến môi trường — **không commit vào repo**
> (đã chặn trong `.gitignore`).

---

## Kết quả đo được (tóm tắt; chi tiết ở báo cáo)

- **Engine‑replay:** 210/210 ca đạt, 0 sai — engine nhất quán trên tập chuẩn.
- **Độ chính xác ký hiệu:** 279/279 đáp ở dạng căn/π/hữu tỉ, 0 đáp làm tròn.
- **An toàn (end‑to‑end, tập TEST giữ riêng 65 ca):** tỉ lệ “sai tự tin” (confidently‑wrong)
  của hệ **1.5–6.2%** so với **23.1–29.2%** khi để LLM giải thẳng — khoảng tin cậy 95% không
  chồng nhau. Đóng góp cốt lõi là **AN TOÀN kiểm chứng được**, không phải accuracy cao hơn.

---

## Bản đồ thư mục

| Đường dẫn | Nội dung |
|---|---|
| `api/_lib/kernel/` | Engine ký hiệu (số học chính xác hữu tỉ + căn; khoảng cách/góc/thể tích/diện tích/mặt cầu/giải tích; tự kiểm) |
| `api/_lib/kernel-bridge/` | Khối dịch: prompt dịch đề, cổng từ chối, phân tầng độ tin cậy (tier), thang chữ |
| `api/_lib/bench/` | So đáp, chạy gate, capture ca |
| `bench/golden/` | 210 ca chuẩn (đề + kế hoạch JSON + đáp đã xác minh) |
| `bench/splits/` | Tách train/test tất định (seed 42) |
| `bench/abstain-set/` | Bộ ca “phải từ chối” để đo cổng từ chối |
| `scripts/eval/` | Harness so sánh baseline đa mô hình + đo cổng từ chối |
| `scripts/label/` | Công cụ gán nhãn benchmark (kiểm hai chiều: công thức tay ↔ engine) |
| `scripts/prompt-opt/` | Tối ưu prompt tiến hoá (đã hiện thực; hiện chạy chế độ mô phỏng) |
| `docs/nghien-cuu/` | **Báo cáo khoa học**, biên bản phản biện, tài liệu dữ liệu & năng lực/ranh giới |

---

## Ứng dụng — ghi trung thực “đã làm” vs “hướng phát triển”

**Đã có trong repo này:**
- Nhãn độ tin cậy (đã kiểm / chưa chắc / từ chối) cho mỗi đáp.
- Ngân hàng đề + đáp chuẩn tự sinh và **kiểm hai chiều** tự động.
- Quy trình đánh giá tái lập được (engine‑replay offline + eval đa mô hình).

**Hướng phát triển (CHƯA hiện thực trong repo này):**
- Trợ giảng chấm/kiểm lời giải cho giáo viên (các mảnh ghép đã có, chưa ráp thành tính năng).
- Mở rộng **cùng khuôn “dịch–tính–tự kiểm–từ chối”** sang môn khác (Vật lý, Hoá) — hiện engine
  kiểm chứng mới phủ hình học; các môn khác nếu có chỉ ở mức mô phỏng/trực quan, chưa nối engine.
- Bất kỳ lĩnh vực nào “đọc hiểu ngôn ngữ + tính toán chặt + sai thì nguy hiểm”.

---

## Liêm chính & ghi công (minh bạch)

Dự án có **sử dụng trợ lý lập trình AI để hiện thực phần mã nguồn**, dưới sự chỉ đạo, kiểm thử và
nghiệm thu của nhóm học sinh. Các **quyết định thiết kế, công thức toán, việc soạn & xác minh đề,
và diễn giải kết quả** là do nhóm thực hiện. Việc dùng công cụ AI hỗ trợ lập trình được khai báo
công khai; bảng phân định đóng góp chi tiết nằm trong báo cáo (`docs/nghien-cuu/`, mục Đạo đức &
liêm chính). Mọi số liệu trong báo cáo đều đo được và tái lập được; ô chưa đo ghi rõ.

## Giấy phép
[MIT](LICENSE).
