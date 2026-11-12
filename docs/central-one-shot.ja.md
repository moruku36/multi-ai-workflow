# 署名付き・対象1件の中央レビュー — 無効のソース草案

[English](central-one-shot.md)

## 観測状態 — 2026-11-12

| 層 | 状態 |
| --- | --- |
| 承認署名・launcher来歴・共通target処理・送信上限 | 草案実装と静的レビューまで。動作未検証 |
| オフライン検証 | tests/check_one_shot_integration.pyに5件作成。未実行 |
| 信頼鍵の設定 | checked-in一覧は空。運用鍵の生成・登録なし |
| workflow配備・実対象受入・定期有効化 | 未実施 |
| 独立2系統コードレビュー・所有者merge | この草案では未完了 |

これは製品コードであり、OpenClawの実行権限変更ではありません。ホストの承認binding障害を直すものでも、既消費の試験・呼出し枠を再開するものでもありません。署名検証、終了、Check成功、ソース保存をレビュー品質・独立provider受入・送達・merge権限と混同しません。

## 1. 所有者側の承認証拠

tools/central_one_shot_auth.pyは固定/usr/bin/openssl（OpenSSL 3必須）でEd25519分離署名を検証します。署名発行・秘密鍵読込みは実装しません。信頼公開鍵はtrusted controller checkoutのconfig/central-one-shot-trust.jsonだけから取得し、空一覧なら停止します。

envelopeはキーをsortし、ensure_ascii、空白なし、末尾改行なしの厳密なcanonical ASCII JSONです。fieldはpayloadとsignatureのみ。signatureは64bytesの標準base64正規表現です。

署名対象はbyte列のcentral-review-hub NUL one-shot NUL v1 NULとcanonical(payload)の連結です。payloadのfieldは次の集合に限定します。

- schema_versionは整数1、domainはcentral-review-hub/one-shot/v1。
- issuer／key_idは公開してよい小文字identifier、1〜64文字。
- authorizationはkind=one_target_dual_review、targets=1、reruns=false、refunds=falseのみ。整数・bool型も厳密検査。
- repository／pr／base／head／controller_revisionは所有者の適格な対象1件。hub除外、SHAは固定40文字小文字。
- eligible_since／expires_atは秒単位UTC。正の有効窓は最大1時間、現在時刻はその内側。
- lane_attempt_limitsはAlibaba1〜8、Cloudflare1。

envelope上限8192bytes。重複・余分fieldや非有限数を拒否し、payload改変は署名を無効化します。digest・manifest bool・request内の鍵・注入callbackは権限ではありません。

trust policyはschema_version=1とkeysのみ、最大16件の一意な(issuer,key_id)。各keyはissuer／key_id／algorithm=Ed25519／public_key（32raw bytesの正規base64）です。policy変更には独立レビューと既存の人のmerge gateを適用します。秘密鍵はrepo・workflowの外に保持します。外部署名主体・鍵管理の設定は管理側の配備前提で、この作業では行っていません。

controller_revisionは固定system Git・制限環境でcleanな実HEADから独立取得し、署名値とGitHub claimへ照合します。policy変更後のreviewed mainの実revisionに署名し、feature branchや過去mainへの署名を転用しません。

## 2. trustedな直列launcherと共通処理

本番入口は固定hubのmain上の.github/workflows/central-review-hub.ymlだけです。既存workflow全体のconcurrency group central-review-hub／cancel-in-progress=falseを維持し、同じjobのworkflow_dispatch input one_shot_envelopeで対象1件を受け取ります。別launcher・別lock・ローカル有料command・定期enabled書換え・新schedulerは作りません。定期フラグの既定無効は維持します。

tools/central_one_shot_provenance.pyはGitHubのTLS経由JWKS証明書とOpenSSLでOIDC JWTのRS256署名を検証し、issuer／audience／repo・owner／main ref／workflow path／source・workflow revision／hosted runner／event／run claimを照合します。単発audienceはenvelopeそのもののSHA256を含み、定期は別audienceです。単発run_attempt=1必須で旧job再実行を承認経路にしません。環境変数はrunner capabilityの所在と認証済みclaimとの比較にしか使わず、GITHUB_ACTIONS=trueだけでは許可しません。

配備ではGitHub TLS/JWKS・OIDC発行・hosted runner隔離・reviewed mainの排他契約を信頼します。runner capabilityや所有者秘密鍵の窃取、trusted mainの支配に対する防御ではありません。claim／証明書schema／OpenSSL／custom OIDC subject／runner service host契約が合わなければfallbackせず停止します。job-level id-token:write追加も、レビュー・配備前のソース変更のみです。実GitHubのclaim／host互換性は実run未受入です。JWT・capability・raw署名は公開しません。

Hub.prepare_one_shotはpreflight前に署名とlauncherを認証。Hub.run_one_shotは署名対象1件だけを_run_targetsへ渡し、他repoを探索しません。定期も同じ_run_targetsを共有します。

1. current対象・完全ledger・dedup・既存日次/run上限を検査。
2. global予約を消費しreadback。ACK不明なら再試行せず停止。
3. target予約を再検査し、receiptを作成・readback。
4. 対象コードを実行せず固定sourceを取得。
5. 各lane前にcurrent／同UTC日／期限を検査しunknownを永続記録。
6. stale・品質・人のmerge gateを保ち、安全な結果を保存。

unknown予約は返却しません。単発対象の不適格・stale・既予約は、何もせず成功とせず停止します。旧validate_one_shotは既存offline用の読取り専用proposal検査として残しますが、本番有料権限には使いません。GitHub concurrencyではpending runが置換されることがあり、dispatch応答は実行受領ではありません。待機中に期限が切れても自動延長しません。

## 3. HTTP試行とpayload上限

署名されたcapをHub→real_lane→child worker→Alibaba relay／Cloudflare senderへ渡します。有効capは既存lane上限を超えません。実送信前にserialized bytesを予約し、失敗分も消費して返却しません。Cloudflare要求上限196608bytes、source／diff／snapshot上限65536、Alibaba既存累積枠は維持します。いずれも金額上限ではありません。

署名UTC期限を予約・lane前に再検査し、monotonic deadlineへ変換して各実HTTP直前でも検査し、worker生存時間も制限します。送信済み応答は結果不明になる可能性があり、期限切れでも返却・再送許可にはなりません。生成後byte検査をprovider側token／金額上限とは呼びません。

## 残る検証

作成した5件は、実ローカルEd25519検証／改変／空鍵、launcher claim検査と環境自己申告拒否、共通ledger順序／replay／cap伝播、予約ACK不明、実senderの回数／失敗計上／期限です。全件未実行。ローカルAPI・transport fixtureは実GitHub OIDC・provider受入ではありません。実JWKS/JWT互換性・排他・認証workflow実行は基盤修復後の別の限定受入が必要です。以前の7件枠を勝手に消費・リセットしません。

大容量sourceの初回独立レビュー経路とサイズ方針は別の未解決条件です。草案公開のためだけに既知のoversized有料自動レビューを起動しません。有効化・鍵登録・workflow dispatch・有料実review・merge・本番設定変更は含みません。
