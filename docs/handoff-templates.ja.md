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

## 3. PoCから実装への任意の精緻化

PoCが重要な不確実性を減らす場合にだけ使います。既存artifactを保持し、初期実装を重複させません。

```markdown
# Goal and acceptance criteria
[範囲を限定した目標]

## Existing artifact and verification
- revision / files:
- 実行済みテスト:
- 既知の不足:

## Refinement request
- 根拠が変更を支持しない限り、動作中の挙動とarchitectureを保つ。
- 編集、確認、未解決事項、必要な承認を報告する。
```

## 5. 検証済みreview指摘の適用

```text
次の確認済み指摘だけを適用する:
[指摘IDと根拠]

変更範囲を小さく保つ。関連する確認を行い、変更ファイル、確認結果、残る不明点を報告する。
```

## 6. 権限承認が拒否された場合は停止して保持

```text
必要な操作は[承認段階]で拒否された。
繰り返し再試行したり、別経路で拒否を迂回したりしない。
現在の作業を保持し、正確な操作、対象、拒否理由、保存済みartifact、次に許可された手順を報告する。
```
## 4. 独立レビューの範囲と出力

レビュー依頼では、確認するfiles、変更範囲、特に見るrisk領域を指定します。reviewerは実装変更を行わず、次を返します。

- Critical/Majorの指摘はfile/line、根拠、影響、再現または確認方法を含める。
- 未確認の前提を列挙し、確かな事実のように書かない。
- 重要なtest gapを示す。
- 重大な指摘がない場合も、その結論と残るtest/runtime制約を記す。
## 範囲

レビュー対象revision、files／変更箇所、懸念するrisk領域を明示します。reviewerは提示されたrevisionを独立に確認し、実装をしません。

## 出力

- Critical/Majorの指摘にはseverity、file/line、根拠、影響、再現または確認方法を含めます。
- 未確認の前提と重要なテスト不足を列挙します。
- 重大な指摘がなければその旨を述べ、残るtest/runtime gapも記します。