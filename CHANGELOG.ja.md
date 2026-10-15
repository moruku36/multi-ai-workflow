# 更新履歴

[English](CHANGELOG.md) | [日本語](CHANGELOG.ja.md)

## v2026.10.15-r2 — 2026-10-15（Asia/Tokyo）

- コード・検証・資料／設計書レビューの**今後の標準**をMiMo-V2.6-Pro APIに変更。Flashは軽量レビューの任意検証候補。
- RunPodはGPU・モデル起動などの技術検証専用とし、Qwen/RunPodによる定常レビュー計画を置き換え。
- 重大指摘の独立確認、機密性・費用・レビュー品質の事前評価を必須とする。文書のみ、実行・課金・設定変更なし。

## 2026-10-15（Asia/Tokyo）

- [日付付き運用判断](docs/operating-decisions-2026-10-15.ja.md)を追加。本人選択のGPT/Solで難題が停滞した場合の、Claude Opus 5.5 Mediumへの限定的な最終エスカレーション1回。本人の運用判断であり、Opusが客観的に最良／Solより常に優れるという主張ではない。
- 日英README、役割表、routing guide、handoffテンプレートへ規則を追加（証拠保存、残量・費用確認、指定とruntime観測の分離、承認、現在revisionのレビュー、通常モデルへの復帰）。
- 2026-10-13時点の「Phase 2はmock/offlineのみ」「Codexが最終エスカレーション」を日付付きsnapshotと明記。過去記録は保持。
- OpusによるRunPod Phase 2接続合格は**本人報告**。独立ログ、Pod終了、課金停止は未確認。A100レビュー品質・自動運用は未受入。Mattermostは難題の例示のみ。
- **文書のみ。GPU、モデル、TLS、権限、runtimeの変更なし。**

## 2026-10-14（Asia/Tokyo）

- Gemini 4 Argonの条件付き統合方針を追加。Antigravityで実利用と品質を確認した後、PoC・モックから通常実装・テスト・小規模修正へ担当拡大を検討。
- Claudeの難しい実装、GPT-6/Codexの設計・限定PRレビュー、DottieのPM、Qwenの専門調査と将来レビュー候補（未受入）を維持。
- README・ルーティングを日英で更新し、[導入手順と構成図](docs/gemini-4-argon-rollout.ja.md)を追加。**文書のみ。実行環境の設定変更なし。**

## 2026-10-13（Asia/Tokyo）

### 追加

- Codex Review / PR Review Pipelineの詳細、構成図、担当分離、再現可能な品質ゲート、修正ループ、リスク別マージ方針。
- PRレビュー証拠のhandoff、日英PRテンプレート、repo固有のCodexレビュー規則。
- 日付付きの運用判断記録。

### 更新

- 日英README、チーム役割、routing guide、handoff、repo保守手順を新しいレビュー手順へ統合。
- Codexに範囲限定PRレビューを追加。Codex実装時は別providerを選択。Qwenの未受入状態と通常OpenAI Medium 2択を維持。

### 状態

文書・テンプレートの更新。自動レビュー、scanner、必須CI、保護設定、自動マージのlive設定・検証は含まない。過去の運用判断記録は履歴として保持。

[詳細・構成図](docs/pr-review-pipeline.ja.md) | [運用記録](docs/operating-decisions-2026-10-13.ja.md)
