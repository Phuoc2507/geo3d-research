# So sánh baseline — full210-3.5-flash

_Chạy 2026-08-29T09:32:40.077Z · 210 ca · nhà cung cấp: vertex (google/gemini-3.5-flash) · chế độ: THẬT (LLM)._

| Phương pháp | Accuracy | Confidently-wrong | Precision khi trả lời | Từ chối | Lỗi | Latency TB |
|---|---:|---:|---:|---:|---:|---:|
| system | 81.4% | 6.2% | 92.9% | 1.4% | 23 | 5623ms |
| llm-direct | 65.2% | 25.7% | 71.7% | 0.0% | 19 | 2792ms |

## Ý nghĩa các cột
- **Accuracy**: tỉ lệ ra đáp ĐÚNG trên toàn tập.
- **Confidently-wrong**: tỉ lệ đưa đáp số SAI một cách tự tin — chỉ số AN TOÀN then chốt (càng thấp càng tốt).
- **Precision khi trả lời**: khi hệ CÓ đưa đáp (không từ chối), tỉ lệ đúng = correct/(correct+wrong). Hệ Neuro-Symbolic kỳ vọng CAO nhờ tự kiểm + từ chối an toàn.
- **Từ chối**: tỉ lệ hệ chủ động không trả lời (an toàn, không tính là sai).

> Chạy trên LLM thật (google/gemini-3.5-flash).
