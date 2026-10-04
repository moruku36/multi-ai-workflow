# Antigravity / Gemini タスク指針

[English](AGY_RULES.md) | [日本語](AGY_RULES.ja.md)

これはタスク指針であり、全体共通のモデル・effort既定ではありません。モデル名は本人の運用上の表記です。指定名から実行時モデルやCLI IDを断定しません。

## タスクごとの選択

- PoC、mock、探索、範囲を限定した実装など、機能と環境が合う場合にAntigravity/Geminiを使います。
- 難度、品質、環境、最新のcapacity根拠、コストからモデルとeffortを選びます。タスク固有の明示指定は尊重しますが、全体既定にはしません。
- Antigravity GeminiとAntigravity Claude/GPTは別poolです。native Gemini/Claude/Codexのpoolとも別で、API課金はsubscription quotaと異なります。
- 直接Claude CodeとAntigravity内Claudeは別のcapacity poolです。
- GeminiでPoCをしてClaudeで仕上げる経路は任意です。既存実装を維持・改善し、重複した初期実装を避けます。

## 境界

- 指定モデルと実行時に観測されたモデルを分け、証拠がなければ`unknown`とします。
- CodexBar quota画像は手動確認です。自動取得・routingは未検証で、古い観測は`unknown`です。
- Web依頼のacceptedやWorking表示は、実装、テスト、完了、自動連携を証明しません。
- ユーザー承認、実行環境の権限、ローカルテスト、live deployを別段階として記録します。正規の承認が拒否されたら保存して止めます。

[Routing Guide](../../docs/routing-guide.ja.md)、[運用判断](../../docs/operating-decisions-2026-10-05.ja.md)、[handoffテンプレート](../../docs/handoff-templates.ja.md)を参照してください。
