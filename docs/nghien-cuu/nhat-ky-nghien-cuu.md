# Nhật ký nghiên cứu — GeometryPro (mẫu để nhóm điền)

> Mục đích: làm **bằng chứng quá trình** cho khâu hậu kiểm — chứng minh hai em thật sự
> LÀM CHỦ đề tài (hiểu, quyết định, tự giải, phát hiện lỗi), kể cả khi có dùng công cụ
> AI hỗ trợ lập trình. **Điền trung thực theo đúng thực tế.** Ghi ngắn gọn, có mốc thời gian,
> đính kèm ảnh/đường dẫn khi có (ảnh lời giải tay, ảnh màn hình, số hiệu commit…).
>
> Có thể giữ nhật ký này ở đây (Markdown), hoặc chép sang Google Sheets/sổ tay — miễn là
> có mốc thời gian và bằng chứng.

## 1. Thông tin nhóm
- Thành viên 1: ⟦Họ tên – lớp⟧ — vai trò chính: ⟦…⟧
- Thành viên 2: ⟦Họ tên – lớp⟧ — vai trò chính: ⟦…⟧
- Giáo viên hướng dẫn: ⟦…⟧
- Thời gian thực hiện: ⟦từ … đến …⟧

## 2. Nhật ký theo mốc thời gian
> Mỗi dòng một hoạt động. "Người làm" ghi rõ em nào / cả nhóm / (có) dùng công cụ AI hỗ trợ.
> "Bằng chứng" ghi đường dẫn ảnh, số commit, tên file, hoặc "ảnh lời giải tay #…".

| Ngày | Người làm | Việc / hoạt động | Kết quả | Bằng chứng |
|---|---|---|---|---|
| ⟦dd/mm⟧ | ⟦…⟧ | ⟦vd: thiết kế cổng từ chối 3 câu hỏi⟧ | ⟦…⟧ | ⟦…⟧ |
| ⟦dd/mm⟧ | ⟦…⟧ | ⟦vd: tự giải câu mặt cầu ngoại tiếp OABC, ra √14/2⟧ | ⟦khớp engine⟧ | ⟦ảnh lời giải tay #1⟧ |
| ⟦dd/mm⟧ | ⟦…⟧ | ⟦vd: phát hiện engine rớt chữ a ở mặt cầu (25/8 vs 25a/8)⟧ | ⟦báo lỗi + vá⟧ | ⟦commit b7fbd09⟧ |
| ⟦dd/mm⟧ | ⟦…⟧ | ⟦vd: chạy eval Vertex 3.5-flash trên TEST-65⟧ | ⟦CW 6.2%⟧ | ⟦eval-runs/…-test/report.md⟧ |
| … | | | | |

## 3. Bằng chứng "học sinh làm chủ" (chuẩn bị cho phỏng vấn/hậu kiểm)
Điền thật — đây là phần giám khảo hay hỏi nhất.

- **Tự giải tay các ca tiêu biểu** (đính ảnh lời giải viết tay của em, ghi rõ em nào giải):
  - Ca 1: ⟦đề + đáp + ảnh⟧
  - Ca 2: ⟦…⟧
  - (Nên có ≥ 5 ca thuộc các dạng khác nhau: khoảng cách, thể tích, mặt cầu, góc…)
- **Giải thích được cơ chế lõi** (viết vài dòng bằng lời của em, để nhớ khi bảo vệ):
  - Cổng từ chối theo bất biến affine hoạt động thế nào? ⟦…⟧
  - Vì sao engine hạ `exact → approximate` khi lệch dung sai `1e-6`? ⟦…⟧
  - "Thang chữ" (scaleSymbol) ghép `×aᵏ` ra sao? ⟦…⟧
- **Mức độ dùng công cụ AI** (khai trung thực): phần mã nào do AI hỗ trợ viết, nhóm đã
  đọc/hiểu/kiểm thử/sửa những gì: ⟦…⟧

## 4. Chuẩn bị trả lời câu hỏi "tử huyệt" (từ biên bản phản biện)
Mỗi câu chuẩn bị sẵn 2–4 câu trả lời.

1. Git cho thấy nhiều commit do AI — phần nào chính em làm, chứng minh sao? → ⟦…⟧
2. Cổng từ chối kích hoạt mấy lần trên 210 ca; đo precision/recall thế nào? → ⟦chạy scripts/eval/do-abstain.mjs, dán số⟧
3. Vì sao Bảng 3 báo trên TEST-65; con số ra sao? → ⟦…⟧
4. Bỏ cổng affine + chứng chỉ tự kiểm, phần còn lại có phải chỉ là toạ-độ-hoá? → ⟦…⟧
5. Khác gì GeoGebra/Photomath? → ⟦…⟧
6. Cho xem đề thi thật đã nhập + lời giải tay? → ⟦đính kèm khi có⟧

## 5. Danh mục việc còn phải làm trước 15/9
- [ ] Điền hết placeholder ⟦…⟧ ở bìa báo cáo.
- [ ] Chèn ảnh giao diện app 3D (Phụ lục B).
- [ ] Giải & nhập ≥ 15–20 đề thi thật (ngoài "sân nhà"); chạy đo tỉ lệ từ chối.
- [ ] Chạy `do-abstain.mjs` với khoá Vertex → điền precision/recall cổng từ chối.
- [ ] Hoàn thiện bảng "Phân định đóng góp" (D.6) cho đúng thực tế.
- [ ] Mỗi em tự giải thành thạo ≥ 5 đề để bảo vệ.
