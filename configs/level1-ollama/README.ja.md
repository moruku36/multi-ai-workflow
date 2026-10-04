# Legacy: Ollama / Qwen (+ Open WebUI)

[English](README.md) | [日本語](README.ja.md)

このフォルダは以前のローカル構成を保持します。自動orchestration一式ではありません。

## ローカルでの確認

- WindowsのOpen WebUI/Ollama経由で文章応答を本人操作により確認しました。
- MacのOpen WebUI 0.11.4と小型のローカルQwen2.5 3Bでローカル応答およびWeb検索結果を確認しました。
- これらは全scriptの現役利用、quota routing、自動orchestrationを意味しません。
- 固定Q8のColab notebookは別環境でマルチモーダル構成を保持します。Colab機能をローカルQwenの機能と混同しません。

`Modelfile`、`run.sh`、`run.ps1`、`start-webui.bat`は旧式／参考用です。利用前に実ファイルと環境を確認してください。

## 実行環境の区別

| 項目 | ローカルOpen WebUI/Ollama | Qwen Multimodal Colab |
|---|---|---|
| 実行環境 | WindowsまたはMac | Google Colab notebook |
| 確認状態 | 本人操作の文章応答。Macはローカル3B応答とWeb検索 | [PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35)のCPU CI 287件（2 skip）。GPU inference／モデル取得なし |
| 自動化 | 未確認 | notebook検証から自動化を推定しない |

[Routing Guide](../../docs/routing-guide.ja.md)と[運用判断記録](../../docs/operating-decisions-2026-10-05.ja.md)を参照してください。

Colab notebook固有の画像、PDF、audio、video機能はローカル環境へあるものと推定しません。PR #35で確認されたのはCPU CI 287件（2件skip）であり、GPU inferenceもモデルdownloadも実行されていません。notebookの検証から自動化を推定しません。
