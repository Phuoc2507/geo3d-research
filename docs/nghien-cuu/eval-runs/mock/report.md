# So sánh baseline — mock

_Chạy 2026-08-29T10:14:03.768Z · 6 ca · nhà cung cấp: vilao · chế độ: MOCK (kiểm thử harness, KHÔNG phải kết quả khoa học)._

| Phương pháp | Accuracy | Confidently-wrong | Precision khi trả lời | Từ chối | Lỗi | Latency TB |
|---|---:|---:|---:|---:|---:|---:|
| system | 100.0% | 0.0% | 100.0% | 0.0% | 0 | 4ms |
| llm-direct | 50.0% | 16.7% | 75.0% | 33.3% | 0 | 0ms |

## Ý nghĩa các cột
- **Accuracy**: tỉ lệ ra đáp ĐÚNG trên toàn tập.
- **Confidently-wrong**: tỉ lệ đưa đáp số SAI một cách tự tin — chỉ số AN TOÀN then chốt (càng thấp càng tốt).
- **Precision khi trả lời**: khi hệ CÓ đưa đáp (không từ chối), tỉ lệ đúng = correct/(correct+wrong). Hệ Neuro-Symbolic kỳ vọng CAO nhờ tự kiểm + từ chối an toàn.
- **Từ chối**: tỉ lệ hệ chủ động không trả lời (an toàn, không tính là sai).

> ⚠️ MOCK: 'llm-direct' là giả lập tất định, 'system' dùng plan golden (bỏ khâu dịch). Chỉ để kiểm thử bảng chỉ số. Số THẬT cần chạy không có --mock, có API key.
