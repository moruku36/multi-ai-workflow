# Tools: 自動化パイプライン CLI (`pipeline.py`)

Layer 1（Ollamaによるローカル高速加工）と Layer 4（Claude APIによる批判的レビュー）を、コマンドライン1発で直結する簡易オーケストレーションツールです。  
Python標準ライブラリのみで動作するため、追加の `pip install` は不要です。

---

## 主な機能

1. **`chain` モード（デフォルト）**:
   入力テキスト（生データや議事録）を **Layer 1 で整形・ノイズ除去** した後、その結果を自動で **Layer 4 に渡してリスク検証** します。
2. **`clean` モード**:
   社外秘データや大量ログをローカルの Ollama（`qwen-processor`）のみで整形・抽出します（外部通信ゼロ）。
3. **`review` モード**:
   指定テキストを Claude API に送信し、辛口の監査レビュー結果を取得します。

---

## 使い方

### 1. 準備
```bash
# Claude APIキーを設定（review または chain モードで使用）
export ANTHROPIC_API_KEY="your-api-key"
# Windows PowerShell の場合: $env:ANTHROPIC_API_KEY="your-api-key"
```

### 2. コマンド実行例

**手元の議事録を自動成形してリスクチェックする:**
```bash
python tools/pipeline.py meeting_memo.txt
```

**パイプライン処理（PowerShell / Bash）:**
```powershell
Get-Content raw_log.txt | python tools/pipeline.py --mode clean -o clean_log.json
```

**レビュー結果をファイルに保存する:**
```bash
python tools/pipeline.py proposal.md --mode review -o review_report.md
```