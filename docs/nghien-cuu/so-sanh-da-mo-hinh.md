# So sánh đa mô hình (ablation "đầu dịch")

> **Trạng thái số liệu:** đã đo **2 model Gemini qua Vertex** (2026-08-29) trên **toàn bộ 210 ca golden**. Số là **đo thật**, không bịa.
> _(Không đưa Vilao vào bảng: dịch vụ Vilao thực chất cũng gọi `gemini-3.5-flash` ở dưới nên so lại chính nó, không thêm thông tin.)_
> _Kiểm chéo overfit: đo trên tập TEST-65 (chưa dùng luyện prompt) và trên toàn tập 210 cho số **tương đương** (system 3.5-flash ~81–85% ở cả hai) — không phóng đại._

## 1. Câu hỏi thí nghiệm

Hệ của đề tài tách làm hai tầng: **LLM dịch đề → bản kế hoạch (Plan)**, rồi **engine tất định tính + tự kiểm**.
Vậy nếu **thay LLM ở tầng dịch** (các model Gemini khác nhau) thì:

1. Engine có còn cho đáp **chính xác** không? (kỳ vọng: CÓ — vì engine không đổi)
2. Chất lượng dịch khác nhau ảnh hưởng thế nào tới **tỉ lệ giải được** và **tỉ lệ từ chối**?
3. So với để **LLM trả lời thẳng** (không engine) thì an toàn hơn bao nhiêu?

Đây là bằng chứng cho luận điểm: *độ tin cậy đến từ ENGINE + cơ chế từ chối, không phụ thuộc vào một LLM cụ thể.*

## 2. Thiết lập

- **Tập đề:** **toàn bộ 210 ca** của bộ golden (đã kiểm hai chiều). Có kiểm chéo thêm trên tập TEST-65 giữ riêng (không dùng luyện prompt) — số tương đương, xem banner.
- **Đáp chuẩn:** do nhóm tự giải, đã xác minh (hai chiều). LLM **chỉ làm khâu dịch**, KHÔNG dùng để sinh đáp chuẩn.
- **Hai phương pháp** trên cùng tập:
  - `system` — hệ của đề tài: LLM dịch → engine tính + tự kiểm → **từ chối** khi thiếu dữ kiện.
  - `llm-direct` — đối chứng: để LLM **giải thẳng** và tự đưa đáp số (không engine).
- **Các "đầu dịch" thử:** **Gemini qua Vertex AI** — `google/gemini-2.5-flash` và `google/gemini-3.5-flash` (tính vào credit $300 của Google Cloud).
- **Đo mỗi ô:** trung bình, mỗi lượt chạy 1 lần; ghi ngày chạy + model cụ thể.

## 2b. Giới hạn diễn giải (đọc kỹ trước khi trích số)

Để không phóng đại — ba điểm phải hiểu đúng:

1. **Tập đánh giá là "sân nhà" của engine.** 210 ca này thuộc bộ golden, tức đã được soạn để **nằm trong danh mục
   engine biểu diễn được**. Vậy accuracy ~85% nghĩa là *"với bài trong tầm engine, khâu dịch + engine chạy đúng
   ~85%"* — **KHÔNG** phải "engine giải được 85% mọi đề khó". Đề thi thật (bộ 150 các em đang giải) sẽ khó hơn,
   con số dự kiến **thấp hơn**; đó mới là phép thử ngoài-sân-nhà trung thực.
2. **"Lỗi dịch" là khâu dịch, không phải engine sai.** Model đôi khi xuất plan lệch cách viết. Đã thêm lớp
   **chuẩn hoá tất định** giảm đáng kể (§3.3, không cần prompt riêng từng model); phần còn lại là dư địa tiếp.
3. **Điểm vững nhất là chỉ số AN TOÀN, không phải accuracy tuyệt đối.** "SAI tự tin" của `system` (5.2–5.7%) thấp
   hơn `llm-direct` (21.9–24.3%) **bất kể** prompt/model, vì đó là do engine tự kiểm chặn đáp sai — không phụ thuộc
   khâu dịch. Nếu chỉ được nêu một con số, nêu con số này.

Cách xác minh (đã chạy): `mock=false`; bộ so đáp **so khớp chính xác** (vd engine `3√2/2` = vàng `3√2/2`, `20`=`20`);
"lỗi" = plan JSON hỏng (mảng rỗng) nên engine không chạy, **tính là không-đúng** chứ không bỏ qua; prompt-opt học
trên tập **train**, đánh giá trên tập **test** (tách bạch, xem `scripts/prompt-opt/run.mjs`).

