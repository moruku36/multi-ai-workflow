# 更新履歴

[English](CHANGELOG.md) | [日本語](CHANGELOG.ja.md)

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
