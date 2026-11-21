# Sidekick アドバイザリー伝送の確認記録

[English](sidekick-advisory-transport.md) | [日本語](sidekick-advisory-transport.ja.md)

この候補は、公開リポジトリ `moruku36/local-ai-sidekick` の PR 26 に対し、エントリーポイントで固定した base と head で、中立のチェックを1件記録するものです。外部モデルを呼び出さずに伝送を確認します。レビューの実施、受入、マージ権限を示すものではありません。署名付きの2系統レビューと人による判断には、それぞれのゲートがあります。 [ワークフロー](../.github/workflows/sidekick-advisory-transport.yml) · [エントリーポイント](../tools/sidekick_advisory_transport.py)

承認されたワークフローのリビジョンが Hub のデフォルトブランチ `main` に入った後、所有者が初回試行として手動実行できます。`confirmation` には `WRITE ONE NEUTRAL SIDEKICK PR 26 ADVISORY CHECK` を完全一致で入力します。既存の App 設定を使い、Sidekick のみに絞ったプルリクエスト読み取りとチェック書き込みのトークンを発行します。発行範囲、PR の識別情報、固定コミット、現在の `main` 先端が一致した場合にチェックを送信します。

固定した head 上で参照可能なすべてのチェックを、App や状態を問わず走査します。同じ名前または固定の外部 ID を持つチェックがあれば停止します。公開 REST API で `main` の従来のブランチ保護と有効なルールも読み取ります。必須チェック名の衝突、保護情報の読み取り不可、チェック一覧の取得不備があれば、POST 前に停止します。`central-hub-advisory-transport-v1` は必須チェックから外しておきます。事前確認とチェック作成は別々の GitHub 操作のため、最後の確認から POST までに発生する PR や保護設定の変更は排除できません。

POST は1回だけ行い、応答の ID でチェックを読み戻して App、head、チェック名、外部 ID、中立の結論を照合します。送信後に読み戻しを確認できずに終了した場合は、固定 head とエントリーポイントの外部 ID を使い、GitHub の記録を読み取り専用で照合します。応答の消失、タイムアウト、読み戻しの失敗は、直後にチェックが見つからなくても未解決として扱い、再実行や新しい手動実行で書き込みを再送しません。

エントリーポイントは擬似 HTTPS のテスト5件に合格しました。2026年11月21日には、実際の公開 API でも Sidekick の PR、チェック一覧、ブランチ、適用ルールの読み取りを確認しました。インストールトークンの範囲とチェックの実配信は、まだ確認できていません。 [オフラインテスト](../tests/test_sidekick_advisory_transport.py)
