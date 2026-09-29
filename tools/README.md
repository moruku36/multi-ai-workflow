# Tools: Legacy Ollama + Claude review CLI

> **Legacy:** 現在の標準ワークフローでは、このOllama前処理パイプラインは通常利用していません。
>
> 個人用のQwen環境は [qwen-multimodal-colab](https://github.com/moruku36/qwen-multimodal-colab) へ移行しています。このCLIは過去のローカルOllama構成を再利用したい場合の参考として残しています。

`pipeline.py` は、Ollamaによるローカル前処理とClaude APIによる独立レビューを直結する旧補助CLIです。

## 現在の推奨

- 画像・PDF・短動画・音声・Qwenチャット → **Qwen Multimodal Colab**
- コード実装 → **Codex / Claude Code / Antigravity**
- 独立レビュー → **Claude Code Opus 5.5 / Codex**
- `pipeline.py` → Legacy互換用途のみ

## Legacy CLI

1. `chain`: Ollamaで整形後、Claudeでレビュー
2. `clean`: Ollamaのみでローカル整形
3. `review`: Claude APIのみでレビュー

Claudeの既定モデルは `claude-opus-5-5` です。

```bash
export ANTHROPIC_API_KEY="your-api-key"
python tools/pipeline.py proposal.md --mode review -o review_report.md
```

Ollamaを再利用する場合のみ、旧 `configs/level1-ollama/` を参照してください。
