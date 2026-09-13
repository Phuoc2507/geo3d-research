#!/usr/bin/env bash
# Chạy EVAL SO SÁNH ĐA MÔ HÌNH trên MÁY BẠN (web/CI chặn mạng ra Vilao/Google).
# Cùng một tập đề TEST (đã giữ riêng), thay "đầu dịch" LLM khác nhau → các dòng cho bảng so sánh.
# Đầu dịch chính: GEMINI QUA VERTEX (tính vào credit $300 của Google Cloud).
#
# Chuẩn bị 1 lần:
#   • sa.json (khoá service-account) để NGOÀI repo, vd F:/geo3dnew/vertex-keys/sa.json
#   • Bật "Vertex AI API" trên project và cấp role aiplatform.user cho service-account.
#
# Chạy (PowerShell / Git-Bash trên Windows, hoặc bash):
#   VERTEX_SA_KEY=F:/geo3dnew/vertex-keys/sa.json \
#   VERTEX_PROJECT=gen-lang-client-0968335636 \
#   VILAO_API_KEY=sk-... \
#   bash scripts/eval/chay-eval-da-mo-hinh.sh
#
# Kết quả: mỗi lượt ghi docs/nghien-cuu/eval-runs/<tag>/report.md → chép số vào
#   docs/nghien-cuu/so-sanh-da-mo-hinh.md (chỗ ⟦CHỜ ĐO⟧).
set -u

# ---- Nạp khoá Vertex: VERTEX_SA_KEY (đường dẫn file) -> VERTEX_SA_KEY_JSON (nội dung) ----
if [ -z "${VERTEX_SA_KEY_JSON:-}" ] && [ -n "${VERTEX_SA_KEY:-}" ] && [ -f "${VERTEX_SA_KEY}" ]; then
  export VERTEX_SA_KEY_JSON="$(cat "${VERTEX_SA_KEY}")"
fi
export VERTEX_PROJECT="${VERTEX_PROJECT:-gen-lang-client-0968335636}"
export VERTEX_LOCATION="${VERTEX_LOCATION:-global}"

# Model Vertex (tiền tố google/). Bản đã kiểm chạy được: google/gemini-3.5-flash, google/gemini-2.5-flash.
VERTEX_FLASH="${VERTEX_FLASH:-google/gemini-2.5-flash}"
VERTEX_FLAGSHIP="${VERTEX_FLAGSHIP:-google/gemini-3.5-flash}"

SPLIT_ARGS="${SPLIT_ARGS:---split default --use test}"   # tập TEST giữ riêng (công bằng). ="" = toàn bộ golden.
METHODS="${METHODS:-system,llm-direct}"

run() {  # $1=provider  $2=model(rỗng=mặc định)  $3=nhãn
  local provider="$1" model="$2" label="$3"
  echo ""
  echo "==================== $label ===================="
  if [ -n "$model" ]; then
    node scripts/eval/baseline.mjs --methods "$METHODS" --provider "$provider" --model "$model" $SPLIT_ARGS
  else
    node scripts/eval/baseline.mjs --methods "$METHODS" --provider "$provider" $SPLIT_ARGS
  fi
}

node scripts/build-kernel.mjs >/dev/null 2>&1 || npm run build:kernel

# 1) Vilao (hiện tại) — cần VILAO_API_KEY
if [ -n "${VILAO_API_KEY:-}" ]; then run vilao "" "Vilao (gemini-3.5-flash-low, hiện tại)"; else echo "⚠ Bỏ qua Vilao: chưa đặt VILAO_API_KEY"; fi

# 2) + 3) Gemini qua VERTEX — cần VERTEX_SA_KEY_JSON + VERTEX_PROJECT
if [ -n "${VERTEX_SA_KEY_JSON:-}" ] || [ -n "${VERTEX_ACCESS_TOKEN:-}" ]; then
  run vertex "$VERTEX_FLASH"    "Vertex Flash ($VERTEX_FLASH)"
  run vertex "$VERTEX_FLAGSHIP" "Vertex Flagship ($VERTEX_FLAGSHIP)"
else
  echo "⚠ Bỏ qua Vertex: chưa nạp khoá. Đặt VERTEX_SA_KEY=<đường dẫn sa.json> (hoặc VERTEX_SA_KEY_JSON=<nội dung>)."
fi

# 4) (tuỳ chọn) DeepSeek / nguồn OpenAI-compat khác — cần OAI_BASE_URL + OAI_API_KEY + OAI_MODEL.
#    DeepSeek chính hãng: OAI_BASE_URL=https://api.deepseek.com  OAI_MODEL=deepseek-chat
#    OpenRouter:          OAI_BASE_URL=https://openrouter.ai/api/v1  OAI_MODEL=deepseek/deepseek-chat
#    (Dùng nguồn CHÍNH DANH, tái lập được — KHÔNG proxy lậu.)
if [ -n "${OAI_API_KEY:-}" ] && [ -n "${OAI_BASE_URL:-}" ]; then
  run openai "${OAI_MODEL:-}" "DeepSeek/OpenAI-compat (${OAI_MODEL:-deepseek-chat})"
fi

echo ""
echo "Xong. Số nằm ở docs/nghien-cuu/eval-runs/<tag>/report.md — chép vào so-sanh-da-mo-hinh.md."
