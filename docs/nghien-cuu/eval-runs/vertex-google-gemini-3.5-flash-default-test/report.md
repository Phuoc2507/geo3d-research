# So sánh baseline — vertex-google-gemini-3.5-flash-default-test

_Chạy 2026-08-29T09:13:00.121Z · 65 ca · nhà cung cấp: vertex (google/gemini-3.5-flash) · chế độ: THẬT (LLM)._

| Phương pháp | Accuracy | Confidently-wrong | Precision khi trả lời | Từ chối | Lỗi | Latency TB |
|---|---:|---:|---:|---:|---:|---:|
| system | 84.6% | 6.2% | 93.2% | 0.0% | 6 | 6262ms |
| llm-direct | 56.9% | 29.2% | 66.1% | 0.0% | 9 | 2924ms |

## Ý nghĩa các cột
- **Accuracy**: tỉ lệ ra đáp ĐÚNG trên toàn tập.
- **Confidently-wrong**: tỉ lệ đưa đáp số SAI một cách tự tin — chỉ số AN TOÀN then chốt (càng thấp càng tốt).
- **Precision khi trả lời**: khi hệ CÓ đưa đáp (không từ chối), tỉ lệ đúng = correct/(correct+wrong). Hệ Neuro-Symbolic kỳ vọng CAO nhờ tự kiểm + từ chối an toàn.
- **Từ chối**: tỉ lệ hệ chủ động không trả lời (an toàn, không tính là sai).

> Chạy trên LLM thật (google/gemini-3.5-flash).
