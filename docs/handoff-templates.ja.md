# 再利用可能なhandoffテンプレート

[English](handoff-templates.md) | [日本語](handoff-templates.ja.md)

ツール間で作業を渡すときは、範囲と受け入れ条件を明確にします。DottieはPMと受け入れ調整、Factoryは薄いhandoff/artifact/evidence層、AIteamBridgeは別個のローカルcapacity/router/transport開発を担います。live quota取得と自動dispatchは未検証です。

## Evidence manifest

モデル比較や複数段階の作業では、実行前に入力、prompt、受け入れ条件、rubric、制約、評価手順を固定します。

```text
task_id:
input revision / paths / hashes:
prompt / rubric / acceptance criteria:
provider / route / environment:
requested model / effort:
observed runtime model / effort: 証拠がなければ UNKNOWN
accepted / executed / verified: それぞれ別の状態と証拠参照
output paths / hashes:
review findings / test results / unresolved items:
reacquire source / revision / hash:
```

依頼がacceptedまたはWorkingと表示されても、完了の証明にはなりません。結果を読み、受け入れ条件を確認します。local/offlineテストはlive provider経路や本番反映を証明しません。

## Product Owner / Dottieから実装担当へ

```markdown
# Goal
[達成したいこと]

## Scope and constraints
- 対象:
- 対象外:
- 環境 / provider制約:

## Acceptance criteria
- [観測可能な結果]

## Requested model/effort
[このタスク固有の指定。全体既定に一般化しない]

## Report back
- 変更ファイル / artifact:
- 実施した確認と結果:
- accepted / executed / verifiedの状態:
- 未確認事項とblocker:
```

## Qwen調査handoff

```markdown
# Research question
[質問]

## Inputs and permitted sources
- Files / URLs:
- Read-onlyか、その他の境界:

## Findings
- 出典付きの所見:
- 確度や曖昧さ:

## Handoff
- Evidence / artifact参照:
- 次の担当への質問:
- 調査結果から実装、稼働成功、権限を推定しない:
```

## 独立レビュー

```text
提示したrevisionを独立にレビューし、実装変更は行わない。
重大度、file/line、根拠、影響、再現または確認方法を記載。
未確認の前提と重要なテスト不足を明示。
重大な指摘がなければ、その旨と残るruntime制約を記す。
```
