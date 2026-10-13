# PR Review Pipeline 運用更新 — 2026-10-13

[English](operating-decisions-2026-10-13.md) | [日本語](operating-decisions-2026-10-13.ja.md)

更新日：2026-10-13（Asia/Tokyo）。[2026-10-10の配分方針](operating-decisions-2026-10-10.ja.md)を維持し、コードPRのレビューに限り以下を追加します。過去の観測・記録は変更しません。

- **Codex Review**：Claude/Gemini実装への範囲を限定した独立レビュー。Codex実装時はClaude/Geminiを選び、同じproviderによる自己レビューと区別。
- **PR Review Pipeline**：PR head固定 → 別AIレビューとCI → 指摘確認・最小修正 → 新headで再確認 → リスクと権限に応じたマージ。
- **証拠と受入**：reviewer/provider、SHA、試験・指摘・不足を記録。未知や未完了を合格扱いにしない。
- **リスク区分**：低リスク自動マージは将来の条件付き案。中・高リスクは人が受入。自動化設定・必須チェック・保護設定は別途実証。
- **Qwen**：RunPod A100独立レビューは未受入の将来候補のまま。GPU起動・モデル選定・品質受入をこの改訂から推定しない。
- **文書整合**：日英README、役割表、routing、handoff、repo保守手順、更新履歴、レビュー規則・PRテンプレートを更新。

[詳細設計](pr-review-pipeline.ja.md)と[更新履歴](../CHANGELOG.ja.md)を参照。確認したのは文書・テンプレートであり、live Codex Review、CI強制、別provider評価、自動マージの稼働完了ではありません。
