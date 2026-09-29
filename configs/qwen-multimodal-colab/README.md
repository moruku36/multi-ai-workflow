# Qwen Multimodal Colab

現在の個人用Qwen環境は、別リポジトリの **[moruku36/qwen-multimodal-colab](https://github.com/moruku36/qwen-multimodal-colab)** で管理します。

このディレクトリは、Multi-AI Workflowの中での**役割と使い分け**だけを記載します。実装・起動手順・モデル設定は本体リポジトリを参照してください。

## 現在の構成

推奨構成:

- Google Colab
- **A100 80GB** 推奨
- Chat / Vision: **Qwen3.8-27B Q8_K_L** via llama.cpp
- 画像生成・編集: **Qwen-Image-2.1**
- UI: Gradio
- 履歴・生成画像: Google Driveへ保存可能

L4も選択可能ですが、GPUメモリや画像解像度に制約があります。

## Multi-AI Workflowでの役割

Qwen Multimodal Colabは、**個人用のマルチモーダル実験・調査環境**として扱います。

向いている用途:

- 普通のChat / Vision
- 画像を見せて質問
- 画像生成・画像編集
- PDFの読解
- 短い動画の読解
- 音声入力・読み上げ
- Web検索を使った調査
- GitHub URLを渡したRead-onlyリポジトリ調査
- ChatGPT / Claude / Geminiとは別系列のセカンドオピニオン

## 他ツールとの使い分け

| 用途 | 第一候補 |
|---|---|
| 要件整理・文章・資料 | ChatGPT |
| PoC・コードの大量初期実装 | Gemini 3.8 Flash + Antigravity |
| 通常のコード実装 | Codex GPT-6 Luna |
| 難しい実装 | Codex GPT-6 Sol / Claude Opus 5.5 |
| 独立コードレビュー | Claude Opus 5.5 |
| 画像・PDF・動画・音声・Qwen実験 | **Qwen Multimodal Colab** |

## セキュリティ上の注意

これは**ローカルLLMではありません**。

Google Colab / Google Driveを利用し、設定によってはTavily / Brave Search / TTS等の外部サービスも利用します。そのため、以前のOllama環境のような「PC内だけで完結する機密処理基盤」としては扱いません。

- APIキーやパスワードはNotebookへ直接書かず、Colab Secretsを利用する
- 機密情報・社外秘データは、組織や各サービスの利用ルールに従って投入可否を判断する
- 共有URLを使う場合は認証を有効にする

## 本体

- Repository: https://github.com/moruku36/qwen-multimodal-colab
- Colab Notebook: https://colab.research.google.com/github/moruku36/qwen-multimodal-colab/blob/main/Qwen-Multimodal-Colab.ipynb

モデル構成やVRAM測定値、最新の制限事項は本体リポジトリのREADME / TECHNICAL.mdを正とします。
