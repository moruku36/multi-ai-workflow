# AI Team Operating Decisions - Japanese - 2026-10-05

[English](operating-decisions-2026-10-05.md) | [Japanese](operating-decisions-2026-10-05.ja.md)

> **Legacy（当時の記録）:** モデル選定は[2026-10-06の本人最新方針](operating-decisions-2026-10-06.ja.md)で更新されました。以下の当時の段階選定・実験・観測は履歴として保持し、現行の推奨にはしません。

GitHubでコードを変更した場合は、影響するREADME、利用方法、設計文書と既存の日英対応ページを更新します。両言語で根拠、検証済み範囲、未確認事項をそろえます。

Public operating guidanceとevidence boundaryを記録します。model labelは本人の運用上の表記であり、API ID、正確な実行時model、特定CLIでの利用可能性を保証しません。非公開のaccount情報、会話、logは記載しません。

## 役割とrouting

| 役割 | 責任 |
|---|---|
| Product Owner | 目標、優先順位、受入、意思決定 |
| Dottie | PM: タスク仕様、provider／環境選択、進捗、受入管理 |
| Chappy | アーキテクトとレビュアー。依頼されたChatGPT/Codex作業も担当可能 |
| Claude Code | 通常のコーディング／デプロイ担当。通常Sonnet 5.5、必要時Opus 5.5 |
| Gemini / Antigravity | PoC／モックや適合する実装タスクの候補。タスクごとに選択 |
| Qwen | ローカル文章処理と別環境のマルチモーダル調査 |

タスク難度、品質、環境、新鮮なquota根拠、消費ペース／リセット時間、費用で選択します。明示的なタスク単位の指定を尊重します。Antigravity-Claude固定優先の規則はありません。

Codexはタスクに適合する場合、または本人が割り当てた場合に使います。effort段階はLuna/Low → Luna/Medium → Luna/High → GPT-6.1 Sol/Low → Sol/Medium → Sol/Highです。ExtraHighは使いません。Astraは通常コーディングtierにはせず、個別に必要性を判断した高度な学術・技術分析に限り、十分ならSolを使います。

## 容量と観測

- Sessionとweeklyのwindowを区別し、異なるwindowの使用量／残量を合算しません。
- 観測時刻と鮮度を記録します。5時間利用が観測されなかっただけでは100%へのリセットを示しません。
- CodexBarのquota画像は手動確認です。quota自動取得と完全自動routingは未検証です。
- Antigravity Gemini、Antigravity Claude/GPT、直接のClaude Code、native Codexの容量poolは別です。API費用はsubscription quotaとは別です。
- 欠落・古い読み取りは`unknown`とし、残高、費用、画像、認証情報、個別アカウント情報を推測・公開しません。

## システム境界と日付付き根拠

- **Dottie**はPM業務を行います。**AI Engineering Factory**は薄い再利用handoff／artifact／evidence層です。minimal handoffは[Factory PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29)（`4fb014a`でmerge）で検証済みで、Ubuntu/Windows品質ゲートとofflineのcontainer-boundary検証を含みます。
- **AIteamBridge**は別個のcapacity/router/transport実装プロジェクトです。報告されている状態はlocal/offline、246 tests、未commit／未publishで、ライブ自律quota取得／dispatchは未検証です。この日付付き状況を変更する際はBridge repoを再確認します。
- これらは補完する役割です。重複する完全自動orchestratorとして説明しません。
- 監督付きAntigravity Webセッション1件でタスク依頼と応答を確認し、取得した結果にはunit check 324件とmock browser check 25件が報告されていました。この単一結果はCLI稼働、一般的な自動routing、テストの独立再実行を証明しません。
- WindowsローカルCLIはAccess deniedとなり、根本原因は不明、利用も未確認です。Web経路とローカルCLI経路は別です。
- Windowsを常時稼働のローカル基地かつ第一選択とします。Windowsで進められない場合はMacへ切り替える前にユーザーへ相談します。
- 固定Q8のColabチャットnotebookは元のマルチモーダル構成を保持します。[Qwen Multimodal Colab PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35)はCPU CI 287件（2件skip）を報告しています。Colab/GPU inferenceとモデルdownloadは実行されていません。A100での品質・速度・VRAM・計算使用量は延期中です。
- [Qwen RunPod Operations PR #1](https://github.com/moruku36/qwen-runpod-operations/pull/1)は文書のみです。最新チャット候補はLinux CPU検証済みで、CUDA、モデルdownload、inferenceはruntime pendingです。
- WebUI → OpenAI-compatible API → オンデマンドRunPod Qwenは目標設計です。Pod起動、HTTP接続、自動終了は未検証です。OpenAI-compatibleはAPI形式を示し、有料OpenAI利用を意味しません。Pod停止と削除は別で、停止後も永続storageに費用がかかる場合があり、削除するとデータを失う可能性があります。

## 根拠の状態

英日両方で次の状態を一貫して使います。

- **verified/merged**: 該当のテストまたは文書／コードのmergeを根拠で確認済み。
- **local/offline**: ライブprovider/runtime経路を証明しないローカル確認。
- **runtime pending**: 目標のライブ／CUDA／download／inference／dispatchが未検証。
- **proposal**: 目標設計または今後の作業で、実装済み動作ではない。

ユーザー承認、実行環境の権限承認、ローカルテスト成功、deploy／runtimeへの反映は別の段階です。承認が拒否されたら作業を保持して正規の経路で止まります。再承認を連打したり拒否を迂回したりしません。

## 公開文書の境界

一般化した運用制約だけを公開します。私的な会話／履歴、個人・家族事情、秘密情報、ログイン先、quota画像、正確な残高／口座情報、非公開ログは含めません。この文書更新にサービス導入、課金、APIキー作成、アプリ実行構成変更は必要ありません。
