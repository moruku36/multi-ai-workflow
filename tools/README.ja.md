# ツール: 旧式Ollama + ClaudeレビューCLI

[English](README.md) | [日本語](README.ja.md)

> 旧式の参照実装です。OllamaからClaude APIへ渡すpipelineは現在の通常運用ではありません。

`pipeline.py`はOllamaで草案を作り、Claude APIにレビューを依頼できます。保持されているコードの説明であり、稼働中のorchestrationサービスを意味しません。

## 現在のルーティング

- コード変更は[routing guide](../docs/routing-guide.ja.md)に従ってCodex、Claude Code、Antigravityなどから選びます。
- Windows Open WebUI/Ollamaのローカル文章応答は本人操作で確認済みです。Mac環境での応答確認も、自動orchestrationを証明しません。
- Dottie、Factory、AIteamBridgeはPM、handoff/evidence、local capacity/router/transportで役割が異なります。Bridgeのlive quota取得や自動dispatchは未検証です。
- 必要な場合は実装担当と異なるツールで独立レビューします。

## 旧式CLIモード

1. `chain`: Ollamaで草案を作り、Claude APIへレビューを依頼。
2. `clean`: Ollamaのみで草案作成。
3. `review`: Claude APIのレビューのみ。

歴史的なモデル設定が現在の製品提供状況や運用判断に合うとは限りません。利用前に確認し、API設定からsubscription利用権を推定しないでください。APIキーを作成・課金して使うことは今回の文書更新範囲に含みません。

Ollamaの旧式構成は[設定フォルダ](../configs/level1-ollama/README.ja.md)を参照してください。

このlegacy scriptで指定された過去のreview modelは、現在の提供状況や運用判断に合わない場合があります。利用前に確認し、API設定からsubscriptionの利用資格を推定しないでください。次は既存CLIの例であり、API keyの発行や課金を今回要求するものではありません。

```bash
export ANTHROPIC_API_KEY="your-api-key"
python tools/pipeline.py proposal.md --mode review -o review_report.md
```