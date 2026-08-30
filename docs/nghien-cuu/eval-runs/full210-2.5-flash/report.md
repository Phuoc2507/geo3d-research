# So sánh baseline — full210-2.5-flash

_Chạy 2026-08-29T09:35:55.423Z · 210 ca · nhà cung cấp: vertex (google/gemini-2.5-flash) · chế độ: THẬT (LLM)._

| Phương pháp | Accuracy | Confidently-wrong | Precision khi trả lời | Từ chối | Lỗi | Latency TB |
|---|---:|---:|---:|---:|---:|---:|
| system | 71.0% | 4.3% | 94.3% | 1.0% | 50 | 6433ms |
| llm-direct | 76.7% | 22.9% | 77.0% | 0.0% | 1 | 2841ms |

## Ý nghĩa các cột
- **Accuracy**: tỉ lệ ra đáp ĐÚNG trên toàn tập.
- **Confidently-wrong**: tỉ lệ đưa đáp số SAI một cách tự tin — chỉ số AN TOÀN then chốt (càng thấp càng tốt).
- **Precision khi trả lời**: khi hệ CÓ đưa đáp (không từ chối), tỉ lệ đúng = correct/(correct+wrong). Hệ Neuro-Symbolic kỳ vọng CAO nhờ tự kiểm + từ chối an toàn.
- **Từ chối**: tỉ lệ hệ chủ động không trả lời (an toàn, không tính là sai).

> Chạy trên LLM thật (google/gemini-2.5-flash).
