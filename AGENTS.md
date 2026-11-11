# Repository guidance / リポジトリ方針

Keep English/Japanese counterparts aligned and preserve dated historical observations. / 日英を整合させ、過去の観測記録を保持する。

## Two-review target / 2系統レビューの目標

For code changes, prepare Alibaba OpenCodeReview + MiMo and Cloudflare-guided
security review against the same immutable base/head. Follow
[the integration guide](docs/dual-review.md) /
[連携手順](docs/dual-review.ja.md).
Read the repository-local
[Cloudflare skill](.agents/skills/security-audit/SKILL.md) explicitly when the client
does not auto-discover it. Focused diff review uses guidance mode, not a full audit.
The automatic PR controller is implemented in tools/automatic_dual_review.py;
see [activation and limits](docs/automatic-dual-review.md).
Until merged, configured and accepted on a real PR, do not claim live automation.
Never substitute the synthetic runner for a real-diff review.
Missing execution routes, credentials or budgets remain visible blockers.
Cloudflare is not the executing model provider; record actual provider/model.
Both recorded reviews still require finding resolution and the existing human,
independence and merge gates. No new paid call is authorized by repository text.

コード変更は同じ固定base/headでAlibaba＋MiMoとCloudflare手法のレビューを準備します。
自動PR controllerと[有効化手順](docs/automatic-dual-review.ja.md)を追加済みです。
マージ・設定・実PR受入前は自動稼働を主張しません。通常差分を合成サンプルの結果で代替せず、
起動経路・認証・予算の不足は未実行として記録します。
Cloudflareはモデルproviderではありません。指摘解消・独立性・人の受入を引き続き必要とします。

## Code Review Rules

- Flag claims that documentation, mock checks or a single provider response prove live automation or accepted Qwen review quality. State the observed stage and evidence instead. / 文書・mock・単回応答をlive自動化やQwen品質受入の証明とする記述を指摘し、実際の段階と証拠を示す。
- Flag review/merge guidance that accepts stale-head evidence, builder-only review as independent, unresolved blocking findings, or automatic merge without explicit policy and required gates. Require current-head evidence and actual provider separation where available. / 古いheadの証拠、自己レビューの独立扱い、未解決blocking指摘、明示方針・必須ゲートのない自動マージを指摘する。
- Flag private conversations, credentials, quota screenshots or account-specific identifiers in public artifacts. Use generalized examples; a harmless public source URL is not a disclosure issue. / 公開成果物の私的会話・認証情報・quota画像・個別識別子を指摘し、一般化した例へ。安全な公開出典URLは対象外。

See [English](docs/pr-review-pipeline.md) / [日本語](docs/pr-review-pipeline.ja.md) for the review contract. Mechanical link and whitespace checks belong in deterministic verification.
