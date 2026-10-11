# AI Team Operating Decisions - 2026-10-02

[English](operating-decisions-2026-10-02.md) | [Japanese](operating-decisions-2026-10-02.ja.md)

> **Legacy（当時の記録）:** モデル選定は[2026-10-06の本人最新方針](operating-decisions-2026-10-06.ja.md)で更新されました。以下の当時の段階選定・実験・観測は履歴として保持し、現行の推奨にはしません。

この日付付き記録は2026-10-02時点の方針です。CLI観測は当時の本人セッションから報告されたもので、この文書更新では再実行していません。方針の承認、コマンド受付、実行、検証は別の事実です。[2026-10-05の後続方針](operating-decisions-2026-10-05.ja.md)が後続のroutingを更新しています。

## 役割とモデル選択

| 役割 | 責任 |
|---|---|
| Dottie | PM／orchestrator: 範囲、割当、handoff、quota認識、根拠管理 |
| Chappy | Architect／独立reviewer。OpenAIの調査・文章、明示指定されたCodex作業 |
| Claude | 当時のコーディング／deploy担当。通常Sonnet、deployには該当承認が必要 |
| Gemini / Antigravity | PoC、モック、初期実装の候補。同じartifactをClaudeへ渡す当時の運用 |
| Qwen | マルチモーダル作業。ローカル文章環境とColab機能を区別 |

当時の通常Codex文章／コーディングはLuna / Lowから開始し、必要に応じLuna Medium、Luna High、Sol Mediumへ進める方針でした。これはCodex作業に適用され、すべてのコーディングをCodexへ割り当てる指示ではありません。本人の明示指定を優先し、既存実装を再利用します。

蒸留とAI Governance Controlの初期調査では、本人が論文解釈へのAstra利用を明示的に許可していました。十分ならSolを使います。この例外は全タスクのAstra標準化を意味しません。Claudeは通常Sonnet、Opusは難しい作業に使います。版付きモデル名は本人申告のスナップショットであり、実行時モデルやAPI IDの証明ではありません。

当時、Gemini effort方針と本人の希望に差がありました。既存文書は通常High、quotaが少ない場合はリセット時刻と難度を考慮してMediumとし、本人はその作業でMediumを希望していました。この記録は当時の状況です。現行routingは2026-10-05のタスク別方針に従い、指定effortと実行時観測を別々に記録します。

## 比較と根拠の契約

モデル比較の前に、同一の入力artifact、prompt、受入条件、rubric、制約、評価手順を固定します。比較runの前にmanifestを作り、条件が変わった場合は別の比較として記録します。

```text
task_id / comparison_id:
input_revision / paths / content_hashes:
prompt_revision / rubric_revision / acceptance_criteria:
provider / route / CLI_version / environment:
requested_model / requested_effort:
observed_runtime_model / observed_runtime_effort: 根拠がなければ UNKNOWN
accepted: status / receipt_reference
executed: status / run_reference
verified: status / check_reference
output_paths / content_hashes:
review_findings / verification_results / unresolved_items:
reacquire_source / revision_or_hash:
```

要求モデル／effortは実行時の証明ではありません。根拠がなければ`UNKNOWN`とします。`accepted`、`executed`、`verified`を分け、queue receiptは受付だけを示すものとします。結果を読み、受入条件を検証してから完了を報告します。公開するmanifestと証跡参照はsanitizedにします。

## 当時報告されたCLI検証

| 経路 | 報告された根拠 | その根拠だけでは確認できないこと |
|---|---|---|
| Claude、既存Mac cloud session | CLI実送信を確認 | Windows経路 |
| Claude、Windows 2.1.287 | syntax対応、local Sonnet no-tool OK test | Windows cloud sessionへの実送信。queue receiptは結果の読取ではない |
| Antigravity、Windows 1.2.14 | 要求名`gemini-3.8-flash-medium`を使ったno-tool OK test、headless JSON／timeout／conversation機能 | cloud session経路、要求名からの実行モデル特定、coding/tool実行 |

これらの限定テストはdeploy、repo編集、無人実行、完全自動化を示しません。

## 当時のWindows基盤とAI Governance Control

Windowsは常時稼働ローカル基盤の想定でした。2026-10-02の報告ではWindows wrapper prototype (task7) は14 offline testsに合格しましたが、wrapper経由のlive実行は未テストでした。Antigravity wrapperは呼出単位のtool-scope制御確認待ちでした。これは日付付き観測で一般的な製品制約ではありません。Dottieのcloud PM、CodexBar routing、local agent adapterは統合検証が必要で、完全自動とは表現していませんでした。

当時AI Governance Controlのminimal manifest/review/reacquire方針は実装承認済み、検証未了でした。artifactを再取得できるようsource/revision/hashを保持し、欠落時は記憶から再構成せず再取得・再検証します。実装承認とend-to-end検証を分けます。後続のAI Governance Control根拠は2026-10-05記録を参照してください。

## 公開文書の境界

秘密、認証情報、個人情報、企業メール、私的メモは除外します。この文書作業はinstall、認証／設定変更、課金、自動deployを承認するものではありません。
