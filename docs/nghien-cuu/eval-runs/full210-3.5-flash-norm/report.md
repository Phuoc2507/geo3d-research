# So sánh baseline — full210-3.5-flash-norm

_Chạy 2026-08-29T09:51:04.511Z · 210 ca · nhà cung cấp: vertex (google/gemini-3.5-flash) · chế độ: THẬT (LLM)._

| Phương pháp | Accuracy | Confidently-wrong | Precision khi trả lời | Từ chối | Lỗi | Latency TB |
|---|---:|---:|---:|---:|---:|---:|
| system | 83.3% | 5.7% | 93.6% | 0.5% | 22 | 5512ms |
| llm-direct | 66.7% | 24.3% | 73.3% | 0.0% | 19 | 2826ms |

## Ý nghĩa các cột
- **Accuracy**: tỉ lệ ra đáp ĐÚNG trên toàn tập.
- **Confidently-wrong**: tỉ lệ đưa đáp số SAI một cách tự tin — chỉ số AN TOÀN then chốt (càng thấp càng tốt).
- **Precision khi trả lời**: khi hệ CÓ đưa đáp (không từ chối), tỉ lệ đúng = correct/(correct+wrong). Hệ Neuro-Symbolic kỳ vọng CAO nhờ tự kiểm + từ chối an toàn.
- **Từ chối**: tỉ lệ hệ chủ động không trả lời (an toàn, không tính là sai).

> Chạy trên LLM thật (google/gemini-3.5-flash).
