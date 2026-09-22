# Tools: ローカル加工 + Claude独立レビュー CLI

`pipeline.py` は、Ollamaによるローカル前処理とClaude APIによる独立レビューを直結する補助CLIです。

日常の開発フローは ChatGPT / Antigravity / Codex / Claude Code を直接使うことを前提としており、このCLIは**機密データをローカルで整形してからレビューへ渡したい場合**などに使います。

---

## 主な機能

1. **`chain`**: Ollamaで整形した後、Claudeでレビュー
2. **`clean`**: Ollamaのみでローカル整形
3. **`review`**: Claude APIのみでレビュー

Claudeの既定モデルは `claude-opus-5-5` です。必要に応じて `CLAUDE_MODEL` または `--claude-model` で変更してください。

---

## 準備

```bash
export ANTHROPIC_API_KEY="your-api-key"
export CLAUDE_MODEL="claude-opus-5-5"
```

Windows PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="your-api-key"
$env:CLAUDE_MODEL="claude-opus-5-5"
```

---

## 使用例

ローカル整形後にレビュー:

```bash
python tools/pipeline.py meeting_memo.txt
```

ローカル整形のみ:

```bash
python tools/pipeline.py raw_log.txt --mode clean -o clean_log.txt
```

Claudeレビューのみ:

```bash
python tools/pipeline.py proposal.md --mode review -o review_report.md
```

別モデルを指定:

```bash
python tools/pipeline.py proposal.md --mode review --claude-model claude-sonnet-5
```
