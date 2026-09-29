# Legacy: Ollama / Qwen (+ Open WebUI)

> **この構成は現在の通常運用では使用していません。**
>
> 現在の個人用Qwen環境は [qwen-multimodal-colab](https://github.com/moruku36/qwen-multimodal-colab) へ移行しています。

このディレクトリは、過去にローカルPC上でOllama / Qwen / Open WebUIを使っていた構成を再現できるよう、**Legacy資料としてのみ保持**しています。

現在の標準ルーティングやREADMEでは、このローカルLLMを前提にしません。

## 現行環境との違い

| 項目 | Legacy Ollama | 現行 Qwen Multimodal Colab |
|---|---|---|
| 実行場所 | ローカルPC | Google Colab |
| 主モデル | Qwen 2.5系 | Qwen3.8-27B Q8_K_L |
| UI | Open WebUI | Gradio |
| Vision | 構成依存 | 対応 |
| 画像生成・編集 | なし | Qwen-Image-2.1 |
| PDF / 短動画 | なし | 対応 |
| 音声入力 | なし | 対応 |
| GitHub調査 | なし | Read-only agent対応 |
| 機密性 | ローカル完結可能 | Colab / Drive / 外部検索利用を前提に個別判断 |

旧スクリプト（`Modelfile`, `run.sh`, `run.ps1` など）は互換性・履歴のため残しています。