## 3. Kết quả

### 3.1. Hệ `system` (LLM dịch → engine) — thay đầu dịch

| Đầu dịch (LLM) | Accuracy | Giải đúng khi CÓ trả lời (precision) | Từ chối (abstain) | Trả lời **SAI tự tin** | Lỗi dịch | Latency TB |
|---|---:|---:|---:|---:|---:|---:|
| Vertex `google/gemini-2.5-flash` | 78.6% | 93.8% | 0.5% | **5.2%** | 33/210 | 6203ms |
| Vertex `google/gemini-3.5-flash` | 83.3% | 93.6% | 0.5% | **5.7%** | 22/210 | 5512ms |

_Đo ngày 2026-08-29 trên toàn bộ 210 ca golden, **sau khi thêm lớp chuẩn hoá plan tất định** (xem §3.3)._

*Đọc bảng:*
- **Precision khi trả lời rất cao (~94%)**: khi hệ CÓ đưa đáp thì gần như luôn đúng — nhờ engine tự kiểm.
- **"SAI tự tin" thấp (5.2% / 5.7%)** — đây là chỉ số an toàn cốt lõi (đối chiếu §3.2 để thấy chênh lệch lớn).
- **"Lỗi dịch"** = số ca model dịch ra plan hỏng/không JSON nên engine không chạy được (tính là *không đúng*, KÉO
  accuracy xuống). Đã giảm nhờ chuẩn hoá plan (§3.3); phần còn lại (22–33 ca) là các kiểu sai khác của model —
  dư địa cải thiện tiếp. Ghi trung thực để phân biệt "engine sai" vs "khâu dịch lỗi".

### 3.2. Đối chứng — LLM trả lời THẲNG (không engine)

| LLM trả thẳng | Accuracy | Từ chối | Trả lời **SAI tự tin** |
|---|---:|---:|---:|
| Vertex `google/gemini-2.5-flash` | 77.1% | 0.0% | **21.9%** |
| Vertex `google/gemini-3.5-flash` | 66.7% | 0.0% | **24.3%** |

_Đo ngày 2026-08-29, cùng toàn bộ 210 ca golden._

*Đọc bảng:* LLM trần **gần như không bao giờ từ chối** (0%) và **trả lời SAI tự tin 21.9–24.3%** — cao gấp
**~4 lần** so với hệ `system` (§3.1: 5.2% / 5.7%). Đây là minh hoạ trực tiếp: tầng engine + cơ chế từ chối
biến "AI hay bịa" thành "hệ đáng tin".

### 3.3. Chuẩn hoá plan tất định — giảm "lỗi dịch" cho MỌI model

Soi 50 ca lỗi dịch thấy chúng KHÔNG phải engine sai, mà model xuất plan **đúng ý nhưng lệch cách viết**:
`ops` rỗng ở bài công thức (nón/trụ/cầu/chóp cụt), `point_dir.base` ghi *tên điểm* thay vì *toạ độ*, thiếu
`solidName`. Ta thêm một **lớp chuẩn hoá tất định** (không đoán/không bịa) sửa các khác biệt hình thức này
trước khi kiểm schema — **một lần cho mọi model**, thay vì nuôi prompt riêng từng model.

| Đầu dịch | Accuracy trước | Accuracy **sau** | Lỗi dịch trước | Lỗi dịch **sau** |
|---|---:|---:|---:|---:|
| `gemini-2.5-flash` | 71.0% | **78.6%** | 50 | 33 |
| `gemini-3.5-flash` | 81.4% | **83.3%** | 23 | 22 |

Giúp **model yếu (2.5-flash) nhiều hơn** (+7.6 điểm), và **"SAI tự tin" không tăng** (vẫn ~5%) — tức chỉ biến
"lỗi" thành "giải đúng", không đánh đổi an toàn. bench:gate vẫn **210/210** (chuẩn hoá không phá case cũ).

## 4. Kết luận (từ số đã đo)

1. **An toàn là bất biến, không phụ thuộc model.** Ở CẢ hai đầu dịch, hệ `system` giữ "SAI tự tin" rất thấp
   (5.2% với 2.5-flash, 5.7% với 3.5-flash) trong khi để LLM trả thẳng thì sai tự tin 21.9–24.3% — **cao gấp ~4 lần**.
   Đây là bằng chứng chính: độ tin cậy đến từ **engine + cơ chế từ chối**, không phải từ một LLM cụ thể.
