# Repository guidance / リポジトリ方針

Keep English/Japanese counterparts aligned and preserve dated historical observations. / 日英を整合させ、過去の観測記録を保持する。

## Code Review Rules

- Flag claims that documentation, mock checks or a single provider response prove live automation or accepted Qwen review quality. State the observed stage and evidence instead. / 文書・mock・単回応答をlive自動化やQwen品質受入の証明とする記述を指摘し、実際の段階と証拠を示す。
- Flag review/merge guidance that accepts stale-head evidence, builder-only review as independent, unresolved blocking findings, or automatic merge without explicit policy and required gates. Require current-head evidence and actual provider separation where available. / 古いheadの証拠、自己レビューの独立扱い、未解決blocking指摘、明示方針・必須ゲートのない自動マージを指摘する。
- Flag private conversations, credentials, quota screenshots or account-specific identifiers in public artifacts. Use generalized examples; a harmless public source URL is not a disclosure issue. / 公開成果物の私的会話・認証情報・quota画像・個別識別子を指摘し、一般化した例へ。安全な公開出典URLは対象外。

See [English](docs/pr-review-pipeline.md) / [日本語](docs/pr-review-pipeline.ja.md) for the review contract. Mechanical link and whitespace checks belong in deterministic verification.
