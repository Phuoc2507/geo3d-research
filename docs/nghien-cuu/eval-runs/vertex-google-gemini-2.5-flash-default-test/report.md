# So sánh baseline — vertex-google-gemini-2.5-flash-default-test

_Chạy 2026-08-29T09:10:56.499Z · 65 ca · nhà cung cấp: vertex (google/gemini-2.5-flash) · chế độ: THẬT (LLM)._

| Phương pháp | Accuracy | Confidently-wrong | Precision khi trả lời | Từ chối | Lỗi | Latency TB |
|---|---:|---:|---:|---:|---:|---:|
| system | 69.2% | 1.5% | 97.8% | 1.5% | 18 | 5324ms |
| llm-direct | 75.4% | 23.1% | 76.6% | 0.0% | 1 | 3150ms |

## Ý nghĩa các cột
- **Accuracy**: tỉ lệ ra đáp ĐÚNG trên toàn tập.
- **Confidently-wrong**: tỉ lệ đưa đáp số SAI một cách tự tin — chỉ số AN TOÀN then chốt (càng thấp càng tốt).
- **Precision khi trả lời**: khi hệ CÓ đưa đáp (không từ chối), tỉ lệ đúng = correct/(correct+wrong). Hệ Neuro-Symbolic kỳ vọng CAO nhờ tự kiểm + từ chối an toàn.
- **Từ chối**: tỉ lệ hệ chủ động không trả lời (an toàn, không tính là sai).

> Chạy trên LLM thật (google/gemini-2.5-flash).
