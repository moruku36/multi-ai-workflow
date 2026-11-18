# リポジトリ対象台帳（P2a）

[English](review-inventory.md) · 設計：[全リポジトリ品質ゲート詳細設計](global-review-design.ja.md)（§4・§5・§6・§9）

> **状態：作成のみ・未実行。hubと未接続・未認証の純粋なshadowモジュール。** 単独・
> オフラインで、ネットワーク通信、hub・workflow・configの変更、有効化は一切ありません。
> facts・owner情報・信頼フラグは呼出し側の申告で認証された強制ではないため、`enforced`は
> 「強制済みと申告」の意味であり、保護済みの証拠ではありません。テストは未実行です。

## 目的

リポジトリごとに台帳エントリを1件残し、対象外・未確認・非公開・fork・archived・他ownerも
見える状態にします。不明・未保護は合格にしません。

## 構成

- `tools/review_inventory.py`：取得済みの記録とfactsに対する純粋関数。
- `tests/check_review_inventory.py`：合成データの10ケース（作成のみ）。

対象外：取得、ページネーション読取り、webhook、Check、protectionのreadback、PR単位のcoverage、
`tools/central_review_hub.py`の変更。

## エントリと分類

項目：`key`、`repository_id`、`full_name`、`owner`、`visibility`、`fork`、`archived`、
`disabled`、`default_branch`、`installation_id`、`consent`、`enrollment`、`protection`、
`coverage_class`、`reasons`、`enforced`、`operator_action`。不明な値は`null`／`unknown`のまま。

| coverage_class | 意味 |
|---|---|
| `eligible` | public・同owner・非fork・稼働中・installation既知 |
| `manual_required` | private・fork・installation無し。人の経路のみ |
| `excluded` | 他owner・hub自身・archived・disabled |
| `unverified` | 記録の不正・重複、またはfactsの不正 |

理由：`invalid_record`、`invalid_facts`、`duplicate_repository_id`、`not_owner_managed`、
`hub_self_excluded`、`archived`、`disabled`、`private_consent_pending`、
`private_unsupported`、`fork_manual_required`、`installation_missing`。
privateはここでは外部送信しません。

Enrollment：`discovered → consent_pending → configured → protection_verified →
acceptance_pending → enforced`、および`degraded`。`enforced`にはeligible、`configured`、
protection確認済みの申告、acceptance `passed`が必要です。段階を飛ばしたfactsは
`invalid_facts`、対象外の進捗主張は`degraded`です。

## 完全性とscope

一覧の完全性と、そこから導出されるowner完全性。`complete`：一覧と記録の整合のみ。
`owner_complete`：導出値で、`complete`かつowner全体の明示的な突合せが成立（理由は
`incomplete_reasons`とは別の`owner_incomplete_reasons`）。`all_enforced`は`owner_complete`・
空でない台帳・全件enforcedが必要です。

次の場合`complete`はfalse：ページネーション打切り／不明（`truncated=None`）、件数が`limit`
に到達、不正な行・facts、不正または対応先の無いfactsキー、ID重複、不正なscope。
`limit`は正のintで、それ以外は`ValueError`です。

`scope`は必須です。`owner`：一覧がownerの全件で、そのページネーション状態が`truncated`。
`owner_ids`／`owner_truncated`はinstallation専用で、ここでは拒否します
（`owner_metadata_not_allowed`）。`installation`：部分集合。呼出し側が`owner_ids`（独立した
owner readerによる、正のintで重複しないlist・tuple・set・frozenset）を渡し、それが一覧の有効なID
と完全に一致（不足・余分・空対非空はすべて不一致）し、かつ`owner_truncated`がリテラルの`False`
（`None`・`True`・`0`は不可）の場合のみowner-completeです。これらが無い綺麗な部分集合は
`complete`でも`owner_complete`ではありません。空の台帳は`all_enforced`になりません。
すべて未認証の申告です。

factsのキーは正の非boolのintのみ。`True`などは決して紐付けません。ID重複：全メンバーを
サニタイズ済みidentity付きで残し、`unverified`固定・非enforcedにします。Identity：`full_name`の
接頭辞は`owner.login`と一致（大小無視）が必須で、他ownerは`not_owner_managed`です。
デフォルトブランチ：空でなく、制御文字なし、250文字以内。

## プライバシー

`public_view()`は既定で名前・repository ID・ID由来のキーを出さず、内容順の`restricted:N`を
付与します。`visibility_trusted=True`（リテラル。信頼できる公開範囲のreadbackという呼出し側の
申告であり、認証情報でも公開の権限でもない）の場合のみ、正しい重複でないpublic行にkey・ID・
名前を出します。private・不明・不正な行と、未解決の重複行はすべて出さず、それらのidentityは
非公開台帳にのみ置きます。

## 限界

- 入力・facts・信頼フラグは未認証の呼出し側申告です。別途レビューされる後続のreaderが与える
  必要があり、ここでは強制しません。
- 未実装：webhook ingress、protection audit、job schema、aggregate gate。
- テストは未実行です。実行には新しい予算の明示が必要です。
