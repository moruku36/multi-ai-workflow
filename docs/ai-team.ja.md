# AIチームの役割と運用

[English](ai-team.md) | [日本語](ai-team.ja.md)

> 2026-10-05時点の運用。モデル名は本人の運用上の表記です。

| 担当 | ツール／役割 | 主な責務 |
|---|---|---|
| Owner | 人間 / Product Owner | 目標、優先順位、受け入れ判断 |
| Dottie | OpenAI Dots / PM | タスク定義、providerと環境選択、進捗、受け入れ、handoff |
| Chappy | ChatGPT + Codex | アーキテクチャ、レビュー、調査、文章、割り当てられたrepo作業 |
| Claude | Claude Code | 通常の実装・deploy担当。通常Sonnet 5.5、難しい作業はOpus 5.5 |
| Gemini | Gemini + Antigravity | PoC、mock、適合する実装。固定の優先経路ではない |
| Qwen | Open WebUI/Ollama、別のColab構成 | ローカル文章処理とマルチモーダル調査 |

## Windowsを基盤にした運用

Windowsを常時稼働のローカル基地かつ第一選択とします。Windowsで作業を続けられない場合、Macへ切り替える前にユーザーへ相談します。Macは補助環境です。CodexBarのquota画像は手動で確認します。quotaの自動取得や完全自動routingは未検証です。

## 役割の境界

- DottieがPMとしてscope、provider／環境選択、進捗、受け入れを調整します。すべての実行が自動とは限りません。
- AI Engineering Factoryは再利用可能な薄いhandoff、artifact、evidence層です。minimal handoffは[PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29)で検証済みです。
- AIteamBridgeはcapacity、router、transportを扱う別のローカル開発プロジェクトです。live quota取得と自動dispatchは未検証です。

これらは補完関係にあり、完全自律型の重複orchestratorではありません。状態はverified/merged、local/offline、runtime pending、proposalに分けます。

## 実行状況

監督付きAntigravity Webセッション1件でタスク依頼と応答が確認され、取得結果にはunit check 324件、mock browser check 25件が報告されました。これは単一結果であり、CLI稼働、一般的な自動routing、独立したテスト再実行を示すものではありません。

QwenのWindowsローカル文章応答は本人操作で確認済みです。Colabの[PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35)はCPU CI 287件（2件skip）を報告し、Colab/GPU inferenceとモデルdownloadは実行していません。A100での品質、速度、VRAM、計算使用量は延期中です。RunPodの起動、HTTP接続、自動終了は目標設計であり、未検証です。

ユーザー承認、実行環境の権限承認、ローカルテスト、稼働環境への反映は別段階です。正規の承認が拒否されたら作業を保存して止め、再承認を連打したり別経路で迂回したりしません。
