# 観測した応答理由

[English](review-response-reason.md)

2026-11-12: 診断の差分を作成、3件は **未実行**。
隔離実行はメモリ上限設定で停止し、テスト本体は起動していません。
3件・1回の承認は受領済み・未消費です。live復旧は主張しません。
PR54記録: Alibaba `cli_exit_nonzero`、HTTP 2、完了1。
Cloudflare `response_validation`、HTTP 1、完了0、completion tokens 2048。
原因 **UNKNOWN**。トークン数だけで打切りとは判断できません。

任意の `response_reason` は `length_stop`（明示的length終了）、
`model_mismatch`、`malformed_response`（JSON／応答構造）、
`unexpected_tools`（Cloudflare）だけを保持。不明は省略し、生応答・エラー・
認証情報は追加しません。例外を出さない上限付き観測をAlibaba継承検証より前と
Cloudflare検証に追加。validatorと中央hubは変更せず、receipt境界では
`safe_diagnostics` で再投影します。
過去のreceipt／予約、上限・試行数・期限・provider/model・ソース制限・
再試行禁止・信頼／有効化／mergeゲートを維持します。

mockは3件: Cloudflare lengthが1試行で未完了、Alibaba不正応答を拒否しつつ
理由を保持、receipt／中央投影で任意文字列を除去し観測済みコードを保持。
テスト本体・build・ネットワーク・providerは未実行。同一headのレビュー受入も未完了。
追加の一般許可ではなく、制御を強制できる隔離実行が必要です。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/check_review_response_reason.py
```

オフライン成功でもlive復旧の証明にはなりません。予約済みペアは再送しません。