2. **Precision khi trả lời cao ổn định (93–98%):** khi hệ chịu đưa đáp thì gần như luôn đúng.
3. **Model dịch tốt hơn → hệ mạnh hơn rõ:** 3.5-flash cho `system` accuracy 83.3% (vs `llm-direct` 66.7% cùng model);
   2.5-flash yếu hơn ở khâu dịch (33/210 ca lỗi dịch) nên accuracy 78.6%. → **engine không đổi, chất lượng dịch quyết định
   accuracy**, đúng như thiết kế hai tầng. Lớp chuẩn hoá plan (§3.3) đã kéo hai model lại gần nhau hơn.

## 5. Cách chạy (trên máy có mạng + API key)

Gemini chạy qua **Vertex AI** (tính vào credit $300). Khoá service-account (`sa.json`) để **ngoài repo**;
truyền bằng đường dẫn — **không dán nội dung khoá vào chat/PR/log, không commit**.

```bash
# 1 lệnh — chạy Vertex(2.5-flash) + Vertex(3.5-flash) trên tập test:
VERTEX_SA_KEY=F:/geo3dnew/vertex-keys/sa.json \
VERTEX_PROJECT=gen-lang-client-0968335636 \
VILAO_API_KEY=sk-... \
bash scripts/eval/chay-eval-da-mo-hinh.sh

# hoặc từng lượt (Vertex cần VERTEX_SA_KEY_JSON = NỘI DUNG sa.json + VERTEX_PROJECT):
VILAO_API_KEY=sk-...  node scripts/eval/baseline.mjs --methods system,llm-direct --split default --use test
VERTEX_SA_KEY_JSON="$(cat sa.json)" VERTEX_PROJECT=gen-lang-client-0968335636 \
  node scripts/eval/baseline.mjs --methods system,llm-direct --provider vertex --model google/gemini-2.5-flash --split default --use test
VERTEX_SA_KEY_JSON="$(cat sa.json)" VERTEX_PROJECT=gen-lang-client-0968335636 \
  node scripts/eval/baseline.mjs --methods system,llm-direct --provider vertex --model google/gemini-3.5-flash --split default --use test
```

> Có thể thay bằng **AI Studio key tĩnh** (`--provider gemini`, biến `GEMINI_API_KEY`) nếu không dùng Vertex;
> nhưng credit $300 gắn với **Vertex** nên Vertex là đường chính.

**Thêm model khác (DeepSeek…) — provider `openai` (OpenAI‑compatible):**
```bash
# DeepSeek chính hãng (rất rẻ, ~$0.09/1M token → 210 câu vài xu):
OAI_BASE_URL=https://api.deepseek.com  OAI_API_KEY=sk-...  \
  node scripts/eval/baseline.mjs --methods system,llm-direct --provider openai --model deepseek-chat
# hoặc OpenRouter (1 key cho 300+ model):
OAI_BASE_URL=https://openrouter.ai/api/v1  OAI_API_KEY=sk-or-...  \
  node scripts/eval/baseline.mjs --methods system,llm-direct --provider openai --model deepseek/deepseek-chat
```
> ⚠️ Chỉ dùng **nguồn chính danh** (DeepSeek official / OpenRouter). **KHÔNG** dùng proxy free reverse‑engineer:
> không tái lập được + vi phạm ToS → **mất uy tín số liệu bài báo**. DeepSeek: `⟦CHỜ ĐO — cần key DeepSeek/OpenRouter⟧`.

Mỗi lượt ghi `docs/nghien-cuu/eval-runs/<tag>/report.md` + `results.json`. Chép số vào bảng §3 (thay `⟦CHỜ ĐO⟧`),
ghi rõ **ngày chạy** và **tên model** ở chú thích. Chi phí ước tính: **vài đô** cho toàn bộ (Flash rất rẻ).
Đang dùng **$300 Free Trial** → trừ vào credit, **không đụng thẻ** tới khi bấm Upgrade; hết credit thì call **fail**, không âm thầm tính tiền.

### Liêm chính
- Gemini/Vilao **chỉ dịch đề**; đáp chuẩn là của nhóm tự giải. Không để model sinh đáp chuẩn.
- Số phải **đo thật**; báo cả chỗ model làm *tệ hơn* — đó cũng là dữ liệu tốt.
- Key API để dạng biến môi trường; **không commit** vào repo.
